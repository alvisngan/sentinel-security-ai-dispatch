"""
main.py
-------
Run this to test the shift email parser.

1. Set PROVIDER and your API key below.
2. Set ACTIVE_EMAIL to whichever demo email you want to test.
3. Run: python main.py

Requirements:
    pip install openai
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from providers.openai_provider   import OpenAIProvider
from providers.deepseek_provider import DeepSeekProvider
from providers.ollama_provider   import OllamaProvider
from parser    import ShiftParser
from schemas   import employee_swap, employee_cover, client_request


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PROVIDER = "ollama"          # "ollama" | "deepseek" | "openai"
MODEL    = "deepseek-r1:14b" # model to use (for ollama/deepseek/openai)

OPENAI_API_KEY   = ""        # or set env var OPENAI_API_KEY
DEEPSEEK_API_KEY = ""        # or set env var DEEPSEEK_API_KEY

# Which demo email to parse — change this to test different schemas
ACTIVE_EMAIL = "client_request"   # "employee_swap" | "employee_cover" | "client_request"


# ─────────────────────────────────────────────────────────────────────────────
#  DEMO EMAILS
# ─────────────────────────────────────────────────────────────────────────────

EMAILS = {
    "client_request": """\
Please find the security request for the function below:
  
Kore Inc – Thursday, January 22nd – The Austin Gallery
1 Guard Scheduled from 6:00pm-10:30pm.
 
Onsite contact would be a Banquet Manager either Lance, Cristina, or Reggie.
 
Please let us know if you have any questions.
 
Kind Regards,
""",
}
# EMAILS = {
# 
#     "employee_swap": """\
# From: Sarah Johnson <sarah.johnson@company.com>
# To: manager@company.com
# Subject: Shift Swap Request – Dec 14
# 
# Hi,
# 
# I'm hoping to swap my shift this Saturday (December 14th) from 9 AM to 5 PM
# with Tom Bradley. Tom has agreed to cover my shift, and I'll take his Sunday
# shift (December 15th) from 2 PM to 10 PM at the downtown location.
# 
# The reason is a family event I cannot reschedule. Could you please approve?
# 
# Thanks,
# Sarah Johnson
# Cashier – Downtown Branch
# """,
# 
#     "employee_cover": """\
# From: Mike Torres <mike.torres@company.com>
# To: scheduling@company.com
# Subject: Need someone to cover my Friday night shift ASAP
# 
# Hey team,
# 
# I'm sick and won't be able to make my Friday shift (Dec 6, 6 PM to 2 AM)
# in the kitchen at the Westside location. This is urgent — I need a cover ASAP.
# 
# Please let me know if anyone is available.
# 
# Mike Torres
# Line Cook
# """,
# 
#     "client_request": """\
# From: Jennifer Walsh <j.walsh@eventco.com>
# To: staffing@company.com
# Subject: Staff Request – Saturday Night Event
# 
# Hi,
# 
# We need 3 security guards at the downtown convention centre this Saturday,
# December 14th, from 8 PM to 2 AM for a private corporate event.
# 
# Smart dress code required. Please confirm availability by Thursday.
# 
# Thanks,
# Jennifer Walsh
# EventCo Ltd.
# """,
# 
# }

# Which schema to use for each email type
SCHEMAS = {
    "employee_swap":    employee_swap,
    "employee_cover":   employee_cover,
    "client_request":   client_request,
}


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Build the provider
    if PROVIDER == "openai":
        provider = OpenAIProvider(api_key=OPENAI_API_KEY, model=MODEL)
    elif PROVIDER == "deepseek":
        provider = DeepSeekProvider(api_key=DEEPSEEK_API_KEY, model=MODEL)
    elif PROVIDER == "ollama":
        provider = OllamaProvider(model=MODEL)
    else:
        print(f"Unknown PROVIDER '{PROVIDER}'. Choose: ollama, deepseek, openai")
        sys.exit(1)

    schema     = SCHEMAS[ACTIVE_EMAIL]
    email_text = EMAILS[ACTIVE_EMAIL]

    print(f"Schema   : {ACTIVE_EMAIL}")
    print(f"Provider : {provider.name} / {provider.model}")
    print(f"\n── Email ──────────────────────────────────────────")
    print(email_text)

    print(f"Parsing…\n")
    result = ShiftParser(provider=provider, schema=schema).parse(email_text)

    # Pretty summary
    result.print_summary()

    # Show raw JSON too
    import json, dataclasses
    print("── Raw JSON ───────────────────────────────────────")
    print(json.dumps(dataclasses.asdict(result), indent=2))


if __name__ == "__main__":
    main()
