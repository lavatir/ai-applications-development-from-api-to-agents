import asyncio
from pathlib import Path

from commons.constants import OPENAI_API_KEY
from commons.models.message import Message
from commons.models.role import Role
from t9_mcp_fundamentals.agent.agent import AgentMCPFundamentals
from t9_mcp_fundamentals.agent.mcp_clients.stdio import StdioMCPClient
from t9_mcp_fundamentals.agent.prompts import SYSTEM_PROMPT

PROJECT_ROOT = Path(__file__).parent.parent.parent
STDIO_SERVER_PATH = (
    PROJECT_ROOT / "t9_mcp_fundamentals" / "mcp_server" / "stdio_server.py"
)


async def main():
    async with StdioMCPClient(
        docker_image="mcp/duckduckgo:latest"  # inherit env + add project root
    ) as mcp_client:
        resources = await mcp_client.get_resources()
        tools = await mcp_client.get_tools()
        prompts = await mcp_client.get_prompts()

        print(resources)
        print(tools)
        print(prompts)

        agent = AgentMCPFundamentals(
            api_key=OPENAI_API_KEY,
            model="gpt-5.2",
            tools=tools,
            mcp_client=mcp_client,
        )

        messages: list[Message] = []
        messages.append(Message(role=Role.SYSTEM, content=SYSTEM_PROMPT))

        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                break

            messages.append(Message(role=Role.USER, content=user_input))

            response = await agent.get_response(messages)

            ai_message = Message(
                Role.ASSISTANT,
                content=response.content,
                tool_call_id=response.tool_call_id,
                tool_calls=response.tool_calls,
            )

            messages.append(ai_message)
            print(f"Assistant: {ai_message.content}")


if __name__ == "__main__":
    asyncio.run(main())
