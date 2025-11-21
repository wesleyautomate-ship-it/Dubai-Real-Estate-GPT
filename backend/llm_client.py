"""
Unified LLM client that supports OpenAI (default) and Gemini.
Gemini support currently provides text-only responses (no tool calling).
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import List, Dict, Optional

from backend.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

logger = logging.getLogger(__name__)

_provider_lock = Lock()
_default_provider = LLM_PROVIDER


def get_default_provider() -> str:
    with _provider_lock:
        return _default_provider


def set_default_provider(provider: str) -> str:
    provider = provider.strip().lower()
    if provider not in {"openai", "gemini"}:
        raise ValueError("Provider must be either 'openai' or 'gemini'")
    if provider == "gemini" and not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required to use Gemini")
    with _provider_lock:
        global _default_provider
        _default_provider = provider
    return provider


def get_llm_options() -> List[Dict[str, str]]:
    return [
        {
            "provider": "openai",
            "label": f"GPT-4o mini (OpenAI)",
            "model": OPENAI_CHAT_MODEL,
            "supports_tools": True,
            "available": True,
        },
        {
            "provider": "gemini",
            "label": f"Gemini 1.5 Flash",
            "model": GEMINI_CHAT_MODEL,
            "supports_tools": False,
            "available": bool(GEMINI_API_KEY),
        },
    ]


class LLMClient:
    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = (provider or get_default_provider()).lower()
        self.supports_tool_calling = self.provider == "openai"
        self._init_client()

    def _init_client(self) -> None:
        if self.provider == "openai":
            if OpenAI is None:
                raise RuntimeError("OpenAI SDK is not installed")
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.chat_model = OPENAI_CHAT_MODEL
        else:
            if genai is None:
                raise RuntimeError(
                    "google-generativeai package is required when LLM_PROVIDER=gemini"
                )
            genai.configure(api_key=GEMINI_API_KEY)
            self.client = genai.GenerativeModel(GEMINI_CHAT_MODEL)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.2,
    ):
        if self.provider != "openai":
            raise NotImplementedError("Tool calling is only available for OpenAI.")
        return self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )

    def simple_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        prompt_parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            prefix = "User"
            if role == "assistant":
                prefix = "Assistant"
            elif role == "system":
                prefix = "System"
            prompt_parts.append(f"{prefix}: {msg.get('content', '')}")
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)

        response = self.client.generate_content(
            prompt, generation_config={"temperature": temperature}
        )
        text = getattr(response, "text", None)
        if text:
            return text

        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            parts = getattr(candidate, "content", None)
            if not parts:
                continue
            for part in getattr(parts, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    return part_text

        logger.warning("Gemini response contained no text; returning empty string.")
        return ""


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    return LLMClient(provider)
