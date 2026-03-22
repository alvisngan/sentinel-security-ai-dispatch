"""
shift_parser.__main__
----------------------
Command-line interface for the shift_parser package.

Run via:
    python -m shift_parser [options]
    python -m shift_parser --demo
    python -m shift_parser --provider ollama --model deepseek-r1:7b --file email.txt
"""

import argparse
import json
import sys

DEMO_EMAIL = """\
From: Sarah Johnson <sarah.johnson@company.com>
To: manager@company.com
Subject: Shift Swap Request – Dec 14

Hi,

I'm hoping to swap my shift this Saturday (December 14th) from 9 AM to 5 PM
with Tom Bradley. Tom has agreed to cover my shift, and I'll take his Sunday
shift (December 15th) from 2 PM to 10 PM at the downtown location.

The reason is a family event I cannot reschedule.

Could you please approve this swap? Let me know if you need anything else.

Thanks,
Sarah Johnson
Cashier – Downtown Branch
"""


def build_provider(args):
    """Instantiate the correct provider from CLI args."""
    p = args.provider.lower()

    if p == "openai":
        from shift_parser.providers import OpenAIProvider
        kwargs = {}
        if args.api_key: kwargs["api_key"] = args.api_key
        if args.model:   kwargs["model"]   = args.model
        return OpenAIProvider(**kwargs)

    elif p == "deepseek":
        from shift_parser.providers import DeepSeekProvider
        kwargs = {}
        if args.api_key: kwargs["api_key"] = args.api_key
        if args.model:   kwargs["model"]   = args.model
        return DeepSeekProvider(**kwargs)

    elif p == "ollama":
        from shift_parser.providers import OllamaProvider
        kwargs = {}
        if args.model: kwargs["model"] = args.model
        if args.host:  kwargs["host"]  = args.host
        return OllamaProvider(**kwargs)

    else:
        print(f"Unknown provider '{args.provider}'. Choose: openai, deepseek, ollama",
              file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="python -m shift_parser",
        description="Parse shift-scheduling emails with any LLM provider.",
    )

    # Input source
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--email", help="Email text as a string")
    src.add_argument("--file",  help="Path to a .txt email file")
    src.add_argument("--demo",  action="store_true", help="Run with built-in demo email")

    # Provider selection
    parser.add_argument("--provider", default="deepseek",
                        choices=["openai", "deepseek", "ollama"],
                        help="LLM provider to use (default: deepseek)")
    parser.add_argument("--model",   help="Override the default model name")
    parser.add_argument("--api-key", dest="api_key", help="API key (or set env var)")
    parser.add_argument("--host",    default="http://localhost:11434",
                        help="Ollama server URL (default: http://localhost:11434)")

    # Output
    parser.add_argument("--json", dest="output_json", action="store_true",
                        help="Print raw JSON output")
    parser.add_argument("--save", metavar="FILE",
                        help="Save JSON result to this path")

    args = parser.parse_args()

    # Resolve email content
    if args.email:
        email_text = args.email
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            email_text = f.read()
    elif args.demo:
        print("── Demo email ─────────────────────────────────────────")
        print(DEMO_EMAIL)
        email_text = DEMO_EMAIL
    else:
        if sys.stdin.isatty():
            print("No input given — running demo email.\n")
            email_text = DEMO_EMAIL
        else:
            email_text = sys.stdin.read()

    provider = build_provider(args)
    print(f"Parsing with {provider.name} / {provider.model} …")

    from shift_parser import ShiftParser
    sp = ShiftParser(provider)

    try:
        result = sp.parse(email_text)
    except ValueError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(result.to_json())
    else:
        result.print_summary()

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(result.to_json())
        print(f"Saved → {args.save}")


if __name__ == "__main__":
    main()
