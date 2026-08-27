import asyncio

from commons.constants import OPENAI_API_KEY
from commons.models.message import Message
from commons.models.role import Role
from t10_mcp_advanced.agent.agent import CustomAgentMCP
from t10_mcp_advanced.agent.clients.custom_mcp_client import CustomMCPClient
from t10_mcp_advanced.agent.clients.mcp_client import MCPClient

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools from multiple MCP servers. "
    "Use the available tools to help the user manage users and search/fetch info from the web."
)


async def main():
    tools: list[dict] = []
    tool_name_client_map: dict[str, MCPClient | CustomMCPClient] = {}

    ums_client = await MCPClient.create("http://localhost:8006/mcp")
    ums_tools = await ums_client.get_tools()
    tools.extend(ums_tools)
    for tool in ums_tools:
        tool_name_client_map[tool["function"]["name"]] = ums_client

    # fetch_client = await MCPClient.create("https://remote.mcpservers.org/fetch/mcp")
    # fetch_tools = await fetch_client.get_tools()
    # tools.extend(fetch_tools)
    # for tool in fetch_tools:
    #     tool_name_client_map[tool["function"]["name"]] = fetch_client

    agent = CustomAgentMCP(
        api_key=OPENAI_API_KEY,
        model="gpt-5.2",
        tools=tools,
        tool_name_client_map=tool_name_client_map,
    )

    messages: list[Message] = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append(Message(role=Role.USER, content=user_input))

        ai_message = await agent.get_completion(messages)

        messages.append(ai_message)
        print(f"Assistant: {ai_message.content}")


if __name__ == "__main__":
    asyncio.run(main())


# Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him
