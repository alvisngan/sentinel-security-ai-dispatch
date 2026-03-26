"""
providers.py
------------
All supported LLM providers in one place.
Pick one and pass it to ShiftParser in main.py.

Usage:
    from providers import OpenAIProvider, DeepSeekProvider, OllamaProvider
"""

import os
from openai import OpenAI


class OpenAIProvider:
    """Calls the OpenAI cloud API. Needs an OPENAI_API_KEY."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        self.model = model
        self.name  = "OpenAI"
        self._client = OpenAI(
            api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages, return the model's reply as a string."""
        response = self._client.chat.completions.create(
            model       = self.model,
            temperature = 0.1,
            max_tokens  = 1024,
            messages    = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()


class DeepSeekProvider:
    """Calls the DeepSeek cloud API. Needs a DEEPSEEK_API_KEY."""

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.model = model
        self.name  = "DeepSeek"
        self._client = OpenAI(
            api_key  = api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url = "https://api.deepseek.com",
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages, return the model's reply as a string."""
        response = self._client.chat.completions.create(
            model       = self.model,
            temperature = 0.1,
            max_tokens  = 1024,
            messages    = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()


class OllamaProvider:
    """Calls a locally running Ollama model. No API key needed."""

    def __init__(self, model: str = "deepseek-r1:7b", host: str = "http://localhost:11434"):
        self.model = model
        self.name  = "Ollama"
        self._client = OpenAI(
            api_key  = "ollama",   # Ollama requires a non-empty string but ignores it
            base_url = f"{host}/v1",
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages, return the model's reply as a string."""
        response = self._client.chat.completions.create(
            model       = self.model,
            temperature = 0.1,
            max_tokens  = 1024,
            messages    = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
