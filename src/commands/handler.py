"""
commands/handler.py
-------------------
Per-message handling: fetch full body, parse with LLM, print result.
"""

from __future__ import annotations

import dataclasses
import json

from mail.formatting import print_message_summary
from mail.graph_client import GraphApiError, GraphClient
from parsing import ShiftParser
from worker_queue import print_lock, safe_print


def handle_message(
    message: dict,
    client: GraphClient,
    mailbox_user_id: str,
    parser: ShiftParser,
    output_json: bool,
) -> None:
    """Fetch the full body for *message*, parse it with the LLM, and print results."""
    with print_lock():
        print_message_summary(message)

    body: str = (
        message.get("body", {}).get("content")
        or _fetch_full_body(client, mailbox_user_id, message.get("id", ""))
    )

    if not body.strip():
        safe_print("  [parse] Message body is empty — skipping.")
        return

    try:
        result = parser.parse(body)
    except Exception as exc:  # noqa: BLE001
        safe_print(f"  [parse] Failed: {exc}")
        return

    if output_json:
        safe_print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        with print_lock():
            result.print_summary()


def _fetch_full_body(client: GraphClient, mailbox_user_id: str, message_id: str) -> str:
    """Retrieve the full body of a single message from the Graph API."""
    if not message_id:
        return ""
    try:
        msg = client.get_message(mailbox_user_id, message_id)
        return msg.get("body", {}).get("content", "")
    except GraphApiError as exc:
        safe_print(f"  [parse] Could not fetch full body: {exc}")
        return ""
