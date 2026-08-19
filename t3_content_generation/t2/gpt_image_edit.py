import base64
from pathlib import Path

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST

# https://developers.openai.com/api/reference/resources/images/methods/edit
# ---
# Request (multipart/form-data, NOT json):
# curl -X POST "https://api.openai.com/v1/images/edits" \
#     -H "Authorization: Bearer $OPENAI_API_KEY" \
#     -F "model=gpt-image-1" \
#     -F "image=@logo.png" \
#     -F "prompt=Add magical sparkles and glowing aura around the logo"
# Response:
# {
#   "created": 1699900000,
#   "data": [
#     {
#       "b64_json": "Qt0n6ArYAEABGOhEoYgVAJFdt8jM79uW2DO..."
#     }
#   ]
# }

# TODO:
# You need to edit an existing image with `gpt-image-2` model:
#   - Take a local image (e.g. 'logo.png') and a prompt describing the edit
#   - Send it to the OpenAI images edit API
#   - Decode the returned base64 image and save it locally
# ---
# Hints:
#   - Use /v1/images/edits endpoint
#   - The request must be 'multipart/form-data' (NOT json) — pass the image as a file and the prompt/model as form fields
#   - The edited image will be returned in base64 format

endpoint = f"{OPENAI_HOST}/v1/images/edits"

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
}

logo_path = Path(__file__).parent / "logo.png"

with open(logo_path, "rb") as image_file:
    files = {"image": image_file}
    data = {
        "model": "gpt-image-2",
        "prompt": "Add magical sparkles and glowing aura around the logo",
    }

    response = requests.post(endpoint, headers=headers, files=files, data=data)

response.raise_for_status()

edited_image = response.json()["data"][0]["b64_json"]

with open(Path(__file__).parent / "logo_edited.png", "wb") as f:
    f.write(base64.b64decode(edited_image))
