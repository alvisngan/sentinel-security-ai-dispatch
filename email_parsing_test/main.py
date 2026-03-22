"""
main.py — run this to test the shift email parser
--------------------------------------------------
No pip install needed. Just set your API key below and run:

    python main.py

Requirements (only one package needed):
    pip install openai
"""

import sys
import os

# ── Make sure the package folder is on the path ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "shift_parser"))

from shift_parser import ShiftParser
from shift_parser.providers import OpenAIProvider, DeepSeekProvider, OllamaProvider

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG — pick ONE provider and set your key / model below
# ─────────────────────────────────────────────────────────────────────────────

PROVIDER = "ollama"           # "ollama" | "deepseek" | "openai"

OPENAI_API_KEY   = ""         # or set env var OPENAI_API_KEY
DEEPSEEK_API_KEY = ""         # or set env var DEEPSEEK_API_KEY
OLLAMA_MODEL     = "deepseek-r1:14b"   # any model you have pulled locally
OLLAMA_HOST      = "http://localhost:11434"

# ─────────────────────────────────────────────────────────────────────────────
#  DEMO EMAILS — swap in any of these, or add your own
# ─────────────────────────────────────────────────────────────────────────────

EMAILS = {

    "swap": """\
Good afternoon,
 
Please find the security request for the function below:
  
Kore Inc – Thursday, January 22nd – The Austin Gallery
1 Guard Scheduled from 6:00pm-10:30pm.
 
Onsite contact would be a Banquet Manager either Lance, Cristina, or Reggie.
 
Please let us know if you have any questions.
 
Kind Regards,
""",

}

# Change this to "cover" or "cancellation" to test other emails
ACTIVE_EMAIL = "swap"

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def make_provider():
    if PROVIDER == "openai":
        key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        return OpenAIProvider(api_key=key)

    elif PROVIDER == "deepseek":
        key = DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
        return DeepSeekProvider(api_key=key)

    elif PROVIDER == "ollama":
        return OllamaProvider(model=OLLAMA_MODEL, host=OLLAMA_HOST)

    else:
        print(f"Unknown PROVIDER '{PROVIDER}'. Choose: ollama, deepseek, openai")
        sys.exit(1)


def main():
    print(f"Provider : {PROVIDER}")
    print(f"Email    : '{ACTIVE_EMAIL}'")
    print()

    email_text = EMAILS[ACTIVE_EMAIL]
    print("── Email content ──────────────────────────────────────")
    print(email_text)

    provider = make_provider()
    parser   = ShiftParser(provider)

    print(f"Sending to {provider.name} / {provider.model} …\n")
    try:
        result = parser.parse(email_text)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # ── Pretty summary ────────────────────────────────────────────────────────
    result.print_summary()

    # ── Show individual fields ────────────────────────────────────────────────
    print("── Individual field access ────────────────────────────")
    print(f"  shift_change_type : {result.shift_change_type}")
    print(f"  urgency           : {result.urgency}")
    print(f"  approval_required : {result.approval_required}")
    if result.requestor:
        print(f"  requestor.name    : {result.requestor.name}")
        print(f"  requestor.email   : {result.requestor.email}")
    if result.original_shift:
        print(f"  original date     : {result.original_shift.date}")
        print(f"  original time     : {result.original_shift.start_time} – {result.original_shift.end_time}")
    if result.action_items:
        print(f"  action_items      : {result.action_items}")
    print()

    # ── Raw JSON ──────────────────────────────────────────────────────────────
    print("── Raw JSON output ────────────────────────────────────")
    print(result.to_json())


if __name__ == "__main__":
    main()
