"""
shift_parser.providers.base
----------------------------
Abstract base class that every LLM provider must implement.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    Minimal interface all providers must satisfy.

    Subclasses only need to implement `complete()`.  The ShiftParser calls
    `complete(system, user)` and expects a plain-text string back; JSON
    parsing is handled upstream.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider label, e.g. 'OpenAI'."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier used for this provider instance."""

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Send a single-turn chat completion and return the raw text response.

        Args:
            system_prompt: The system / instruction message.
            user_message:  The user message containing email content.

        Returns:
            Raw text from the model (should be JSON, but may include fences).
        """
