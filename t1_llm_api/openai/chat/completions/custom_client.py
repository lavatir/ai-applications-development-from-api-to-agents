import json

import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.openai.base import BaseOpenAIClient


class CustomOpenAIClient(BaseOpenAIClient):
    """
    Custom HTTP client for OpenAI Chat Completions API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, providing more control over the HTTP layer and demonstrating
    how to interact with the API directly.
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
            ValueError: If the API response contains no choices.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            The system prompt is automatically prepended to the messages.
            The response is printed to stdout before being returned.
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self._model_name,
            "messages": [
                Message(role=Role.SYSTEM, content=self._system_prompt).to_dict()
            ]
            + [message.to_dict() for message in messages],
        }

        response = requests.post(self._endpoint, headers=headers, json=request_data)
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            raise ValueError("API response contains no choices")

        content = choices[0]["message"]["content"]
        print(content)

        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed token-by-token using OpenAI's SSE format,
        with each chunk printed immediately as it arrives.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The complete AI response message after all chunks are received.

        Note:
            The system prompt is automatically prepended to the messages.
            Each token is printed to stdout as it arrives.
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        request_data = {
            "model": self._model_name,
            "messages": [
                Message(role=Role.SYSTEM, content=self._system_prompt).to_dict()
            ]
            + [message.to_dict() for message in messages],
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

            async for line in response.content:
                decoded = line.decode("utf-8").strip()
                if not decoded.startswith("data: "):
                    continue
                payload = decoded[len("data: ") :]
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                delta = data["choices"][0]["delta"].get("content")
                if delta:
                    print(delta, end="", flush=True)
                    chunks.append(delta)

        return Message(role=Role.ASSISTANT, content="".join(chunks))
