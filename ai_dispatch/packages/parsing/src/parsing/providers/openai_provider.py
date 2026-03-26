"""
providers/openai_provider.py
-----------------------------
Calls the OpenAI cloud API.

Setup:
    export OPENAI_API_KEY="sk-..."

Usage:
    from providers.openai_provider import OpenAIProvider
    provider = OpenAIProvider()
    provider = OpenAIProvider(api_key="sk-...", model="gpt-4o")
"""

import os
from openai import OpenAI


class OpenAIProvider:
    """Calls the OpenAI cloud API. Reads OPENAI_API_KEY from env if no key is passed."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        self.name  = "OpenAI"
        self.model = model
        self._client = OpenAI(
            api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages to OpenAI, return the reply as a string."""
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
