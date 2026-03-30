"""
commands/list_recent.py
-----------------------
List recent messages from a mailbox Inbox.

Usage:
    dispatch-list [--top N] [--parse] [--schema NAME] [--provider NAME] [--model NAME]
"""

from __future__ import annotations

import argparse
import sys

from mail.auth import GraphTokenProvider
from mail.config import ConfigError, load_config
from mail.formatting import print_message_summary
from mail.graph_client import GraphClient
from parsing import ShiftParser
from parsing.providers import DeepSeekProvider, OllamaProvider, OpenAIProvider
from parsing.schemas import REGISTRY as SCHEMA_REGISTRY


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="List recent messages from a mailbox Inbox using app-only Microsoft Graph auth."
    )
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--parse", action="store_true",
                   help="Parse each message's bodyPreview with the LLM.")
    p.add_argument("--schema", default="client_request", choices=list(SCHEMA_REGISTRY))
    p.add_argument("--provider", default="ollama", choices=["ollama", "deepseek", "openai"])
    p.add_argument("--model", default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    try:
        config = load_config()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    parser: ShiftParser | None = None
    if args.parse:
        schema = SCHEMA_REGISTRY[args.schema]
        if args.provider == "ollama":
            provider = OllamaProvider(model=args.model or "deepseek-r1:7b")
        elif args.provider == "deepseek":
            provider = DeepSeekProvider(model=args.model or "deepseek-chat")
        else:
            provider = OpenAIProvider(model=args.model or "gpt-4o-mini")
        parser = ShiftParser(provider=provider, schema=schema)

    token_provider = GraphTokenProvider(config)
    client = GraphClient(config, token_provider)

    try:
        profile = client.get_user_mailbox_profile(config.mailbox_user_id)
        messages = client.list_recent_messages(config.mailbox_user_id, top=args.top)
    finally:
        client.close()

    mailbox_label = profile.get("mail") or profile.get("userPrincipalName") or config.mailbox_user_id
    print(f"Mailbox : {profile.get('displayName') or mailbox_label} <{mailbox_label}>")
    print(f"Messages: {len(messages)}")

    for message in messages:
        print_message_summary(message)
        if parser:
            body = message.get("bodyPreview") or ""
            if body.strip():
                try:
                    result = parser.parse(body)
                    result.print_summary()
                except Exception as exc:  # noqa: BLE001
                    print(f"  [parse] Failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
