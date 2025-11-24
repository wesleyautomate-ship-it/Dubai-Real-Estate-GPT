"""
Gemini API client for AI-based data enrichment.
"""

import os
import google.generativeai as genai


def _get_model() -> genai.GenerativeModel:
    """Configure Gemini lazily from environment and return a model instance.

    This ensures that `.env` has already been loaded (via `load_dotenv()` in the
    caller) before we read GEMINI_API_KEY / GEMINI_CHAT_MODEL.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in {"your_gemini_api_key", "YOUR_GEMINI_API_KEY"}:
        raise RuntimeError(
            "GEMINI_API_KEY is not set to a valid value. "
            "Update your .env (or environment) with a real Gemini API key from Google AI Studio."
        )

    # Configure client for this process with the current key
    genai.configure(api_key=api_key)

    # Use the same configurable model name as the backend/test scripts
    model_name = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    return genai.GenerativeModel(model_name)


def call_gemini(prompt: str) -> str:
    """Call Gemini with a prompt and return a JSON string response."""
    model = _get_model()
    resp = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return resp.text
