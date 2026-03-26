from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    mailbox_user_id: str
    poll_seconds: int = 10
    state_file: Path = Path(".graph_delta_state.json")
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    request_timeout_seconds: float = 30.0


class ConfigError(ValueError):
    """Raised when required configuration is missing."""



def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value



def load_config() -> AppConfig:
    return AppConfig(
        tenant_id=_require_env("TENANT_ID"),
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
        mailbox_user_id=_require_env("MAILBOX_USER_ID"),
        poll_seconds=int(os.getenv("POLL_SECONDS", "10")),
        state_file=Path(os.getenv("STATE_FILE", ".graph_delta_state.json")),
        graph_base_url=os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
    )
