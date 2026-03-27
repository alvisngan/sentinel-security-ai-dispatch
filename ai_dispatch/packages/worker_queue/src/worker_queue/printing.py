"""
printing.py
-----------
Thread-safe printing for use across multiple worker threads.
"""

from __future__ import annotations

import threading
from typing import Any


_print_lock = threading.Lock()


def safe_print(*args: Any, **kwargs: Any) -> None:
    """Drop-in replacement for print() that is safe to call from multiple threads."""
    with _print_lock:
        print(*args, **kwargs)


def print_lock() -> threading.Lock:
    """
    Return the shared print lock directly.

    Use this when you need to hold the lock across multiple print() calls
    to keep a multi-line block together, e.g.:

        with print_lock():
            print("Subject :", subject)
            print("From    :", sender)
    """
    return _print_lock
