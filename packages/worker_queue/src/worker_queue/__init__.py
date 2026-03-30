"""
worker_queue
------------
A lightweight background worker queue for decoupling fast producers
from slow consumers across any part of the application.

Exports:
    WorkerQueue   — the main queue class
    safe_print    — thread-safe print() replacement
    print_lock    — the shared print lock, for multi-line atomic output
"""

from .printing import print_lock, safe_print
from .worker import WorkerQueue

__all__ = ["WorkerQueue", "safe_print", "print_lock"]
