"""
schemas/employee_cover.py
--------------------------
Schema for employee shift COVER request emails.

A cover is when one employee needs someone else to take their shift.
Only one shift is involved (the one being given away).
The covering employee may or may not be named.

Example email:
    "I'm sick and can't make my Friday night shift (Dec 6, 6PM-2AM).
     Can anyone cover? - Mike"
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Discription  ──────────────────────────────────────────────────────────────
DESCRIPTION = "An EMPLOYEE asking someone to cover their shift"

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a shift scheduling assistant. Extract shift cover request details from the email.

Respond with a single valid JSON object only — no markdown, no explanation.

{
  "requesting_employee": {
    "name": "string",
    "email": "string",
    "role": "string"
  },
  "covering_employee": {
    "name": "string",
    "email": "string",
    "role": "string"
  },
  "shift_to_cover": {
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "string",
    "department": "string"
  },
  "reason": "string",
  "urgency": "low | medium | high | critical",
  "manager_approval_needed": true or false,
  "action_items": ["list of next steps"]
}

Rules:
- Use 24-hour HH:MM format for all times.
- Use YYYY-MM-DD for all dates.
- covering_employee can be null if no one has been named yet.
- Use null for any field not mentioned in the email.
"""


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class Employee:
    """A person involved in the cover request."""
    name:  Optional[str] = None
    email: Optional[str] = None
    role:  Optional[str] = None


@dataclass
class Shift:
    """The single shift that needs to be covered. Belongs to one person."""
    date:       Optional[str] = None
    start_time: Optional[str] = None
    end_time:   Optional[str] = None
    location:   Optional[str] = None
    department: Optional[str] = None


@dataclass
class Result:
    """
    The fully parsed result of an employee shift cover request email.
    Returned by ShiftParser.parse() when using this schema.
    """
    requesting_employee:    Optional[Employee] = None   # person who needs a cover
    covering_employee:      Optional[Employee] = None   # person offering to cover (may be None)
    shift_to_cover:         Optional[Shift]    = None   # the shift that needs covering
    reason:                 Optional[str]      = None
    urgency:                str                = "low"
    manager_approval_needed: bool              = False
    action_items:           list[str]          = field(default_factory=list)

    # Set by ShiftParser after parsing — not from the LLM
    provider_name: str = ""
    model_name:    str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Result":
        """Build a Result from the raw JSON dict returned by the LLM."""

        def to_employee(d):
            if not d:
                return None
            return Employee(name=d.get("name"), email=d.get("email"), role=d.get("role"))

        def to_shift(d):
            if not d:
                return None
            return Shift(
                date       = d.get("date"),
                start_time = d.get("start_time"),
                end_time   = d.get("end_time"),
                location   = d.get("location"),
                department = d.get("department"),
            )

        return cls(
            requesting_employee     = to_employee(data.get("requesting_employee")),
            covering_employee       = to_employee(data.get("covering_employee")),
            shift_to_cover          = to_shift(data.get("shift_to_cover")),
            reason                  = data.get("reason"),
            urgency                 = data.get("urgency") or "low",
            manager_approval_needed = bool(data.get("manager_approval_needed", False)),
            action_items            = data.get("action_items") or [],
        )

    def print_summary(self):
        """Print a readable summary to the terminal."""
        D = "─" * 50
        print(f"\n{'═' * 50}")
        print("  EMPLOYEE SHIFT COVER REQUEST")
        print(f"{'═' * 50}")
        print(f"  Provider : {self.provider_name} ({self.model_name})")
        print(f"  Urgency  : {self.urgency.upper()}")
        print(D)

        if self.requesting_employee:
            e = self.requesting_employee
            print(f"  Needs cover : {e.name or 'Unknown'}" +
                  (f" ({e.role})" if e.role else "") +
                  (f" <{e.email}>" if e.email else ""))

        if self.covering_employee:
            e = self.covering_employee
            print(f"  Covering    : {e.name or 'Unknown'}" +
                  (f" ({e.role})" if e.role else "") +
                  (f" <{e.email}>" if e.email else ""))
        else:
            print("  Covering    : Not yet assigned")
        print(D)

        if self.shift_to_cover:
            s = self.shift_to_cover
            print(f"  Shift  : {s.date}  {s.start_time or '?'} – {s.end_time or '?'}" +
                  (f"  @ {s.location}" if s.location else ""))
            if s.department:
                print(f"  Dept   : {s.department}")
        print(D)

        if self.reason:
            print(f"  Reason   : {self.reason}")
        print(f"  Approval : {'Required' if self.manager_approval_needed else 'Not required'}")
        if self.action_items:
            print("  Actions  :")
            for item in self.action_items:
                print(f"    • {item}")

        print(f"{'═' * 50}\n")
