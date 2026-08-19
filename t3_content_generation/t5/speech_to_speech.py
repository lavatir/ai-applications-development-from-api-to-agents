import base64
from pathlib import Path

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST

# https://developers.openai.com/api/docs/guides/audio#add-audio-to-your-existing-application

# TODO:
# You need to generate answer in audio format based on the audio message:
#   - Create Client that is similar with OpenAIClients but extracts from message audio (instead of content)
#   - Call API
#   - Get response as base64 content, decode and save as .mp3 file
# ---
# Hints:
#   - Use /v1/chat/completions endpoint
#   - Use gpt-4o-audio-preview model
#   - Use modalities=["text", "audio"]
#   - Use audio={"voice": "ballad", "format": "mp3"}
#   - Use similar method to encode audio as you have done for images encoding

endpoint = f"{OPENAI_HOST}/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

question_path = Path(__file__).parent / "question.mp3"
encoded_question = base64.b64encode(question_path.read_bytes()).decode("utf-8")

data = {
    "model": "gpt-audio-1.5",
    "modalities": ["text", "audio"],
    "audio": {"voice": "ballad", "format": "mp3"},
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {"data": encoded_question, "format": "mp3"},
                },
            ],
        }
    ],
}

response = requests.post(endpoint, headers=headers, json=data)
response.raise_for_status()

audio_data = response.json()["choices"][0]["message"]["audio"]["data"]

with open(Path(__file__).parent / "answer.mp3", "wb") as f:
    f.write(base64.b64decode(audio_data))
