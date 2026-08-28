import asyncio
import json

from commons.constants import OPENAI_API_KEY
from commons.models.message import Message
from commons.models.role import Role
from t11_mcp_auth.agent._agent import AgentMCPAuth
from t11_mcp_auth.agent.mcp_clients.oauth_mcp_client import OauthHttpMCPClient

MCP_API_KEY: str = "dev-secret-key"

SYSTEM_PROMPT = "You are a helpful assistant with access to tools from an MCP server."


async def main():
    async with OauthHttpMCPClient(
        mcp_server_url="http://localhost:8008/mcp"
    ) as mcp_client:
        tools = await mcp_client.get_tools()
        for tool in tools:
            print(json.dumps(tool, indent=2))

        agent = AgentMCPAuth(
            api_key=OPENAI_API_KEY,
            model="gpt-5.2",
            tools=tools,
            mcp_client=mcp_client,
        )

        messages: list[Message] = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

        print("Agent ready. Type 'exit' to quit.\n")
        while True:
            user_input = input("You: ").strip()
            if user_input == "exit":
                break

            messages.append(Message(role=Role.USER, content=user_input))

            ai_message = await agent.get_completion(messages)
            messages.append(ai_message)


if __name__ == "__main__":
    asyncio.run(main())
