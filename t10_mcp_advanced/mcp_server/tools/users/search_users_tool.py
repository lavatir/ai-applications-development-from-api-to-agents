from typing import Any

from commons.user_service.user_info import UserSearchRequest
from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class SearchUsersTool(BaseUserServiceTool):
    @property
    def name(self) -> str:
        return "search_users"

    @property
    def description(self) -> str:
        return "Search for users in the UserService"

    @property
    def input_schema(self) -> dict[str, Any]:
        return UserSearchRequest.model_json_schema()

    async def execute(self, arguments: dict[str, Any]) -> str:
        try:
            return self._user_client.search_users(**arguments)
        except Exception as e:
            return f"Error while searching users: {e!s}"
