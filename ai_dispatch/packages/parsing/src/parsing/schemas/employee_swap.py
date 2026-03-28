"""
schemas/employee_swap.py
------------------------
Schema for employee shift SWAP emails.

A swap is when two employees trade shifts with each other.
Both employees and both shifts are captured.

Example email:
    "I'd like to swap my Saturday Dec 14 shift (9AM-5PM) with Tom Bradley.
     He'll take my shift and I'll take his Sunday Dec 15 shift (2PM-10PM)."
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Discription ───────────────────────────────────────────────────────────────
DESCRIPTION = "An EMPLOYEE asking to swap a shift with a colleague"

# ── Prompt ────────────────────────────────────────────────────────────────────
# This is the instruction sent to the LLM. It defines exactly what
# fields to extract and what JSON structure to return.

SYSTEM_PROMPT = """
You are a shift scheduling assistant. Extract shift swap details from the email.

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
  "shift_given_away": {
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "string"
  },
  "shift_taken_on": {
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "string"
  },
  "reason": "string",
  "manager_approval_needed": true or false,
  "action_items": ["list of next steps"]
}

Rules:
- Use 24-hour HH:MM format for all times.
- Use YYYY-MM-DD for all dates.
- Use null for any field that isn't mentioned in the email.
"""


# ── Dataclass ─────────────────────────────────────────────────────────────────
# These mirror the JSON fields above. This is what gets returned
# after parsing — you access fields like result.requesting_employee.name

@dataclass
class Employee:
    """A person involved in the swap."""
    name:  Optional[str] = None
    email: Optional[str] = None
    role:  Optional[str] = None


@dataclass
class Shift:
    """A single shift slot belonging to one person."""
    date:       Optional[str] = None
    start_time: Optional[str] = None
    end_time:   Optional[str] = None
    location:   Optional[str] = None


@dataclass
class Result:
    """
    The fully parsed result of an employee shift swap email.
    Returned by ShiftParser.parse() when using this schema.
    """
    requesting_employee:    Optional[Employee] = None   # person initiating the swap
    covering_employee:      Optional[Employee] = None   # person agreeing to swap
    shift_given_away:       Optional[Shift]    = None   # requesting employee's original shift
    shift_taken_on:         Optional[Shift]    = None   # covering employee's original shift
    reason:                 Optional[str]      = None
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
            )

        return cls(
            requesting_employee     = to_employee(data.get("requesting_employee")),
            covering_employee       = to_employee(data.get("covering_employee")),
            shift_given_away        = to_shift(data.get("shift_given_away")),
            shift_taken_on          = to_shift(data.get("shift_taken_on")),
            reason                  = data.get("reason"),
            manager_approval_needed = bool(data.get("manager_approval_needed", False)),
            action_items            = data.get("action_items") or [],
        )

    def print_summary(self):
        """Print a readable summary to the terminal."""
        D = "─" * 50
        print(f"\n{'═' * 50}")
        print("  EMPLOYEE SHIFT SWAP")
        print(f"{'═' * 50}")
        print(f"  Provider : {self.provider_name} ({self.model_name})")
        print(D)

        if self.requesting_employee:
            e = self.requesting_employee
            print(f"  Requesting : {e.name or 'Unknown'}" +
                  (f" ({e.role})" if e.role else "") +
                  (f" <{e.email}>" if e.email else ""))

        if self.covering_employee:
            e = self.covering_employee
            print(f"  Covering   : {e.name or 'Unknown'}" +
                  (f" ({e.role})" if e.role else "") +
                  (f" <{e.email}>" if e.email else ""))
        print(D)

        if self.shift_given_away:
            s = self.shift_given_away
            print(f"  Gives away : {s.date}  {s.start_time or '?'} – {s.end_time or '?'}" +
                  (f"  @ {s.location}" if s.location else ""))

        if self.shift_taken_on:
            s = self.shift_taken_on
            print(f"  Takes on   : {s.date}  {s.start_time or '?'} – {s.end_time or '?'}" +
                  (f"  @ {s.location}" if s.location else ""))
        print(D)

        if self.reason:
            print(f"  Reason   : {self.reason}")
        print(f"  Approval : {'Required' if self.manager_approval_needed else 'Not required'}")
        if self.action_items:
            print("  Actions  :")
            for item in self.action_items:
                print(f"    • {item}")

        print(f"{'═' * 50}\n")
