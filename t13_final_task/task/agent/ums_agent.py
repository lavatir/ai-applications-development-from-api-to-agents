import json
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from t13_final_task.task.agent.guardrail import UMSDataGuardrail
from t13_final_task.task.agent.models import Message, Role
from t13_final_task.task.agent.tools.base import BaseTool

logger = logging.getLogger(__name__)


class UMSAgent:
    """Handles AI model interactions and integrates with MCP client"""

    def __init__(self, api_key: str, model: str, tools: list[BaseTool]):
        self.tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}
        self.tools_schemas = [tool.schema for tool in tools]
        self.model = model
        self.async_openai = AsyncOpenAI(api_key=api_key)
        self.guardrail = UMSDataGuardrail()

    async def response(self, messages: list[Message]) -> Message:
        """Non-streaming completion with tool calling support"""
        request_data = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "tools": self.tools_schemas,
            "stream": False,
        }

        response = await self.async_openai.chat.completions.create(**request_data)
        choice = response.choices[0]

        ai_message = Message(role=Role.ASSISTANT, content=choice.message.content or "")

        if choice.message.tool_calls:
            ai_message.tool_calls = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in choice.message.tool_calls
            ]

        if ai_message.tool_calls:
            messages.append(ai_message)
            await self._call_tools(ai_message, messages)
            return await self.response(messages)

        return ai_message

    async def stream_response(
        self, messages: list[Message]
    ) -> AsyncGenerator[str, None]:
        """
        Streaming completion with tool calling support.
        Yields SSE-formatted chunks.
        """
        request_data = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "tools": self.tools_schemas,
            "stream": True,
        }

        stream = await self.async_openai.chat.completions.create(**request_data)

        content = ""
        tool_deltas = []

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                content += delta.content

            if delta.tool_calls:
                tool_deltas.extend(delta.tool_calls)

            yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        if tool_deltas:
            tool_calls = self._collect_tool_calls(tool_deltas)
            ai_message = Message(
                role=Role.ASSISTANT, content=content, tool_calls=tool_calls
            )
            messages.append(ai_message)

            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}
                activity = {
                    "type": "call",
                    "name": tool_call["function"]["name"],
                    "arguments": arguments,
                }
                yield f"data: {json.dumps({'tool_activity': activity})}\n\n"

            before_call_count = len(messages)
            await self._call_tools(ai_message, messages)

            for tool_message in messages[before_call_count:]:
                activity = {
                    "type": "result",
                    "name": tool_message.name or "",
                    "content": tool_message.content,
                }
                yield f"data: {json.dumps({'tool_activity': activity})}\n\n"

            async for sse_chunk in self.stream_response(messages):
                yield sse_chunk
            return

        messages.append(Message(role=Role.ASSISTANT, content=content))

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    def _collect_tool_calls(self, tool_deltas):
        """Convert streaming tool call deltas to complete tool calls"""
        tool_dict = defaultdict(
            lambda: {
                "id": None,
                "function": {"arguments": "", "name": None},
                "type": None,
            }
        )

        for delta in tool_deltas:
            idx = delta.index
            if delta.id:
                tool_dict[idx]["id"] = delta.id
            if delta.function.name:
                tool_dict[idx]["function"]["name"] = delta.function.name
            if delta.function.arguments:
                tool_dict[idx]["function"]["arguments"] += delta.function.arguments
            if delta.type:
                tool_dict[idx]["type"] = delta.type

        return list(tool_dict.values())

    async def _call_tools(
        self, ai_message: Message, messages: list[Message], silent: bool = False
    ):
        """Execute tool calls using MCP client"""
        for tool_call in ai_message.tool_calls or []:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            tool = self.tools.get(tool_name)
            if tool:
                tool_message = await tool.execute(tool_call["id"], arguments)
                content = tool_message.content
            else:
                content = f"ERROR: Unknown tool '{tool_name}'"

            messages.append(
                Message(
                    role=Role.TOOL,
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=content,
                )
            )

        # TODO 2:
        # Implement it ONLY after you started the app
        # Make PII filtering for tool call result
