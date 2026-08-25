from typing import Any

from t8_agent.task.tools.users.base import BaseUserServiceTool


class DeleteUserTool(BaseUserServiceTool):
    @property
    def name(self) -> str:
        return "delete_user"

    @property
    def description(self) -> str:
        return "deletes a user from the UserService"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "number",
                    "description": "The numeric id of the user to delete.",
                },
            },
            "required": ["id"],
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        try:
            user_id = int(arguments["id"])
            return self._user_client.delete_user(user_id)
        except Exception as e:
            return f"Error while deleting the user: {e!s}"
