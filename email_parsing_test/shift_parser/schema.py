"""
shift_parser.schema
-------------------
Typed dataclasses that represent a parsed shift-change email.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Person:
    name:  Optional[str] = None
    email: Optional[str] = None
    role:  Optional[str] = None

    def display(self) -> str:
        parts = [self.name or "Unknown"]
        if self.role:
            parts.append(f"({self.role})")
        if self.email:
            parts.append(f"<{self.email}>")
        return " ".join(parts)


@dataclass
class Shift:
    date:       Optional[str] = None   # YYYY-MM-DD
    start_time: Optional[str] = None   # HH:MM  (24 h)
    end_time:   Optional[str] = None   # HH:MM  (24 h)
    location:   Optional[str] = None
    department: Optional[str] = None
    position:   Optional[str] = None

    def display(self, label: str = "Shift") -> str:
        lines = [f"  {label}:"]
        if self.date:
            lines.append(f"    Date     : {self.date}")
        if self.start_time or self.end_time:
            lines.append(f"    Time     : {self.start_time or '?'} – {self.end_time or '?'}")
        if self.location:
            lines.append(f"    Location : {self.location}")
        if self.department:
            lines.append(f"    Dept     : {self.department}")
        if self.position:
            lines.append(f"    Position : {self.position}")
        return "\n".join(lines)


@dataclass
class ShiftInfo:
    # ── Change metadata ───────────────────────────────────────────────────────
    shift_change_type: str = "unknown"
    urgency:           str = "low"
    approval_required: bool = False
    approved_by:       Optional[str] = None
    reason:            Optional[str] = None
    notes:             Optional[str] = None
    action_items:      list[str] = field(default_factory=list)

    # ── People ────────────────────────────────────────────────────────────────
    requestor:          Optional[Person] = None
    covering_employee:  Optional[Person] = None

    # ── Shifts ────────────────────────────────────────────────────────────────
    original_shift: Optional[Shift] = None
    new_shift:      Optional[Shift] = None   # populated for swaps / modifications

    # ── Source metadata (set by ShiftParser) ─────────────────────────────────
    provider_name: str = ""
    model_name:    str = ""

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self) -> str:
        """Return a formatted multi-line summary string."""
        D = "─" * 56
        lines = [
            f"\n{'═' * 56}",
            "  SHIFT CHANGE SUMMARY",
            f"{'═' * 56}",
            f"  Type     : {(self.shift_change_type or 'unknown').upper()}",
            f"  Urgency  : {(self.urgency or 'unknonw').upper()}",
            f"  Approval : {'Required' if self.approval_required else 'Not required'}",
        ]
        if self.approved_by:
            lines.append(f"  Approved : {self.approved_by}")
        lines.append(f"  Provider : {self.provider_name}  ({self.model_name})")
        lines.append(D)

        if self.requestor:
            lines.append(f"  Requestor : {self.requestor.display()}")
        if self.covering_employee:
            lines.append(f"  Covering  : {self.covering_employee.display()}")
        lines.append(D)

        if self.original_shift:
            lines.append(self.original_shift.display("Original Shift"))
        if self.new_shift:
            lines.append(self.new_shift.display("New / Swap Shift"))
        lines.append(D)

        if self.reason:
            lines.append(f"  Reason: {self.reason}")
        if self.notes:
            lines.append(f"  Notes : {self.notes}")
        if self.action_items:
            lines.append("  Action Items:")
            for item in self.action_items:
                lines.append(f"    • {item}")

        lines.append(f"{'═' * 56}\n")
        return "\n".join(lines)

    def print_summary(self) -> None:
        print(self.summary())

    # ── Factories ─────────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict) -> "ShiftInfo":
        """Build a ShiftInfo from a raw dict (as returned by the LLM)."""

        def _person(d: Optional[dict]) -> Optional[Person]:
            return Person(**{k: d.get(k) for k in ("name", "email", "role")}) if d else None

        def _shift(d: Optional[dict]) -> Optional[Shift]:
            if not d:
                return None
            return Shift(**{k: d.get(k) for k in
                            ("date", "start_time", "end_time", "location", "department", "position")})

        return cls(
            shift_change_type = data.get("shift_change_type", "unknown"),
            urgency           = data.get("urgency", "low"),
            approval_required = bool(data.get("approval_required", False)),
            approved_by       = data.get("approved_by"),
            reason            = data.get("reason"),
            notes             = data.get("notes"),
            action_items      = data.get("action_items") or [],
            requestor         = _person(data.get("requestor")),
            covering_employee = _person(data.get("covering_employee")),
            original_shift    = _shift(data.get("original_shift")),
            new_shift         = _shift(data.get("new_shift")),
        )
