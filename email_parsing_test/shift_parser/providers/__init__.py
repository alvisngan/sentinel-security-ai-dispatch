"""
shift_parser.providers
-----------------------
All built-in LLM providers. Import any of them from here.

Example:
    from shift_parser.providers import OpenAIProvider, DeepSeekProvider, OllamaProvider
"""

from shift_parser.providers.base             import BaseProvider
from shift_parser.providers.openai_provider  import OpenAIProvider
from shift_parser.providers.deepseek_provider import DeepSeekProvider
from shift_parser.providers.ollama_provider  import OllamaProvider

__all__ = ["BaseProvider", "OpenAIProvider", "DeepSeekProvider", "OllamaProvider"]
