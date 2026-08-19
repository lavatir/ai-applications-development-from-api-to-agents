from pathlib import Path

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST

# https://developers.openai.com/api/docs/guides/speech-to-text

# TODO:
# You need to transcribe 'audio_sample.mp3':
#   - Create Client that will go to transcriptions OpenAI API
#   - Call API and provide file (pay attention that you work with 'multipart/form-data')
#   - Get response with transcription
# ---
# Hints:
#   - Use /v1/audio/transcriptions endpoint
#   - Use whisper-1 or gpt-4o-transcribe model

endpoint = f"{OPENAI_HOST}/v1/audio/transcriptions"

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
}

audio_path = Path(__file__).parent / "audio_sample.mp3"

with open(audio_path, "rb") as audio_file:
    files = {"file": audio_file}
    data = {
        "model": "gpt-4o-transcribe",
    }

    response = requests.post(endpoint, headers=headers, files=files, data=data)

response.raise_for_status()

print(response.text)
