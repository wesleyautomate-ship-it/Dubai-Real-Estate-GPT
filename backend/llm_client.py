"""
Unified LLM client that supports OpenAI (default) and Gemini.
Gemini support currently provides text-only responses (no tool calling).
"""

from __future__ import annotations

import json
import logging
from threading import Lock
from typing import List, Dict, Optional
from uuid import uuid4

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
    from google.generativeai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None
    genai_types = None

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
            "supports_tools": True,
            "available": bool(GEMINI_API_KEY),
        },
    ]


class _SimpleFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _SimpleToolCall:
    def __init__(self, name: str, arguments: str):
        self.id = str(uuid4())
        self.type = "function"
        self.function = _SimpleFunction(name, arguments)


class _SimpleMessage:
    def __init__(self, content: str | None, tool_calls: Optional[List[_SimpleToolCall]] = None):
        self.content = content
        self.tool_calls: List[_SimpleToolCall] = tool_calls or []


class _SimpleChoice:
    def __init__(self, message: _SimpleMessage):
        self.message = message


class _SimpleResponse:
    def __init__(self, choices: List[_SimpleChoice]):
        self.choices = choices


class LLMClient:
    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = (provider or get_default_provider()).lower()
        self.supports_tool_calling = True
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
            if genai_types is None:
                raise RuntimeError(
                    "google-generativeai types module not available; please upgrade google-generativeai"
                )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.2,
    ):
        if self.provider == "openai":
            return self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
            )

        # Gemini tool-calling path
        system_instruction, contents = self._convert_messages_to_gemini(messages)
        tool_decls = self._convert_tools_to_gemini(tools) if tools else None

        response = self.client.generate_content(
            contents=contents,
            tools=tool_decls,
            system_instruction=system_instruction or None,
            generation_config={
                "temperature": temperature,
            },
            tool_config={
                "function_calling_config": {
                    "mode": "AUTO" if tool_choice == "auto" else "ANY"
                }
            }
            if tool_decls
            else None,
        )

        parts = getattr(getattr(response, "candidates", [None])[0], "content", {}).parts or []
        text_segments: List[str] = []
        tool_calls: List[_SimpleToolCall] = []

        for part in parts:
            # Text content
            part_text = getattr(part, "text", None)
            if part_text:
                text_segments.append(part_text)

            # Function calls
            fn_call = getattr(part, "function_call", None)
            if fn_call:
                name = getattr(fn_call, "name", "")
                raw_args = getattr(fn_call, "args", {}) or {}
                try:
                    args_json = json.dumps(raw_args)
                except Exception:
                    args_json = json.dumps({})
                tool_calls.append(_SimpleToolCall(name=name, arguments=args_json))

        message = _SimpleMessage(
            content="\n".join(text_segments).strip() if text_segments else None,
            tool_calls=tool_calls,
        )
        return _SimpleResponse([_SimpleChoice(message)])

    def _convert_tools_to_gemini(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """
        Convert OpenAI-style function tool schemas to Gemini function declarations.
        """
        if not tools:
            return None

        declarations = []
        for tool in tools:
            fn = tool.get("function", {})
            name = fn.get("name")
            if not name:
                continue
            declaration = genai_types.FunctionDeclaration(
                name=name,
                description=fn.get("description", ""),
                parameters=fn.get("parameters") or {},
            )
            declarations.append(declaration)

        if not declarations:
            return None

        return [{"function_declarations": declarations}]

    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> tuple[str, List[Dict]]:
        """
        Convert OpenAI-style messages to Gemini content blocks.
        """
        system_segments: List[str] = []
        contents: List[Dict] = []

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "") or ""

            if role == "system":
                if text:
                    system_segments.append(text)
                continue

            if role == "user":
                contents.append({"role": "user", "parts": [{"text": text}]})
                continue

            if role == "assistant":
                parts = []
                if text:
                    parts.append({"text": text})
                # Preserve prior tool calls as plain text so Gemini has context
                for call in msg.get("tool_calls", []) or []:
                    fn = getattr(call, "function", None) or {}
                    name = getattr(fn, "name", "")
                    args = getattr(fn, "arguments", "") or ""
                    parts.append({"text": f"Called tool {name} with args: {args}"})
                contents.append({"role": "model", "parts": parts or [{"text": ""}]})
                continue

            if role == "tool":
                name = msg.get("name", "tool")
                raw_content = msg.get("content", "")
                try:
                    response_obj = json.loads(raw_content)
                except Exception:
                    response_obj = {"output": raw_content}

                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "function_response": {
                                    "name": name,
                                    "response": response_obj,
                                }
                            }
                        ],
                    }
                )
                continue

            # Fallback: include as text
            contents.append({"role": "user", "parts": [{"text": text}]})

        system_instruction = "\n".join(system_segments).strip()
        return system_instruction, contents

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
