import json

import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.openai.base import BaseOpenAIClient


class CustomOpenAIResponsesClient(BaseOpenAIClient):
    """
    Custom HTTP client for OpenAI Responses API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with the Responses API directly
    and handle its unique event-based streaming format.
    """

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response using raw HTTP POST request.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The AI's response message.

        Raises:
            ValueError: If the API response contains no output text.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            Uses the Responses API format with 'instructions' and 'input' parameters.
            The response is printed to stdout before being returned.
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self._model_name,
            "instructions": self._system_prompt,
            "input": [message.to_dict() for message in messages],
        }

        response = requests.post(self._endpoint, headers=headers, json=request_data)
        response.raise_for_status()

        data = response.json()
        output = data.get("output", [])
        content_parts = [
            content["text"]
            for item in output
            if item.get("type") == "message"
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        ]

        if not content_parts:
            raise ValueError("API response contains no output text")

        content = "".join(content_parts)
        print(content)

        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with event-based streaming.

        The Responses API uses a different SSE format than Chat Completions,
        with explicit event types and data fields.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Uses event-based Server-Sent Events (SSE) format.
            Listens for 'response.output_text.delta' events to build the response.
            Each line with "event: " specifies the event type, followed by "data: " with the payload.
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self._model_name,
            "instructions": self._system_prompt,
            "input": [message.to_dict() for message in messages],
            "stream": True,
        }

        chunks = []
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                self._endpoint, headers=headers, json=request_data
            ) as response,
        ):
            response.raise_for_status()

            event_type = None
            async for line in response.content:
                decoded = line.decode("utf-8").strip()
                if not decoded:
                    continue
                if decoded.startswith("event: "):
                    event_type = decoded[len("event: ") :]
                elif decoded.startswith("data: "):
                    data = json.loads(decoded[len("data: ") :])
                    if event_type == "response.output_text.delta":
                        delta = data.get("delta", "")
                        print(delta, end="", flush=True)
                        chunks.append(delta)

        return Message(role=Role.ASSISTANT, content="".join(chunks))
