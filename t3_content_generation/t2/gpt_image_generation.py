import base64

from commons.constants import OPENAI_HOST
from t3_content_generation._openai_client import OpenAIClientT3

# https://developers.openai.com/api/reference/resources/images/methods/generate
# ---
# Request:
# curl -X POST "https://api.openai.com/v1/images/generations" \
#     -H "Authorization: Bearer $OPENAI_API_KEY" \
#     -H "Content-type: application/json" \
#     -d '{
#         "model": "gpt-image-2",
#         "prompt": "smiling catdog."
#     }'
# Response:
# {
#   "created": 1699900000,
#   "data": [
#     {
#       "b64_json": Qt0n6ArYAEABGOhEoYgVAJFdt8jM79uW2DO...,
#     }
#   ]
# }

endpoint = f"{OPENAI_HOST}/v1/images/generations"

client = OpenAIClientT3(endpoint)

response = client.call(
    print_request=True,
    print_response=True,
    model="gpt-image-2",
    prompt="smiling catdog",
    size="1024x1024",
    quality="high",
)

with open("catdog.png", "wb") as f:
    f.write(base64.b64decode(response["data"][0]["b64_json"]))
