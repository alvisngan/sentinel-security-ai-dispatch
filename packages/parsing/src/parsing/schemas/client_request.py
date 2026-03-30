"""
schemas/client_request.py
--------------------------
Schema for CLIENT shift request emails.

A client is requesting staff to be assigned to a shift slot.
Unlike employee emails, the client doesn't name specific employees —
they just describe the slot and how many people they need.

Example email:
    "We need 3 security guards at the downtown venue this Saturday
     Dec 14, from 8PM to 2AM for a private event."
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Discription  ──────────────────────────────────────────────────────────────
DESCRIPTION = "A CLIENT asking for staff to be assigned to a shift"

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a shift scheduling assistant. Extract client shift request details from the email.

Respond with a single valid JSON object only — no markdown, no explanation.

{
  "client": {
    "name": "string",
    "email": "string",
    "company": "string"
  },
  "shift": {
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "string",
    "role_required": "string",
    "headcount": 1
  },
  "special_requirements": "string",
  "urgency": "low | medium | high | critical",
  "action_items": ["list of next steps"]
}

Rules:
- Use 24-hour HH:MM format for all times.
- Use YYYY-MM-DD for all dates.
- headcount is the number of staff the client needs for this shift slot.
- Use null for any field not mentioned in the email.
"""


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class Client:
    """The client making the request."""
    name:    Optional[str] = None
    email:   Optional[str] = None
    company: Optional[str] = None


@dataclass
class Shift:
    """
    A shift slot that needs to be filled by the scheduling team.
    headcount = how many staff are needed for this slot.
    """
    date:            Optional[str] = None
    start_time:      Optional[str] = None
    end_time:        Optional[str] = None
    location:        Optional[str] = None
    role_required:   Optional[str] = None
    headcount:       Optional[int] = None   # how many staff needed


@dataclass
class Result:
    """
    The fully parsed result of a client shift request email.
    Returned by ShiftParser.parse() when using this schema.
    """
    client:               Optional[Client] = None
    shift:                Optional[Shift]  = None
    special_requirements: Optional[str]    = None
    urgency:              str              = "low"
    action_items:         list[str]        = field(default_factory=list)

    # Set by ShiftParser after parsing — not from the LLM
    provider_name: str = ""
    model_name:    str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Result":
        """Build a Result from the raw JSON dict returned by the LLM."""

        def to_client(d):
            if not d:
                return None
            return Client(name=d.get("name"), email=d.get("email"), company=d.get("company"))

        def to_shift(d):
            if not d:
                return None
            return Shift(
                date          = d.get("date"),
                start_time    = d.get("start_time"),
                end_time      = d.get("end_time"),
                location      = d.get("location"),
                role_required = d.get("role_required"),
                headcount     = d.get("headcount"),
            )

        return cls(
            client               = to_client(data.get("client")),
            shift                = to_shift(data.get("shift")),
            special_requirements = data.get("special_requirements"),
            urgency              = data.get("urgency") or "low",
            action_items         = data.get("action_items") or [],
        )

    def print_summary(self):
        """Print a readable summary to the terminal."""
        D = "─" * 50
        print(f"\n{'═' * 50}")
        print("  CLIENT SHIFT REQUEST")
        print(f"{'═' * 50}")
        print(f"  Provider : {self.provider_name} ({self.model_name})")
        print(f"  Urgency  : {self.urgency.upper()}")
        print(D)

        if self.client:
            c = self.client
            print(f"  Client  : {c.name or 'Unknown'}" +
                  (f" — {c.company}" if c.company else "") +
                  (f" <{c.email}>" if c.email else ""))
        print(D)

        if self.shift:
            s = self.shift
            print(f"  Date     : {s.date}")
            print(f"  Time     : {s.start_time or '?'} – {s.end_time or '?'}")
            if s.location:      print(f"  Location : {s.location}")
            if s.role_required: print(f"  Role     : {s.role_required}")
            if s.headcount:     print(f"  Headcount: {s.headcount} person(s) needed")
        print(D)

        if self.special_requirements:
            print(f"  Special  : {self.special_requirements}")
        if self.action_items:
            print("  Actions  :")
            for item in self.action_items:
                print(f"    • {item}")

        print(f"{'═' * 50}\n")
