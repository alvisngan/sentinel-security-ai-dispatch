# shift_parser

Parse shift-scheduling emails into structured data using any LLM backend.

## Install

```bash
pip install openai          # only dependency
pip install -e .            # install shift_parser itself (from this folder)
```

## Providers

| Provider | Class | Needs |
|---|---|---|
| OpenAI cloud | `OpenAIProvider` | `OPENAI_API_KEY` env var |
| DeepSeek cloud | `DeepSeekProvider` | `DEEPSEEK_API_KEY` env var |
| Ollama (local) | `OllamaProvider` | Ollama running on localhost |

---

## Use as a library

```python
from shift_parser import ShiftParser
from shift_parser.providers import OpenAIProvider, DeepSeekProvider, OllamaProvider

email = """
From: Sarah Johnson <sarah@company.com>
Subject: Shift Swap Request

Hi, I need to swap my Saturday Dec 14 shift (9 AM–5 PM) with Tom Bradley.
Tom will take my shift and I'll cover his Sunday Dec 15 shift (2 PM–10 PM).
Please approve. Thanks, Sarah
"""

# ── OpenAI ────────────────────────────────────────────────────────────────────
parser = ShiftParser(OpenAIProvider())           # reads OPENAI_API_KEY
result = parser.parse(email)
result.print_summary()                           # pretty-print
print(result.to_json())                          # JSON string
print(result.to_dict())                          # plain dict

# ── DeepSeek cloud ────────────────────────────────────────────────────────────
parser = ShiftParser(DeepSeekProvider())         # reads DEEPSEEK_API_KEY
result = parser.parse(email)

# ── Local Ollama ──────────────────────────────────────────────────────────────
parser = ShiftParser(OllamaProvider(model="deepseek-r1:7b"))
result = parser.parse(email)

# ── Switch provider mid-session ───────────────────────────────────────────────
parser2 = parser.switch_provider(OpenAIProvider(model="gpt-4o"))
result2 = parser2.parse(email)

# ── Parse from file ───────────────────────────────────────────────────────────
result = parser.parse_file("path/to/email.txt")

# ── Access individual fields ──────────────────────────────────────────────────
print(result.shift_change_type)         # "swap"
print(result.urgency)                   # "medium"
print(result.requestor.name)            # "Sarah Johnson"
print(result.original_shift.date)       # "2024-12-14"
print(result.original_shift.start_time) # "09:00"
print(result.action_items)              # ["Manager approval needed"]
```

## Write a custom provider

```python
from shift_parser.providers.base import BaseProvider
from shift_parser import ShiftParser

class MyCustomProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "MyLLM"

    @property
    def model(self) -> str:
        return "my-model-v1"

    def complete(self, system_prompt: str, user_message: str) -> str:
        # Call your LLM API here and return the raw text response
        response = my_llm_api.chat(system=system_prompt, user=user_message)
        return response.text

parser = ShiftParser(MyCustomProvider())
result = parser.parse(email)
```

## CLI

```bash
# Demo with DeepSeek (default)
python -m shift_parser --demo

# Choose provider
python -m shift_parser --provider openai  --demo
python -m shift_parser --provider deepseek --demo
python -m shift_parser --provider ollama --model deepseek-r1:7b --demo

# Parse a file
python -m shift_parser --provider ollama --file email.txt

# Output raw JSON
python -m shift_parser --demo --json

# Save result
python -m shift_parser --demo --save result.json

# Pipe from stdin
cat email.txt | python -m shift_parser --provider openai
```

## ShiftInfo fields

| Field | Type | Description |
|---|---|---|
| `shift_change_type` | str | swap / cover / cancellation / new_shift / modification |
| `urgency` | str | low / medium / high / critical |
| `approval_required` | bool | Whether manager sign-off is needed |
| `approved_by` | str? | Name of approver if already approved |
| `reason` | str? | Why the change is requested |
| `notes` | str? | Additional context |
| `action_items` | list[str] | Next steps still needed |
| `requestor` | Person? | name, email, role |
| `covering_employee` | Person? | name, email, role |
| `original_shift` | Shift? | date, start_time, end_time, location, department, position |
| `new_shift` | Shift? | Same fields — populated for swaps |
| `provider_name` | str | Which provider was used |
| `model_name` | str | Which model was used |
