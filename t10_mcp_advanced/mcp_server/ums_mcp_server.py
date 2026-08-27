import asyncio
import uuid

from commons.user_service.client import UserServiceClient
from t10_mcp_advanced.mcp_server.models.request import MCPRequest
from t10_mcp_advanced.mcp_server.models.response import ErrorResponse, MCPResponse
from t10_mcp_advanced.mcp_server.tools.users.create_user_tool import CreateUserTool
from t10_mcp_advanced.mcp_server.tools.users.delete_user_tool import DeleteUserTool
from t10_mcp_advanced.mcp_server.tools.users.get_user_by_id_tool import GetUserByIdTool
from t10_mcp_advanced.mcp_server.tools.users.search_users_tool import SearchUsersTool
from t10_mcp_advanced.mcp_server.tools.users.update_user_tool import UpdateUserTool


class MCPSession:
    """Represents an MCP session with state management"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.ready_for_operation = False
        self.created_at = asyncio.get_event_loop().time()
        self.last_activity = self.created_at


class UmsMCPServer:
    def __init__(self):
        self.protocol_version = "2025-11-25"
        self.server_info = {"name": "custom-ums-mcp-server", "version": "1.0.0"}

        # Session management
        self.sessions: dict[str, MCPSession] = {}
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools"""
        self.usc = UserServiceClient()
        tools = [
            GetUserByIdTool(self.usc),
            SearchUsersTool(self.usc),
            CreateUserTool(self.usc),
            UpdateUserTool(self.usc),
            DeleteUserTool(self.usc),
        ]
        for tool in tools:
            self.tools[tool.name] = tool

    def _validate_protocol_version(self, client_version: str) -> str:
        """Validate and negotiate protocol version"""
        supported_versions = ["2024-11-05", "2025-11-25"]
        if client_version in supported_versions:
            return client_version
        return self.protocol_version

    def get_session(self, session_id: str) -> MCPSession | None:
        """Get an existing session"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = asyncio.get_event_loop().time()
        return session

    def handle_initialize(self, request: MCPRequest) -> tuple[MCPResponse, str]:
        """Handle initialization request with session creation"""
        session_id = str(uuid.uuid4()).replace("-", "")
        session = MCPSession(session_id=session_id)
        self.sessions[session_id] = session

        protocol_version = (
            request.params.get("protocolVersion")
            if request.params
            else self.protocol_version
        )

        mcp_response = MCPResponse(
            id=request.id,
            result={
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": self.server_info,
            },
        )

        return (mcp_response, session_id)

    def handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request"""
        tools_list = [tool.to_mcp_tool() for tool in self.tools.values()]
        return MCPResponse(id=request.id, result={"tools": tools_list})

    async def handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call request with proper MCP-compliant response format"""
        if not request.params:
            return MCPResponse(
                id=request.id,
                error=ErrorResponse(code=-32602, message="Missing parameters"),
            )

        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if not tool_name:
            return MCPResponse(
                id=request.id,
                error=ErrorResponse(
                    code=-32602, message="Missing required parameter: name"
                ),
            )

        if tool_name not in self.tools:
            return MCPResponse(
                id=request.id,
                error=ErrorResponse(
                    code=-32601, message=f"Tool '{tool_name}' not found"
                ),
            )

        tool = self.tools[tool_name]

        try:
            result_text = await tool.execute(arguments)
            return MCPResponse(
                id=request.id,
                result={"content": [{"type": "text", "text": result_text}]},
            )
        except Exception as tool_error:
            return MCPResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Tool execution error: {tool_error!s}",
                        }
                    ],
                    "isError": True,
                },
            )
