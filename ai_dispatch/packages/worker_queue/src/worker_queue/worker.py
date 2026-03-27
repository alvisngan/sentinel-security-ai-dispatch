"""
worker.py
---------
WorkerQueue: a generic background worker queue.

Decouples a fast producer (e.g. polling an API) from a slow consumer
(e.g. calling an LLM, posting to a scheduling service).

Usage:
    from worker_queue import WorkerQueue

    def process(item):
        ...  # your slow work here

    q = WorkerQueue(handler=process, num_workers=2)
    q.start()
    q.enqueue(some_item)
    q.stop()   # waits for in-flight items to finish
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable

from .printing import safe_print


# Sentinel pushed onto the queue to signal a worker to exit cleanly.
_STOP = object()


class WorkerQueue:
    """
    Thread-safe queue that runs ``handler(item)`` in background worker threads.

    Args:
        handler:     Callable invoked for each enqueued item. Called from a
                     worker thread — must be thread-safe.
        num_workers: Number of parallel worker threads (default: 1).
        maxsize:     Max items buffered in the queue. 0 = unlimited. When the
                     queue is full, ``enqueue()`` blocks — intentional
                     back-pressure to avoid unbounded memory growth.
        name:        Label used in log output (e.g. "parse", "humanity").
    """

    def __init__(
        self,
        handler: Callable[[Any], None],
        *,
        num_workers: int = 1,
        maxsize: int = 0,
        name: str = "worker",
    ) -> None:
        self._handler = handler
        self._num_workers = num_workers
        self._name = name
        self._q: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._threads: list[threading.Thread] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spawn all worker threads. Call once before enqueuing."""
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._run_worker,
                name=f"{self._name}-worker-{i}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """
        Signal all workers to stop and block until they finish.

        Any items still in the queue will be processed before workers exit.
        """
        for _ in self._threads:
            self._q.put(_STOP)
        for t in self._threads:
            t.join()

    # ── Producer-side ─────────────────────────────────────────────────────────

    def enqueue(self, item: Any, *, label: str = "") -> None:
        """
        Add an item to the queue.

        Args:
            item:  The item to process.
            label: Optional short description logged alongside queue depth.
        """
        depth = self._q.qsize() + 1
        suffix = f" '{label}'" if label else ""
        safe_print(f"  [{self._name}] Enqueued{suffix} (queue depth: ~{depth})")
        self._q.put(item)

    def depth(self) -> int:
        """Approximate number of items currently waiting in the queue."""
        return self._q.qsize()

    # ── Consumer-side ─────────────────────────────────────────────────────────

    def _run_worker(self) -> None:
        """Drain the queue until the stop sentinel is received."""
        thread_name = threading.current_thread().name
        safe_print(f"  [{self._name}] Worker started: {thread_name}")

        while True:
            item = self._q.get()
            try:
                if item is _STOP:
                    safe_print(f"  [{self._name}] Worker stopping: {thread_name}")
                    return

                self._handler(item)

            except Exception as exc:  # noqa: BLE001
                safe_print(f"  [{self._name}] Error in {thread_name}: {exc}")
            finally:
                self._q.task_done()
