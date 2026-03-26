"""
commands/watch.py
-----------------
Watch a mailbox Inbox for new messages and optionally parse them.

Usage:
    dispatch-watch [--parse] [--schema client_request] [--provider ollama] ...

    --parse           Pass each new message's bodyPreview through ShiftParser.
    --schema NAME     Which schema to use: client_request | employee_cover | employee_swap
                      (default: client_request)
    --provider NAME   LLM provider: ollama | deepseek | openai  (default: ollama)
    --model NAME      Model name passed to the provider.
    --poll-seconds N  Override POLL_SECONDS from the environment.
    --page-size N     Maximum messages per Graph page during delta sync.
    --reset-state     Delete saved delta state and rebuild baseline.
    --print-initial   Print messages found during the initial baseline sync.
"""

from __future__ import annotations

import argparse
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
            "Watch a mailbox Inbox for newly created messages using app-only "
            "Microsoft Graph auth and the messages delta API."
        )
    )
    p.add_argument("--poll-seconds", type=int, default=None)
    p.add_argument("--page-size", type=int, default=25)
    p.add_argument("--reset-state", action="store_true")
    p.add_argument("--print-initial", action="store_true",
                   help="Print messages found during the initial baseline sync.")

    # Parsing options
    p.add_argument("--parse", action="store_true",
                   help="Parse each new message with the LLM after printing its summary.")
    p.add_argument("--schema", default="client_request",
                   choices=list(SCHEMA_REGISTRY),
                   help="Schema to use when --parse is set.")
    p.add_argument("--provider", default="ollama",
                   choices=["ollama", "deepseek", "openai"])
    p.add_argument("--model", default=None,
                   help="Model name. Defaults: ollama=deepseek-r1:7b, deepseek=deepseek-chat, "
                        "openai=gpt-4o-mini")
    return p.parse_args()


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_parser(args: argparse.Namespace) -> ShiftParser | None:
    """Return a ShiftParser if --parse was requested, else None."""
    if not args.parse:
        return None

    schema = SCHEMA_REGISTRY[args.schema]

    if args.provider == "ollama":
        provider = OllamaProvider(model=args.model or "deepseek-r1:7b")
    elif args.provider == "deepseek":
        provider = DeepSeekProvider(model=args.model or "deepseek-chat")
    else:
        provider = OpenAIProvider(model=args.model or "gpt-4o-mini")

    print(f"Parsing enabled  : schema={args.schema}  provider={provider.name}/{provider.model}")
    return ShiftParser(provider=provider, schema=schema)


def maybe_parse(message: dict, parser: ShiftParser | None) -> None:
    """If a parser is configured, run it on the message body preview."""
    if parser is None:
        return

    body = message.get("bodyPreview") or message.get("body", {}).get("content") or ""
    if not body.strip():
        print("  [parse] No body content available.")
        return

    try:
        result = parser.parse(body)
        result.print_summary()
    except Exception as exc:  # noqa: BLE001
        print(f"  [parse] Failed: {exc}")


def validate_inbox_access(client: GraphClient, mailbox_user_id: str) -> None:
    client.list_recent_messages(mailbox_user_id, top=1)


# ── Bootstrap / state ─────────────────────────────────────────────────────────

def bootstrap(
    client: GraphClient,
    state_store: StateStore,
    mailbox_user_id: str,
    page_size: int,
    print_initial: bool,
    parser: ShiftParser | None,
) -> WatchState:
    print("No saved delta state found. Building initial baseline from Inbox...")
    messages, delta_link = client.consume_message_delta_round(
        mailbox_user_id, delta_url=None, page_size=page_size, created_only=True,
    )
    print(f"Initial baseline complete. {len(messages)} existing message(s) observed.")

    if print_initial:
        for message in messages:
            print_message_summary(message)
            maybe_parse(message, parser)
    else:
        print("Existing messages not printed. Future newly-created messages will be shown.")

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


# ── Watch loop ────────────────────────────────────────────────────────────────

def watch_loop(
    client: GraphClient,
    state_store: StateStore,
    mailbox_user_id: str,
    state: WatchState,
    *,
    page_size: int,
    poll_seconds: int,
    parser: ShiftParser | None,
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
                    print_message_summary(message)
                    maybe_parse(message, parser)
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
                    page_size, False, parser,
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
        print(f"Polling every    : {poll_seconds}s")
        print(f"State file       : {config.state_file}")

        validate_inbox_access(client, config.mailbox_user_id)

        state = state_store.load()
        state = ensure_state_matches_mailbox(state_store, state, config.mailbox_user_id)
        if not state.delta_url:
            state = bootstrap(
                client, state_store, config.mailbox_user_id,
                args.page_size, args.print_initial, parser,
            )

        watch_loop(
            client, state_store, config.mailbox_user_id, state,
            page_size=args.page_size,
            poll_seconds=poll_seconds,
            parser=parser,
        )
        return 0

    except GraphApiError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
