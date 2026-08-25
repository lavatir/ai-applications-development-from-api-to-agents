from typing import Any

import requests

from commons.constants import OPENAI_RESPONSES_ENDPOINT
from t8_agent.task.tools.base import BaseTool


class WebSearchTool(BaseTool):
    def __init__(self, open_ai_api_key: str):
        self.__api_key = f"Bearer {open_ai_api_key}"
        self.__endpoint = OPENAI_RESPONSES_ENDPOINT

    @property
    def name(self) -> str:
        return "web_search_tool"

    @property
    def description(self) -> str:
        return "used for searching on the internet"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "The search query to look up on the internet."},
            },
            "required": ["request"],
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        headers = {
            "Authorization": self.__api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": "gpt-5.2",
            "input": arguments["request"],
            "tools": [{"type": "web_search"}],
        }

        response = requests.post(self.__endpoint, headers=headers, json=request_data)

        if response.status_code == 200:
            data = response.json()
            output = data.get("output", [])
            content_parts = [
                content["text"]
                for item in output
                if item.get("type") == "message"
                for content in item.get("content", [])
                if content.get("type") == "output_text"
            ]
            return "".join(content_parts)

        return f"Error: {response.status_code} {response.text}"
