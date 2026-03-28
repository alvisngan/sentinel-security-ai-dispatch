# parsing

Python package for extracting structured data from shift-scheduling emails using an LLM. Supports automatic schema routing, multiple LLM providers, and is straightforward to extend with new schemas.

---

## Overview

```
parsing/
├── parser.py        # ShiftParser — top-level entry point
├── router.py        # SchemaRouter — classifies emails to the right schema
├── schemas/
│   ├── client_request.py   # Client asking for staff to fill a shift
│   ├── employee_cover.py   # Employee asking for someone to cover their shift
│   └── employee_swap.py    # Two employees requesting a shift swap
└── providers/
    ├── ollama_provider.py      # Local Ollama model (no API key needed)
    ├── openai_provider.py      # OpenAI API
    └── deepseek_provider.py    # DeepSeek API
```

---

## Installation

```bash
pip install -e packages/parsing
```

Dependencies: `openai` (used by all three providers).

---

## Quick start

```python
from parsing import ShiftParser
from parsing.providers import OllamaProvider

parser = ShiftParser(provider=OllamaProvider())

result = parser.parse("""
    Hi, I need to swap my Saturday shift (Dec 14, 2–10 PM) with Jordan.
    She's agreed to take it and I'll cover her Sunday morning instead.
""")

result.print_summary()
```

---

## Providers

All providers expose the same interface — `complete(system, user) -> str` — so they are interchangeable.

| Provider | Class | Notes |
|---|---|---|
| Ollama | `OllamaProvider` | Local model, no API key. Default model: `deepseek-r1:7b`. |
| OpenAI | `OpenAIProvider` | Requires `OPENAI_API_KEY`. Default model: `gpt-4o-mini`. |
| DeepSeek | `DeepSeekProvider` | Requires `DEEPSEEK_API_KEY`. Default model: `deepseek-chat`. |

```python
from parsing.providers import OpenAIProvider, DeepSeekProvider, OllamaProvider

# OpenAI
provider = OpenAIProvider()                        # reads OPENAI_API_KEY from env
provider = OpenAIProvider(model="gpt-4o")

# DeepSeek
provider = DeepSeekProvider()                      # reads DEEPSEEK_API_KEY from env

# Ollama (local)
provider = OllamaProvider(model="llama3.2", host="http://localhost:11434")
```

---

## Schemas

Each schema handles one category of shift email. A schema module contains:

- `DESCRIPTION` — one-line description used by the router to classify emails.
- `SYSTEM_PROMPT` — the prompt sent to the LLM, defining the expected JSON shape.
- `Result` — a dataclass with a `from_dict()` classmethod and a `print_summary()` method.

### client_request

A client asking for staff to be assigned to a shift slot.

```python
from parsing.schemas import client_request
from parsing import ShiftParser

parser = ShiftParser(provider=..., schema=client_request)
result = parser.parse(email_text)
# result.shift.date, result.shift.headcount, result.urgency, ...
```

### employee_cover

An employee asking for someone to cover their shift.

### employee_swap

Two employees requesting a mutual shift swap.

---

## Automatic schema routing

Omit the `schema` argument and `ShiftParser` will classify the email automatically before parsing:

```python
parser = ShiftParser(provider=OllamaProvider())   # no schema given
result = parser.parse(email_text)                 # schema detected at runtime
```

The router sends the email to the LLM with a prompt built from each schema's `DESCRIPTION`, then validates the response against the schema registry. A `ValueError` is raised if the LLM returns an unrecognised key.

---

## Adding a new schema

1. Create `parsing/schemas/my_schema.py` with `DESCRIPTION`, `SYSTEM_PROMPT`, and a `Result` dataclass.
2. Register it in `parsing/schemas/__init__.py`:

```python
from parsing.schemas import my_schema

REGISTRY = {
    ...
    "my_schema": my_schema,
}
```

The router picks it up automatically — no other changes needed.

---

## Error handling

`ShiftParser.parse()` raises `ValueError` if:

- The LLM returns output that cannot be parsed as JSON (includes the raw output in the message for debugging).
- The router returns a schema key not present in the registry.
