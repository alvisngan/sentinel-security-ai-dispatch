from __future__ import annotations

from dataclasses import dataclass

import msal

from mail.config import AppConfig


class AuthError(RuntimeError):
    """Raised when Microsoft Entra token acquisition fails."""


@dataclass
class GraphTokenProvider:
    config: AppConfig

    def __post_init__(self) -> None:
        authority = f"https://login.microsoftonline.com/{self.config.tenant_id}"
        self._app = msal.ConfidentialClientApplication(
            client_id=self.config.client_id,
            authority=authority,
            client_credential=self.config.client_secret,
        )

    def get_access_token(self) -> str:
        scopes = ["https://graph.microsoft.com/.default"]
        result = self._app.acquire_token_silent(scopes=scopes, account=None)
        if not result:
            result = self._app.acquire_token_for_client(scopes=scopes)

        access_token = result.get("access_token")
        if access_token:
            return access_token

        error = result.get("error", "unknown_error")
        description = result.get("error_description", "No error description returned.")
        correlation_id = result.get("correlation_id", "n/a")
        raise AuthError(
            "Failed to acquire Microsoft Graph access token. "
            f"error={error}; correlation_id={correlation_id}; description={description}"
        )
