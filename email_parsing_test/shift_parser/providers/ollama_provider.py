"""
shift_parser.providers.ollama_provider
----------------------------------------
Provider for locally running models via Ollama.
Ollama exposes an OpenAI-compatible REST API on localhost:11434.

Setup:
    # Install Ollama → https://ollama.com
    ollama pull deepseek-r1:7b   # or any other model

Usage:
    from shift_parser.providers import OllamaProvider
    provider = OllamaProvider()                            # deepseek-r1:7b on localhost
    provider = OllamaProvider(model="llama3.2", host="http://192.168.1.5:11434")
"""

from __future__ import annotations
from shift_parser.providers.base import BaseProvider


_DEFAULT_HOST  = "http://localhost:11434"
_DEFAULT_MODEL = "deepseek-r1:7b"


class OllamaProvider(BaseProvider):
    """
    Ollama local model provider.

    Args:
        model:       Ollama model tag to use. Defaults to "deepseek-r1:7b".
        host:        Ollama server URL. Defaults to http://localhost:11434.
        temperature: Sampling temperature.
        max_tokens:  Max response tokens.
    """

    def __init__(
        self,
        model:       str   = _DEFAULT_MODEL,
        host:        str   = _DEFAULT_HOST,
        temperature: float = 0.1,
        max_tokens:  int   = 1024,
    ) -> None:
        self._model       = model
        self._host        = host.rstrip("/")
        self._temperature = temperature
        self._max_tokens  = max_tokens

    # ── BaseProvider interface ────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, system_prompt: str, user_message: str) -> str:
        from openai import OpenAI  # lazy import

        # Ollama's OpenAI-compatible endpoint requires a non-empty API key
        client = OpenAI(
            api_key  = "ollama",
            base_url = f"{self._host}/v1",
        )
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
