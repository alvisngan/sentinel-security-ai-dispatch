"""
commands/watch_parse.py
-----------------------
Watch a mailbox Inbox for new messages and parse each one with the LLM.

New messages are placed on an in-process queue so that slow LLM parsing never
blocks email detection.  One or more worker threads drain the queue in the
background.

Unlike ``dispatch-watch --parse``, this command:
  • Always fetches the **full message body** (not just bodyPreview).
  • Treats parsing as the primary purpose, not an optional flag.
  • Emits structured JSON per message when --json is passed.

Usage:
    dispatch-watch-parse
    dispatch-watch-parse --schema employee_swap --provider openai --model gpt-4o
    dispatch-watch-parse --json --poll-seconds 30
    dispatch-watch-parse --workers 4
    dispatch-watch-parse --reset-state --print-initial
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import queue
import sys
import threading
import time
from typing import Any

from mail.auth import GraphTokenProvider
from mail.config import ConfigError, load_config
from mail.formatting import print_message_summary
from mail.graph_client import GraphApiError, GraphClient
from mail.state_store import StateStore, WatchState
from parsing import ShiftParser
from parsing.providers import DeepSeekProvider, OllamaProvider, OpenAIProvider
from parsing.schemas import REGISTRY as SCHEMA_REGISTRY


RECOVERABLE_SYNC_ERRORS = {
    "SyncStateNotFound",
    "ResyncRequired",
    "InvalidSyncStateData",
}

# Sentinel pushed onto the queue to signal workers to exit cleanly.
_STOP = object()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Watch a mailbox Inbox for new messages and parse each one with the LLM. "
            "Fetches the full message body for accurate parsing. "
            "Parsing is handled by a background queue so that slow LLM calls never "
            "delay email detection."
        )
    )
    p.add_argument("--schema", default="client_request",
                   choices=list(SCHEMA_REGISTRY),
                   help="Schema to parse against (default: client_request).")
    p.add_argument("--provider", default="ollama",
                   choices=["ollama", "deepseek", "openai"])
    p.add_argument("--model", default=None,
                   help="Model name. Defaults: ollama=deepseek-r1:14b, "
                        "deepseek=deepseek-chat, openai=gpt-4o-mini")
    p.add_argument("--json", action="store_true", dest="output_json",
                   help="Emit a JSON object per message instead of a human-readable summary.")
    p.add_argument("--poll-seconds", type=int, default=None,
                   help="Override POLL_SECONDS from the environment.")
    p.add_argument("--page-size", type=int, default=25)
    p.add_argument("--workers", type=int, default=1,
                   help="Number of parallel parse workers (default: 1). "
                        "Raise this if your LLM provider supports concurrent requests.")
    p.add_argument("--queue-size", type=int, default=0,
                   help="Maximum number of messages buffered in the parse queue. "
                        "0 means unlimited (default).")
    p.add_argument("--reset-state", action="store_true",
                   help="Delete saved delta state and rebuild baseline.")
    p.add_argument("--print-initial", action="store_true",
                   help="Parse and print messages found during the initial baseline sync.")
    return p.parse_args()


# ── Provider / parser construction ────────────────────────────────────────────

def build_parser(args: argparse.Namespace) -> ShiftParser:
    schema = SCHEMA_REGISTRY[args.schema]

    if args.provider == "ollama":
        provider = OllamaProvider(model=args.model or "deepseek-r1:14b")
    elif args.provider == "deepseek":
        provider = DeepSeekProvider(model=args.model or "deepseek-chat")
    else:
        provider = OpenAIProvider(model=args.model or "gpt-4o-mini")

    return ShiftParser(provider=provider, schema=schema)


# ── Print lock ────────────────────────────────────────────────────────────────
# Multiple worker threads may print concurrently; a lock keeps output coherent.

_print_lock = threading.Lock()


def _safe_print(*args: Any, **kwargs: Any) -> None:
    with _print_lock:
        print(*args, **kwargs)


# ── Per-message handling ──────────────────────────────────────────────────────

def handle_message(
    message: dict,
    client: GraphClient,
    mailbox_user_id: str,
    parser: ShiftParser,
    output_json: bool,
) -> None:
    """Fetch full body for *message*, parse it, and print results."""
    with _print_lock:
        print_message_summary(message)

    body: str = (
        message.get("body", {}).get("content")
        or _fetch_full_body(client, mailbox_user_id, message.get("id", ""))
    )

    if not body.strip():
        _safe_print("  [parse] Message body is empty — skipping.")
        return

    try:
        result = parser.parse(body)
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"  [parse] Failed: {exc}")
        return

    if output_json:
        _safe_print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        with _print_lock:
            result.print_summary()


def _fetch_full_body(client: GraphClient, mailbox_user_id: str, message_id: str) -> str:
    if not message_id:
        return ""
    try:
        msg = client.get_message(mailbox_user_id, message_id)
        return msg.get("body", {}).get("content", "")
    except GraphApiError as exc:
        _safe_print(f"  [parse] Could not fetch full body: {exc}")
        return ""


# ── Parse queue / worker threads ──────────────────────────────────────────────

class ParseQueue:
    """
    Thread-safe queue that decouples email detection from LLM parsing.

    The producer (poll loop) calls ``enqueue()``.
    One or more worker threads call ``_run_worker()`` in the background.
    """

    def __init__(
        self,
        client: GraphClient,
        mailbox_user_id: str,
        parser: ShiftParser,
        output_json: bool,
        *,
        num_workers: int = 1,
        maxsize: int = 0,
    ) -> None:
        self._client = client
        self._mailbox_user_id = mailbox_user_id
        self._parser = parser
        self._output_json = output_json
        self._q: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._workers: list[threading.Thread] = []
        self._num_workers = num_workers

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spawn worker threads."""
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._run_worker,
                name=f"parse-worker-{i}",
                daemon=True,
            )
            t.start()
            self._workers.append(t)

    def stop(self) -> None:
        """Signal all workers to finish and wait for them to drain the queue."""
        for _ in self._workers:
            self._q.put(_STOP)
        for t in self._workers:
            t.join()

    # ── Producer-side ─────────────────────────────────────────────────────────

    def enqueue(self, message: dict) -> None:
        """
        Put a message on the queue.

        If ``maxsize`` was set and the queue is full this will block the caller
        until a worker frees a slot — intentional back-pressure so we don't
        accumulate unbounded memory when the LLM is very slow.
        """
        subject = message.get("subject") or "(no subject)"
        qsize = self._q.qsize()
        _safe_print(
            f"  [queue] Enqueued: '{subject}' "
            f"(queue depth after: ~{qsize + 1})"
        )
        self._q.put(message)

    # ── Consumer-side ─────────────────────────────────────────────────────────

    def _run_worker(self) -> None:
        """Drain the queue until the stop sentinel is received."""
        thread_name = threading.current_thread().name
        _safe_print(f"  [queue] Worker started: {thread_name}")

        while True:
            item = self._q.get()
            try:
                if item is _STOP:
                    _safe_print(f"  [queue] Worker stopping: {thread_name}")
                    return

                handle_message(
                    item,
                    self._client,
                    self._mailbox_user_id,
                    self._parser,
                    self._output_json,
                )
            except Exception as exc:  # noqa: BLE001
                _safe_print(f"  [queue] Unhandled error in {thread_name}: {exc}")
            finally:
                self._q.task_done()


# ── Bootstrap / state helpers (mirrors watch.py) ──────────────────────────────

def bootstrap(
    client: GraphClient,
    state_store: StateStore,
    mailbox_user_id: str,
    page_size: int,
    print_initial: bool,
    parse_queue: ParseQueue,
) -> WatchState:
    print("No saved delta state found. Building initial baseline from Inbox...")
    messages, delta_link = client.consume_message_delta_round(
        mailbox_user_id, delta_url=None, page_size=page_size, created_only=True,
    )
    print(f"Initial baseline complete. {len(messages)} existing message(s) observed.")

    if print_initial:
        for message in messages:
            parse_queue.enqueue(message)
    else:
        print("Existing messages skipped. Future newly-created messages will be parsed.")

    state = WatchState(mailbox_user_id=mailbox_user_id, delta_url=delta_link)
    state_store.save(state)
    return state


def ensure_state_matches_mailbox(
    state_store: StateStore,
    state: WatchState,
    mailbox_user_id: str,
) -> WatchState:
    saved = (state.mailbox_user_id or "").strip().casefold()
    current = mailbox_user_id.strip().casefold()

    if state.delta_url and saved and saved != current:
        print("Saved delta state belongs to a different mailbox. Resetting...")
        state_store.reset()
        return WatchState()

    if state.delta_url and not saved:
        print("Saved delta state is from an older format. Resetting...")
        state_store.reset()
        return WatchState()

    return state


# ── Watch-and-parse loop ──────────────────────────────────────────────────────

def watch_parse_loop(
    client: GraphClient,
    state_store: StateStore,
    mailbox_user_id: str,
    state: WatchState,
    *,
    page_size: int,
    poll_seconds: int,
    parse_queue: ParseQueue,
) -> None:
    """
    Poll for new messages and enqueue them for parsing.

    This loop never calls ``handle_message`` directly — it only puts work on
    the queue, so a slow LLM call in a worker never delays the next poll.
    """
    while True:
        try:
            messages, new_delta_link = client.consume_message_delta_round(
                mailbox_user_id,
                delta_url=state.delta_url,
                page_size=page_size,
                created_only=True,
            )
            state.delta_url = new_delta_link
            state.mailbox_user_id = mailbox_user_id
            state_store.save(state)

            if messages:
                print(f"\nDetected {len(messages)} new message(s) — enqueuing for parse.")
                for message in messages:
                    parse_queue.enqueue(message)
            else:
                print(f"No new messages. Sleeping {poll_seconds}s...")

            time.sleep(poll_seconds)

        except KeyboardInterrupt:
            print("\nStopped by user. Waiting for in-flight parses to finish...")
            return

        except GraphApiError as exc:
            should_resync = (
                exc.status_code in {404, 409, 410}
                or exc.error_code in RECOVERABLE_SYNC_ERRORS
            )
            if should_resync:
                print("Saved delta state invalid. Rebuilding baseline...", file=sys.stderr)
                state_store.reset()
                state = bootstrap(
                    client, state_store, mailbox_user_id,
                    page_size, False, parse_queue,
                )
                continue
            raise


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()

    try:
        config = load_config()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    poll_seconds = args.poll_seconds or config.poll_seconds
    state_store = StateStore(config.state_file)
    if args.reset_state:
        state_store.reset()

    parser = build_parser(args)

    token_provider = GraphTokenProvider(config)
    client = GraphClient(config, token_provider)

    try:
        profile = client.get_user_mailbox_profile(config.mailbox_user_id)
        mailbox_label = profile.get("mail") or profile.get("userPrincipalName") or config.mailbox_user_id
        display_name = profile.get("displayName") or mailbox_label
        print(f"Watching mailbox : {display_name} <{mailbox_label}>")
        print(f"Schema           : {args.schema}")
        print(f"Provider         : {parser.provider.name} / {parser.provider.model}")
        print(f"Polling every    : {poll_seconds}s")
        print(f"State file       : {config.state_file}")
        print(f"Parse workers    : {args.workers}")
        print(f"Queue max size   : {'unlimited' if args.queue_size == 0 else args.queue_size}")

        # Validate inbox access before entering the loop.
        client.list_recent_messages(config.mailbox_user_id, top=1)

        parse_queue = ParseQueue(
            client,
            config.mailbox_user_id,
            parser,
            args.output_json,
            num_workers=args.workers,
            maxsize=args.queue_size,
        )
        parse_queue.start()

        try:
            state = state_store.load()
            state = ensure_state_matches_mailbox(state_store, state, config.mailbox_user_id)
            if not state.delta_url:
                state = bootstrap(
                    client, state_store, config.mailbox_user_id,
                    args.page_size, args.print_initial, parse_queue,
                )

            watch_parse_loop(
                client, state_store, config.mailbox_user_id, state,
                page_size=args.page_size,
                poll_seconds=poll_seconds,
                parse_queue=parse_queue,
            )
        finally:
            # Always drain the queue cleanly on exit (Ctrl-C or error).
            parse_queue.stop()

        return 0

    except GraphApiError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
