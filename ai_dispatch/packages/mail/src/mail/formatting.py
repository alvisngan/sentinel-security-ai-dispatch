from __future__ import annotations

from datetime import datetime
from typing import Any



def format_sender(message: dict[str, Any]) -> str:
    sender = message.get("from") or {}
    email = sender.get("emailAddress") or {}
    name = email.get("name") or "Unknown Sender"
    address = email.get("address") or "unknown@example.com"
    return f"{name} <{address}>"



def format_received(value: str | None) -> str:
    if not value:
        return "unknown time"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.isoformat()
    except ValueError:
        return value



def print_message_summary(message: dict[str, Any]) -> None:
    subject = message.get("subject") or "(no subject)"
    preview = (message.get("bodyPreview") or "").replace("\r", " ").replace("\n", " ").strip()
    if len(preview) > 160:
        preview = preview[:157] + "..."

    print("-" * 80)
    print(f"Subject : {subject}")
    print(f"From    : {format_sender(message)}")
    print(f"Received: {format_received(message.get('receivedDateTime'))}")
    print(f"Read    : {message.get('isRead')}")
    print(f"Graph ID: {message.get('id')}")
    if preview:
        print(f"Preview : {preview}")
