from typing import Any

from commons.user_service.user_info import UserUpdate
from t10_mcp_advanced.mcp_server.tools.users.base import BaseUserServiceTool


class UpdateUserTool(BaseUserServiceTool):
    @property
    def name(self) -> str:
        return "update_user"

    @property
    def description(self) -> str:
        return "updates the user attributes in the UserService"

    @property
    def input_schema(self) -> dict[str, Any]:
        schema = UserUpdate.model_json_schema()
        schema["properties"] = {
            "id": {
                "type": "number",
                "description": "The numeric id of the user to update.",
            },
            **schema["properties"],
        }
        schema["required"] = ["id"]
        return schema

    async def execute(self, arguments: dict[str, Any]) -> str:
        try:
            user_id = int(arguments["id"])
            update_fields = {k: v for k, v in arguments.items() if k != "id"}
            new_info = UserUpdate.model_validate(update_fields)
            return self._user_client.update_user(
                user_id=user_id, user_update_model=new_info
            )
        except Exception as e:
            return f"Error while updating user: {e!s}"
