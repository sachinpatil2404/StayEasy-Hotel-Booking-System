from google import genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from django.conf import settings


# Get the NEW Gemini API key from .env / Django settings
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or getattr(
    settings, "GEMINI_API_KEY", ""
)

# Create Gemini client
client = genai.Client(api_key=GEMINI_KEY)

# Current stable Gemini model
MODEL_NAME = "gemini-3.6-flash"


@csrf_exempt
def chatbot_response(request):

    if request.method != "POST":
        return JsonResponse({
            "reply": "Invalid request. Use POST."
        })

    try:
        data = json.loads(request.body)
        message = data.get("message", "").strip()

        if not message:
            return JsonResponse({
                "reply": "Please type something!"
            })

        # Gemini Interactions API
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=message
        )

        return JsonResponse({
            "reply": interaction.output_text
        })

    except Exception as e:
        return JsonResponse({
            "reply": f"AI Error: {str(e)}"
        })