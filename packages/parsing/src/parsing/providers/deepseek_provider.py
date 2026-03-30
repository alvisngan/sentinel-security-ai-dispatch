"""
providers/deepseek_provider.py
-------------------------------
Calls the DeepSeek cloud API.

Setup:
    export DEEPSEEK_API_KEY="ds-..."

Usage:
    from providers.deepseek_provider import DeepSeekProvider
    provider = DeepSeekProvider()
    provider = DeepSeekProvider(api_key="ds-...", model="deepseek-reasoner")
"""

import os
from openai import OpenAI


class DeepSeekProvider:
    """Calls the DeepSeek cloud API. Reads DEEPSEEK_API_KEY from env if no key is passed."""

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.name  = "DeepSeek"
        self.model = model
        self._client = OpenAI(
            api_key  = api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url = "https://api.deepseek.com",
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages to DeepSeek, return the reply as a string."""
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
