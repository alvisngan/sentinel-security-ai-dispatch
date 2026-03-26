"""
commands/parse.py
-----------------
Parse a raw email string using the LLM, without needing a live mailbox.
Reads the email from stdin or a file path argument.

Usage:
    echo "email body..." | dispatch-parse --schema client_request --provider ollama
    dispatch-parse --file email.txt --schema employee_swap --provider openai
    dispatch-parse --demo client_request
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from parsing import ShiftParser
from parsing.providers import DeepSeekProvider, OllamaProvider, OpenAIProvider
from parsing.schemas import REGISTRY as SCHEMA_REGISTRY


# ── Demo emails (kept here so the command is self-contained for quick testing) ──

DEMO_EMAILS: dict[str, str] = {
    "client_request": """\
Please find the security request for the function below:

Post Inc – Thursday, January 22nd – The Gallery
1 Guard Scheduled from 6:00pm-10:30pm.

Onsite contact would be a Banquet Manager either Mike, James, or Jessica.

Please let us know if you have any questions.

Kind Regards,
""",
    "employee_swap": """\
From: Sarah Johnson <sarah.johnson@company.com>
To: manager@company.com
Subject: Shift Swap Request – Dec 14

Hi,

I'm hoping to swap my shift this Saturday (December 14th) from 9 AM to 5 PM
with Tom Bradley. Tom has agreed to cover my shift, and I'll take his Sunday
shift (December 15th) from 2 PM to 10 PM at the downtown location.

The reason is a family event I cannot reschedule. Could you please approve?

Thanks,
Sarah Johnson
""",
    "employee_cover": """\
From: Mike Torres <mike.torres@company.com>
To: scheduling@company.com
Subject: Need someone to cover my Friday night shift ASAP

Hey team,

I'm sick and won't be able to make my Friday shift (Dec 6, 6 PM to 2 AM)
in the kitchen at the Westside location. This is urgent — I need a cover ASAP.

Please let me know if anyone is available.

Mike Torres
""",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Parse a shift email with the LLM. Reads from stdin, a file, or a built-in demo."
    )
    source = p.add_mutually_exclusive_group()
    source.add_argument("--file", metavar="PATH",
                        help="Path to a plain-text file containing the email.")
    source.add_argument("--demo", choices=list(DEMO_EMAILS),
                        help="Use a built-in demo email instead of stdin/file.")

    p.add_argument("--schema", default="client_request", choices=list(SCHEMA_REGISTRY),
                   help="Schema to parse against (default: client_request).")
    p.add_argument("--provider", default="ollama",
                   choices=["ollama", "deepseek", "openai"])
    p.add_argument("--model", default=None,
                   help="Model name. Defaults: ollama=deepseek-r1:14b, deepseek=deepseek-chat, "
                        "openai=gpt-4o-mini")
    p.add_argument("--json", action="store_true", dest="output_json",
                   help="Output raw JSON instead of the human-readable summary.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # ── Resolve email text ────────────────────────────────────────────────────
    if args.demo:
        email_text = DEMO_EMAILS[args.demo]
    elif args.file:
        try:
            email_text = open(args.file, encoding="utf-8").read()
        except OSError as exc:
            print(f"Cannot read file: {exc}", file=sys.stderr)
            return 2
    else:
        if sys.stdin.isatty():
            print("Reading email from stdin (Ctrl-D / Ctrl-Z to finish)…", file=sys.stderr)
        email_text = sys.stdin.read()

    if not email_text.strip():
        print("No email text provided.", file=sys.stderr)
        return 2

    # ── Build provider ────────────────────────────────────────────────────────
    if args.provider == "ollama":
        provider = OllamaProvider(model=args.model or "deepseek-r1:14b")
    elif args.provider == "deepseek":
        provider = DeepSeekProvider(model=args.model or "deepseek-chat")
    else:
        provider = OpenAIProvider(model=args.model or "gpt-4o-mini")

    schema = SCHEMA_REGISTRY[args.schema]
    parser = ShiftParser(provider=provider, schema=schema)

    print(f"Schema   : {args.schema}", file=sys.stderr)
    print(f"Provider : {provider.name} / {provider.model}", file=sys.stderr)
    print("Parsing…", file=sys.stderr)

    try:
        result = parser.parse(email_text)
    except Exception as exc:  # noqa: BLE001
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        result.print_summary()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
