"""
commands/watch_parse.py
-----------------------
Watch a mailbox Inbox for new messages and parse each one with the LLM.

Unlike ``dispatch-watch --parse``, this command:
  • Always fetches the **full message body** (not just bodyPreview).
  • Treats parsing as the primary purpose, not an optional flag.
  • Emits structured JSON per message when --json is passed.

Usage:
    dispatch-watch-parse
    dispatch-watch-parse --schema employee_swap --provider openai --model gpt-4o
    dispatch-watch-parse --json --poll-seconds 30
    dispatch-watch-parse --reset-state --print-initial
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time

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


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Watch a mailbox Inbox for new messages and parse each one with the LLM. "
            "Fetches the full message body for accurate parsing."
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


# ── Per-message handling ──────────────────────────────────────────────────────

def handle_message(
    message: dict,
    client: GraphClient,
    mailbox_user_id: str,
    parser: ShiftParser,
    output_json: bool,
) -> None:
    """Fetch full body for *message*, parse it, and print results."""
    print_message_summary(message)

    # Prefer already-fetched body; fall back to a targeted Graph call.
    body: str = (
        message.get("body", {}).get("content")
        or _fetch_full_body(client, mailbox_user_id, message.get("id", ""))
    )

    if not body.strip():
        print("  [parse] Message body is empty — skipping.")
        return

    try:
        result = parser.parse(body)
    except Exception as exc:  # noqa: BLE001
        print(f"  [parse] Failed: {exc}")
        return

    if output_json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        result.print_summary()


def _fetch_full_body(client: GraphClient, mailbox_user_id: str, message_id: str) -> str:
    """Retrieve the full body of a single message from the Graph API."""
    if not message_id:
        return ""
    try:
        msg = client.get_message(mailbox_user_id, message_id)
        return msg.get("body", {}).get("content", "")
    except GraphApiError as exc:
        print(f"  [parse] Could not fetch full body: {exc}")
        return ""


# ── Bootstrap / state helpers (mirrors watch.py) ──────────────────────────────

def bootstrap(
    client: GraphClient,
    state_store: StateStore,
    mailbox_user_id: str,
    page_size: int,
    print_initial: bool,
    parser: ShiftParser,
    output_json: bool,
) -> WatchState:
    print("No saved delta state found. Building initial baseline from Inbox...")
    messages, delta_link = client.consume_message_delta_round(
        mailbox_user_id, delta_url=None, page_size=page_size, created_only=True,
    )
    print(f"Initial baseline complete. {len(messages)} existing message(s) observed.")

    if print_initial:
        for message in messages:
            handle_message(message, client, mailbox_user_id, parser, output_json)
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
    parser: ShiftParser,
    output_json: bool,
) -> None:
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
                print(f"\nDetected {len(messages)} new message(s).")
                for message in messages:
                    handle_message(message, client, mailbox_user_id, parser, output_json)
            else:
                print(f"No new messages. Sleeping {poll_seconds}s...")

            time.sleep(poll_seconds)

        except KeyboardInterrupt:
            print("\nStopped by user.")
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
                    page_size, False, parser, output_json,
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

        # Validate inbox access before entering the loop.
        client.list_recent_messages(config.mailbox_user_id, top=1)

        state = state_store.load()
        state = ensure_state_matches_mailbox(state_store, state, config.mailbox_user_id)
        if not state.delta_url:
            state = bootstrap(
                client, state_store, config.mailbox_user_id,
                args.page_size, args.print_initial, parser, args.output_json,
            )

        watch_parse_loop(
            client, state_store, config.mailbox_user_id, state,
            page_size=args.page_size,
            poll_seconds=poll_seconds,
            parser=parser,
            output_json=args.output_json,
        )
        return 0

    except GraphApiError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
