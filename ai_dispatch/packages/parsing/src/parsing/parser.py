"""
parser.py
---------
ShiftParser — the main class that connects a provider to a schema.

Usage:
    from parser import ShiftParser
    from providers import OllamaProvider
    from schemas import employee_swap

    parser = ShiftParser(provider=OllamaProvider(), schema=employee_swap)
    result = parser.parse(email_text)
    result.print_summary()
"""

import json
import re


# Matches <think>...</think> blocks emitted by reasoning models (e.g. deepseek-r1).
# re.DOTALL makes '.' match newlines so the whole block is captured in one go.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _extract_json(raw: str) -> str:
    """
    Clean raw LLM output down to a bare JSON string.

    Handles (in order):
      1. <think>...</think> reasoning blocks  (deepseek-r1, qwq, etc.)
      2. ```json ... ``` or ``` ... ``` markdown fences
      3. Leading/trailing whitespace
    """
    # 1. Strip reasoning block first — it may contain curly braces that confuse
    #    later steps.
    text = _THINK_RE.sub("", raw).strip()

    # 2. Strip markdown fences if present.
    if text.startswith("```"):
        # Remove the opening fence line (e.g. "```json")
        text = "\n".join(text.splitlines()[1:])
    if text.endswith("```"):
        text = "\n".join(text.splitlines()[:-1])

    return text.strip()


class ShiftParser:
    """
    Parses a shift-scheduling email using a given LLM provider and schema.

    Args:
        provider: An LLM provider (OpenAIProvider, DeepSeekProvider, OllamaProvider).
        schema:   A schema module from the schemas/ folder. Each schema module
                  contains a SYSTEM_PROMPT and a dataclass with a from_dict() method.

    The flow is:
        1. Send the email text to the LLM using the schema's SYSTEM_PROMPT.
        2. The LLM returns a JSON string.
        3. Parse the JSON into the schema's dataclass.
        4. Return the dataclass instance.
    """

    def __init__(self, provider, schema):
        self.provider = provider
        self.schema   = schema

    def parse(self, email_text: str):
        """
        Parse a raw email string and return a populated dataclass.

        Args:
            email_text: The full text of the email.

        Returns:
            A dataclass instance defined in the schema module,
            with all extracted fields filled in.
        """
        # Ask the LLM to extract the shift info
        raw = self.provider.complete(
            system = self.schema.SYSTEM_PROMPT,
            user   = f"Parse this shift email:\n\n{email_text}",
        )

        # Clean the raw response before parsing
        text = _extract_json(raw)

        # Parse the JSON and build the dataclass
        data   = json.loads(text)
        result = self.schema.Result.from_dict(data)

        # Stamp which provider/model was used
        result.provider_name = self.provider.name
        result.model_name    = self.provider.model

        return result
