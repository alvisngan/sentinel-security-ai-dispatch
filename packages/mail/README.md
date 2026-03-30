# mail

Python package for reading mailboxes via the **Microsoft Graph API**. Handles authentication, message retrieval, and delta-based inbox synchronisation.

---

## Overview

| Module | Purpose |
|---|---|
| `config.py` | Loads `AppConfig` from environment variables |
| `auth.py` | Acquires Bearer tokens from Microsoft Entra via MSAL |
| `graph_client.py` | HTTP wrapper around the Graph `/users/{id}/messages` endpoints |
| `state_store.py` | Persists the delta-sync cursor (`@odata.deltaLink`) to disk |
| `formatting.py` | Utility functions for printing message summaries |

---

## Installation

```bash
pip install -e packages/mail
```

Dependencies: `httpx`, `msal`, `python-dotenv`.

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```dotenv
TENANT_ID=<Azure AD tenant ID>
CLIENT_ID=<App registration client ID>
CLIENT_SECRET=<App registration client secret>
MAILBOX_USER_ID=<UPN or object ID of the target mailbox>

# Optional
POLL_SECONDS=10
STATE_FILE=.graph_delta_state.json
GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
REQUEST_TIMEOUT_SECONDS=30
```

The app registration must have the `Mail.Read` application permission granted in Azure.

---

## Usage

### Load config and build a client

```python
from mail.config import load_config
from mail.auth import GraphTokenProvider
from mail.graph_client import GraphClient

config = load_config()
client = GraphClient(config=config, token_provider=GraphTokenProvider(config))
```

### List recent inbox messages

```python
messages = client.list_recent_messages(config.mailbox_user_id, top=10)
```

### Fetch a single message (with full body)

```python
message = client.get_message(config.mailbox_user_id, message_id="<Graph message ID>")
```

### Delta sync (poll for new messages)

Delta sync lets you efficiently poll for changes without re-fetching the entire inbox. The `@odata.deltaLink` returned by each round is used as the starting point for the next.

```python
from mail.state_store import StateStore

store = StateStore(config.state_file)
state = store.load()

messages, new_delta_url = client.consume_message_delta_round(
    config.mailbox_user_id,
    delta_url=state.delta_url,   # None on first run → baseline sync
)

state.delta_url = new_delta_url
store.save(state)

for msg in messages:
    print(msg["subject"])
```

On the first call (`delta_url=None`) the client performs a baseline sync and returns the initial delta link. Subsequent calls pass that link back in and receive only the messages that arrived since the previous round.

---

## Error handling

`GraphApiError` is raised for any non-2xx response and carries both `status_code` and `error_code` (from the Graph error envelope):

```python
from mail.graph_client import GraphApiError

try:
    messages = client.list_recent_messages(config.mailbox_user_id)
except GraphApiError as e:
    print(e.status_code, e.error_code)
```

`AuthError` is raised when MSAL cannot acquire a token (bad credentials, expired secret, missing permission, etc.).
