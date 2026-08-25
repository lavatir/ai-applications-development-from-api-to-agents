from commons.constants import OPENAI_API_KEY
from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from commons.user_service.client import UserServiceClient
from t8_agent.task.agents.openai import OpenAIBasedAgent
from t8_agent.task.prompts import SYSTEM_PROMPT
from t8_agent.task.tools.users.create_user_tool import CreateUserTool
from t8_agent.task.tools.users.delete_user_tool import DeleteUserTool
from t8_agent.task.tools.users.get_user_by_id_tool import GetUserByIdTool
from t8_agent.task.tools.users.search_users_tool import SearchUsersTool
from t8_agent.task.tools.users.update_user_tool import UpdateUserTool
from t8_agent.task.tools.web_search import WebSearchTool


def main():

    usc = UserServiceClient()

    tools = [
        CreateUserTool(usc),
        DeleteUserTool(usc),
        GetUserByIdTool(usc),
        SearchUsersTool(usc),
        UpdateUserTool(usc),
        WebSearchTool(OPENAI_API_KEY),
    ]

    agent = OpenAIBasedAgent(
        model="gpt-5.2",
        api_key=OPENAI_API_KEY,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    conversation = Conversation()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break

        conversation.add_message(Message(role=Role.USER, content=user_input))

        response = agent.get_response(
            messages=conversation.get_messages(), print_request=True
        )

        message = Message(
            Role.ASSISTANT,
            content=response.content,
            tool_call_id=response.tool_call_id,
            tool_calls=response.tool_calls,
        )

        conversation.add_message(message)
        print(f"Assistant: {message.content}")


main()
