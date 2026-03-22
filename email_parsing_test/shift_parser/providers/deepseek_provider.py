"""
shift_parser.providers.deepseek_provider
-----------------------------------------
Provider that targets the DeepSeek cloud API.
DeepSeek exposes an OpenAI-compatible endpoint, so we reuse the openai SDK.

Setup:
    pip install openai
    export DEEPSEEK_API_KEY="ds-..."

Usage:
    from shift_parser.providers import DeepSeekProvider
    provider = DeepSeekProvider()                              # env var
    provider = DeepSeekProvider(api_key="ds-...", model="deepseek-reasoner")
"""

from __future__ import annotations
import os
from shift_parser.providers.base import BaseProvider


_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(BaseProvider):
    """
    DeepSeek cloud API provider.

    Args:
        api_key:     DeepSeek API key. Defaults to DEEPSEEK_API_KEY env var.
        model:       Model name. Defaults to "deepseek-chat".
        base_url:    API base URL (override for private deployments).
        temperature: Sampling temperature.
        max_tokens:  Max response tokens.
    """

    _DEFAULT_MODEL = "deepseek-chat"

    def __init__(
        self,
        api_key:     str  | None = None,
        model:       str         = _DEFAULT_MODEL,
        base_url:    str         = _DEEPSEEK_BASE_URL,
        temperature: float       = 0.1,
        max_tokens:  int         = 1024,
    ) -> None:
        self._api_key     = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._model       = model
        self._base_url    = base_url
        self._temperature = temperature
        self._max_tokens  = max_tokens

        if not self._api_key:
            raise ValueError(
                "DeepSeek API key not found. Pass api_key= or set DEEPSEEK_API_KEY."
            )

    # ── BaseProvider interface ────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "DeepSeek"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, system_prompt: str, user_message: str) -> str:
        from openai import OpenAI  # lazy import

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
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
