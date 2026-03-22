"""
shift_parser
============
Parse shift-scheduling emails using any supported LLM backend.

Quick start
-----------
    from shift_parser import ShiftParser, providers

    # OpenAI
    parser = ShiftParser(providers.OpenAIProvider(api_key="sk-..."))

    # DeepSeek cloud
    parser = ShiftParser(providers.DeepSeekProvider(api_key="ds-..."))

    # Local Ollama (no key needed)
    parser = ShiftParser(providers.OllamaProvider(model="deepseek-r1:7b"))

    result = parser.parse(email_text)   # returns ShiftInfo dataclass
    print(result.summary())             # pretty-print to stdout
    print(result.to_dict())             # plain dict
    print(result.to_json())             # JSON string
"""

from shift_parser.parser import ShiftParser
from shift_parser.schema import ShiftInfo, Shift, Person
from shift_parser import providers

__all__ = ["ShiftParser", "ShiftInfo", "Shift", "Person", "providers"]
__version__ = "1.0.0"
