# sentinel-dispatch

Email ingestion + AI shift-scheduling parser for Sentinel Security.

## Layout

```
sentinel-security-ai-dispatch/
├── pyproject.toml          ← workspace root + CLI entry points
├── uv.lock
├── .env.example
│
├── mail/                   ← workspace member (package: mail)
│   ├── pyproject.toml          deps: httpx, msal, python-dotenv
│   └── src/mail/
│       ├── auth.py             MSAL token provider
│       ├── config.py           AppConfig + load_config()
│       ├── formatting.py       print_message_summary()
│       ├── graph_client.py     GraphClient (list, delta sync)
│       └── state_store.py      WatchState persistence
│
├── parsing/                ← workspace member (package: parsing)
│   ├── pyproject.toml          deps: openai
│   └── src/parsing/
│       ├── parser.py           ShiftParser
│       ├── providers/
│       │   ├── openai_provider.py
│       │   ├── deepseek_provider.py
│       │   └── ollama_provider.py
│       └── schemas/
│           ├── client_request.py
│           ├── employee_cover.py
│           └── employee_swap.py 
│
└── src/commands/           ← root package entry points
    ├── watch.py                dispatch-watch
    ├── list_recent.py          dispatch-list
    └── parse.py                dispatch-parse
```

## Setup

```bash
cp .env.example .env   # fill in your Graph credentials
uv sync                # one command — installs everything into a shared .venv
```

## Commands

### Watch a mailbox for new messages

```bash
uv run dispatch-watch
uv run dispatch-watch --parse --schema client_request --provider ollama --model deepseek-r1:14b
uv run dispatch-watch --reset-state   # wipe delta state and re-baseline
```

### List recent messages

```bash
uv run dispatch-list --top 20
uv run dispatch-list --top 5 --parse --schema client_request
```

### Parse an email without a live mailbox

```bash
uv run dispatch-parse --demo client_request
uv run dispatch-parse --file email.txt --schema employee_swap
uv run dispatch-parse --demo employee_cover --json   # raw JSON output
```

## Adding a new schema

1. Add `src/parsing/schemas/my_schema.py` with a `SYSTEM_PROMPT` and a `Result` dataclass.
2. Register it in `parsing/src/parsing/schemas/__init__.py`:
   ```python
   from parsing.schemas import my_schema
   REGISTRY["my_schema"] = my_schema
   ```
