"""
providers/ollama_provider.py
-----------------------------
Calls a locally running Ollama model. No API key needed.

Setup:
    # Install Ollama → https://ollama.com
    ollama pull deepseek-r1:14b

Usage:
    from providers.ollama_provider import OllamaProvider
    provider = OllamaProvider()
    provider = OllamaProvider(model="llama3.2", host="http://localhost:11434")
"""

from openai import OpenAI


class OllamaProvider:
    """Calls a local Ollama model. No API key required."""

    def __init__(self, model: str = "deepseek-r1:7b", host: str = "http://localhost:11434"):
        self.name  = "Ollama"
        self.model = model
        self._client = OpenAI(
            api_key  = "ollama",    # Ollama requires a non-empty string but ignores it
            base_url = f"{host}/v1",
        )

    def complete(self, system: str, user: str) -> str:
        """Send system + user messages to Ollama, return the reply as a string."""
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
