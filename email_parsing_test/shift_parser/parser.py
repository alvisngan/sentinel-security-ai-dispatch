"""
shift_parser.parser
--------------------
ShiftParser — the main entry point for the library.
"""

from __future__ import annotations
import json
from shift_parser.providers.base import BaseProvider
from shift_parser.prompts import SYSTEM_PROMPT, USER_TEMPLATE
from shift_parser.schema import ShiftInfo


class ShiftParser:
    """
    Parse shift-scheduling emails using any LLM provider.

    Args:
        provider: Any instance of BaseProvider (OpenAI, DeepSeek, Ollama, …).

    Example:
        from shift_parser import ShiftParser
        from shift_parser.providers import OllamaProvider

        parser = ShiftParser(OllamaProvider(model="deepseek-r1:7b"))
        result = parser.parse(email_text)
        result.print_summary()
    """

    def __init__(self, provider: BaseProvider) -> None:
        self._provider = provider

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, email_content: str) -> ShiftInfo:
        """
        Parse a raw email string and return a ShiftInfo dataclass.

        Args:
            email_content: The full text of the email to parse.

        Returns:
            ShiftInfo with all extracted fields populated.

        Raises:
            ValueError:        If the model returns non-JSON output.
            ConnectionError:   If the provider cannot be reached.
        """
        user_msg = USER_TEMPLATE.format(email_content=email_content)
        raw = self._provider.complete(SYSTEM_PROMPT, user_msg)
        data = self._clean_and_parse(raw)

        info = ShiftInfo.from_dict(data)
        info.provider_name = self._provider.name
        info.model_name    = self._provider.model
        return info

    def parse_file(self, path: str) -> ShiftInfo:
        """Convenience wrapper — read a .txt file and parse it."""
        with open(path, "r", encoding="utf-8") as f:
            return self.parse(f.read())

    # ── Provider access ───────────────────────────────────────────────────────

    @property
    def provider(self) -> BaseProvider:
        return self._provider

    def switch_provider(self, provider: BaseProvider) -> "ShiftParser":
        """
        Return a NEW ShiftParser using a different provider.
        The original instance is unchanged (immutable-style).
        """
        return ShiftParser(provider)

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_and_parse(raw: str) -> dict:
        """Strip markdown fences and parse JSON."""
        text = raw.strip()

        # Strip ``` or ```json fences
        if text.startswith("```"):
            lines = text.splitlines()
            text  = "\n".join(lines[1:])
        if text.endswith("```"):
            lines = text.splitlines()
            text  = "\n".join(lines[:-1])

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Provider returned invalid JSON.\n"
                f"Raw response:\n{raw}\n\n"
                f"JSON error: {exc}"
            ) from exc
