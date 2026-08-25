import json
from typing import Any

import requests

from commons.constants import OPENAI_CHAT_COMPLETIONS_ENDPOINT
from commons.models.message import Message
from commons.models.role import Role
from t8_agent.task.agents._base import BaseAgent
from t8_agent.task.tools.base import BaseTool


class OpenAIBasedAgent(BaseAgent):
    def __init__(
        self,
        model: str,
        api_key: str,
        tools: list[BaseTool] | None = None,
        system_prompt: str | None = None,
    ):
        super().__init__(model, api_key, tools, system_prompt)
        self._api_key = f"Bearer {api_key}"
        self._tools_schemas = [tool.openai_schema for tool in (tools or [])]
        self._endpoint = OPENAI_CHAT_COMPLETIONS_ENDPOINT
        print(self._endpoint)
        print(json.dumps(self._tools_schemas, indent=4))

    def get_response(
        self, messages: list[Message], print_request: bool = True
    ) -> Message:
        request_messages = list(messages)
        if self._system_prompt:
            request_messages = [
                Message(role=Role.SYSTEM, content=self._system_prompt)
            ] + request_messages

        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self._model,
            "messages": [message.to_dict() for message in request_messages],
            "tools": self._tools_schemas,
        }

        if print_request:
            print(self._endpoint)
            print("REQUEST:", json.dumps(request_data, indent=4))

        response = requests.post(self._endpoint, headers=headers, json=request_data)

        if response.status_code == 200:
            data = response.json()
            choice = data["choices"][0]
            print("RESPONSE:", json.dumps(choice, indent=4))

            message = choice["message"]
            content = message.get("content")
            tool_calls = message.get("tool_calls")

            ai_response = Message(
                role=Role.ASSISTANT, content=content, tool_calls=tool_calls
            )

            if choice.get("finish_reason") == "tool_calls":
                messages.append(ai_response)
                messages.extend(self._process_tool_calls(tool_calls))
                return self.get_response(messages, print_request)

            return ai_response

        raise Exception(f"HTTP {response.status_code}: {response.text}")

    def _process_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[Message]:
        tool_messages = []
        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            result = self._call_tool(function_name, arguments)
            tool_messages.append(
                Message(
                    role=Role.TOOL,
                    name=function_name,
                    tool_call_id=tool_call_id,
                    content=result,
                )
            )
            print(f"{function_name}: {result}")

        return tool_messages

    def _call_tool(self, function_name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools_dict.get(function_name)
        if tool:
            return tool.execute(arguments)
        return f"Unknown function: {function_name}"
