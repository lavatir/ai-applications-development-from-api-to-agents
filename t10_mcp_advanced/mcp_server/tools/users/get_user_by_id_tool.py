from typing import Any

from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class GetUserByIdTool(BaseUserServiceTool):
    @property
    def name(self) -> str:
        return "get_user_by_id"

    @property
    def description(self) -> str:
        return "Retrieve a single user's details from the User Service by their numeric id."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "The numeric id of the user to retrieve.",
                },
            },
            "required": ["id"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        try:
            user_id = int(arguments["id"])
            return self._user_client.get_user(user_id)
        except Exception as e:
            return f"Error while retrieving user by id: {e!s}"
