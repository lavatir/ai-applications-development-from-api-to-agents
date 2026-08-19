import base64
from pathlib import Path

from commons.constants import OPENAI_CHAT_COMPLETIONS_ENDPOINT
from t3_content_generation._openai_client import OpenAIClientT3

# https://developers.openai.com/api/docs/guides/images-vision?format=url&lang=curl
# https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded

# TODO:
# You need to analyse these 2 images:
#   - https://a-z-animals.com/media/2019/11/Elephant-male-1024x535.jpg
#   - in this folder we have 'logo.png', load it as encoded data (see documentation)
# ---
# Hints:
#   - Use OpenAIClientT3 to connect to OpenAI API
#   - Use /v1/chat/completions endpoint
#   - Function to encode image to base64 you can find in documentation
# ---
# In the end load both images (url and base64 encoded 'logo.png'), ask "Generate poem based on images" and se what will happen?

client = OpenAIClientT3(OPENAI_CHAT_COMPLETIONS_ENDPOINT)

logo_path = Path(__file__).parent / "logo.png"
encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("utf-8")

client.call(
    print_request=True,
    print_response=True,
    model="gpt-5.2",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Generate poem based on images"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://a-z-animals.com/media/2019/11/Elephant-male-1024x535.jpg"
                    },
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded_logo}"},
                },
            ],
        }
    ],
)
