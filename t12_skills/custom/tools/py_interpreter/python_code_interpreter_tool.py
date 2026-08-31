from pathlib import Path
from typing import Any

from t12_skills.custom.file_utils import get_file_content
from t12_skills.custom.mcp.mcp_client import T12MCPClient
from t12_skills.custom.mcp.mcp_tool_model import MCPToolModel
from t12_skills.custom.tools.base import BaseTool
from t12_skills.custom.tools.py_interpreter._response import _ExecutionResult


class PythonCodeInterpreterTool(BaseTool):
    def __init__(
        self,
        mcp_client: T12MCPClient,
        mcp_tool_models: list[MCPToolModel],
        tool_name: str,
        skills_dir: Path,
    ):
        self._mcp_client = mcp_client
        self._skills_dir = skills_dir

        self._code_execute_tool: MCPToolModel | None = None
        for tool in mcp_tool_models:
            if tool.name == tool_name:
                self._code_execute_tool = tool
                break

        if self._code_execute_tool is None:
            available = [tool.name for tool in mcp_tool_models]
            raise ValueError(
                f"Tool '{tool_name}' not found. Available tools: {available}"
            )

    @classmethod
    async def create(
        cls, mcp_url: str, tool_name: str, skills_dir: Path
    ) -> "PythonCodeInterpreterTool":
        """Async factory method to create PythonCodeInterpreterTool."""
        mcp_client = await T12MCPClient.create(mcp_url)
        mcp_tool_models = await mcp_client.get_tools()
        return cls(mcp_client, mcp_tool_models, tool_name, skills_dir)

    @property
    def name(self) -> str:
        assert self._code_execute_tool is not None
        return self._code_execute_tool.name

    @property
    def description(self) -> str:
        assert self._code_execute_tool is not None
        return self._code_execute_tool.description

    @property
    def parameters(self) -> dict[str, Any]:
        assert self._code_execute_tool is not None
        parameters = {**self._code_execute_tool.parameters}
        parameters["properties"] = {
            **parameters.get("properties", {}),
            "script_path": {
                "type": "string",
                "description": (
                    "Optional path to a skill script, relative to the skills directory. "
                    "Its content is prepended to `code` before execution."
                ),
            },
        }
        return parameters

    async def _execute(self, arguments: dict[str, Any]) -> str:
        script_path = arguments.get("script_path")
        if script_path:
            full_path = self._skills_dir / script_path.lstrip("/")
            script_content = get_file_content(full_path)
            args = {
                "code": script_content + "\n\n" + arguments["code"],
                "session_id": arguments.get("session_id", ""),
            }
        else:
            args = arguments

        content = await self._mcp_client.call_tool(self.name, args)
        result = _ExecutionResult.model_validate_json(content)
        return result.model_dump_json()
