"""
shift_parser.providers.openai_provider
---------------------------------------
Provider that targets the official OpenAI API (gpt-4o, gpt-4-turbo, etc.).

Setup:
    pip install openai
    export OPENAI_API_KEY="sk-..."

Usage:
    from shift_parser.providers import OpenAIProvider
    provider = OpenAIProvider()                          # reads key from env
    provider = OpenAIProvider(api_key="sk-...", model="gpt-4o")
"""

from __future__ import annotations
import os
from shift_parser.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    OpenAI Chat Completions provider.

    Args:
        api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
        model:   Model name. Defaults to "gpt-4o-mini".
        temperature: Sampling temperature (default 0.1 for deterministic output).
        max_tokens:  Max tokens for the response.
    """

    _DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key:     str  | None = None,
        model:       str         = _DEFAULT_MODEL,
        temperature: float       = 0.1,
        max_tokens:  int         = 1024,
    ) -> None:
        self._api_key    = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model      = model
        self._temperature = temperature
        self._max_tokens  = max_tokens

        if not self._api_key:
            raise ValueError(
                "OpenAI API key not found. Pass api_key= or set OPENAI_API_KEY."
            )

    # ── BaseProvider interface ────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, system_prompt: str, user_message: str) -> str:
        from openai import OpenAI  # lazy import — openai is optional

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model       = self._model,
            temperature = self._temperature,
            max_tokens  = self._max_tokens,
            messages    = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )
        return response.choices[0].message.content.strip()
