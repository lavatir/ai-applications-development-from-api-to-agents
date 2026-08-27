from typing import Any

from commons.user_service.user_info import UserCreate
from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class CreateUserTool(BaseUserServiceTool):
    @property
    def name(self) -> str:
        return "add_user"

    @property
    def description(self) -> str:
        return "Create a new user in the User Service with the given profile details."

    @property
    def input_schema(self) -> dict[str, Any]:
        return UserCreate.model_json_schema()

    async def execute(self, arguments: dict[str, Any]) -> str:
        try:
            user_create = UserCreate.model_validate(arguments)
            return self._user_client.add_user(user_create)
        except Exception as e:
            return f"Error while creating a new user: {e!s}"
