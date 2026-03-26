from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WatchState:
    mailbox_user_id: str | None = None
    delta_url: str | None = None


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> WatchState:
        if not self.path.exists():
            return WatchState()

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return WatchState(
            mailbox_user_id=raw.get("mailbox_user_id"),
            delta_url=raw.get("delta_url"),
        )

    def save(self, state: WatchState) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "mailbox_user_id": state.mailbox_user_id,
                    "delta_url": state.delta_url,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
