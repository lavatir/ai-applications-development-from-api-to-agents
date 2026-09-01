import logging
import sys
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from commons.constants import OPENAI_API_KEY
from t13_final_task.task.agent.clients.http_mcp_client import HttpMcpClient
from t13_final_task.task.agent.clients.stdio_mcp_client import StdioMcpClient
from t13_final_task.task.agent.conversation_manager import ConversationManager
from t13_final_task.task.agent.models import Message, SkillMetadata, load_skills
from t13_final_task.task.agent.tools.base import BaseTool
from t13_final_task.task.agent.tools.mcp_tool import McpTool
from t13_final_task.task.agent.tools.read_skill_tool import ReadSkillTool
from t13_final_task.task.agent.ums_agent import UMSAgent

SKILLS_DIR = Path(__file__).parent.parent / "_skills"


def _build_available_skills_xml(skills: list[SkillMetadata]) -> str:
    root = ET.Element("available_skills")
    for skill in skills:
        el = ET.SubElement(root, "skill", attrib={"name": skill.name})
        ET.SubElement(el, "description").text = skill.description
        if skill.license:
            ET.SubElement(el, "license").text = skill.license
        if skill.compatibility:
            ET.SubElement(el, "compatibility").text = skill.compatibility
        if skill.metadata:
            meta = ET.SubElement(el, "metadata")
            for k, v in skill.metadata.items():
                ET.SubElement(meta, k).text = str(v)
        if skill.allowed_tools:
            ET.SubElement(el, "allowed-tools").text = " ".join(skill.allowed_tools)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def build_system_prompt(skills: list[SkillMetadata]) -> str:
    return f"""\
You are an AI assistant with access to agent skills.

{_build_available_skills_xml(skills)}

## How to use skills

When the user's request matches a skill, activate it:
1. Call `read_skill` with the skill's SKILL.md path (e.g. path="/<skill-name>/SKILL.md") to load
   its full instructions.
2. Follow the instructions in the loaded SKILL.md precisely.
"""


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

conversation_manager: ConversationManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize MCP clients, Redis, and ConversationManager on startup"""
    global conversation_manager

    skills = load_skills(SKILLS_DIR)
    system_prompt = build_system_prompt(skills)

    tools: list[BaseTool] = [ReadSkillTool(skills_dir=SKILLS_DIR)]

    http_mcp_client = await HttpMcpClient.create("http://localhost:8005/mcp")
    for tool_model in await http_mcp_client.get_tools():
        tools.append(McpTool(http_mcp_client, tool_model))

    stdio_mcp_client = await StdioMcpClient.create(
        docker_image="khshanovskyi/ddg-mcp-server:latest"
    )
    for tool_model in await stdio_mcp_client.get_tools():
        tools.append(McpTool(stdio_mcp_client, tool_model))

    ums_agent = UMSAgent(api_key=OPENAI_API_KEY, model="gpt-5.2", tools=tools)

    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    await redis_client.ping()  # type: ignore[misc]

    conversation_manager = ConversationManager(
        ums_agent=ums_agent, redis_client=redis_client, system_prompt=system_prompt
    )

    yield

    await redis_client.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    message: Message
    stream: bool = True


class ChatResponse(BaseModel):
    content: str
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class CreateConversationRequest(BaseModel):
    title: str | None = None


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "conversation_manager_initialized": conversation_manager is not None,
    }


@app.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation"""
    assert conversation_manager is not None
    return await conversation_manager.create_conversation(
        request.title or "New Conversation"
    )


@app.get("/conversations")
async def list_conversations() -> list[ConversationSummary]:
    """List all conversations"""
    assert conversation_manager is not None
    summaries = await conversation_manager.list_conversations()
    return [ConversationSummary(**summary) for summary in summaries]


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    assert conversation_manager is not None
    conversation = await conversation_manager.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    assert conversation_manager is not None
    deleted = await conversation_manager.delete_conversation(conversation_id)
    return {"message": "Conversation deleted" if deleted else "Conversation not found"}


@app.post("/conversations/{conversation_id}/chat")
async def chat(conversation_id: str, request: ChatRequest):
    """Chat endpoint that processes messages and returns assistant response"""
    assert conversation_manager is not None
    result = await conversation_manager.chat(
        request.message, conversation_id, stream=request.stream
    )

    if request.stream:
        return StreamingResponse(result, media_type="text/event-stream")
    return ChatResponse(**result)  # type: ignore[arg-type]


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8011,
        log_level="debug",
    )
