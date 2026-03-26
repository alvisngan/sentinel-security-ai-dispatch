from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from mail.auth import GraphTokenProvider
from mail.config import AppConfig


class GraphApiError(RuntimeError):
    """Raised when a Microsoft Graph request fails."""

    def __init__(self, message: str, *, status_code: int, error_code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


@dataclass
class GraphClient:
    config: AppConfig
    token_provider: GraphTokenProvider

    def __post_init__(self) -> None:
        self._client = httpx.Client(timeout=self.config.request_timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def _auth_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token_provider.get_access_token()}",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def get_json(
        self,
        url_or_path: str,
        *,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if url_or_path.startswith("https://"):
            url = url_or_path
        else:
            url = f"{self.config.graph_base_url.rstrip('/')}/{url_or_path.lstrip('/')}"

        response = self._client.get(
            url,
            params=params,
            headers=self._auth_headers(extra_headers),
        )

        if response.is_success:
            return response.json()

        error_code: str | None = None
        message = response.text
        try:
            payload = response.json()
            error = payload.get("error", {})
            error_code = error.get("code")
            message = error.get("message", message)
        except Exception:
            pass

        raise GraphApiError(
            f"Graph request failed: HTTP {response.status_code}; {message}",
            status_code=response.status_code,
            error_code=error_code,
        )

    def get_user_mailbox_profile(self, mailbox_user_id: str) -> dict[str, Any]:
        user_id = quote(mailbox_user_id)
        return self.get_json(f"/users/{user_id}?$select=id,displayName,mail,userPrincipalName")

    def list_recent_messages(self, mailbox_user_id: str, *, top: int = 10) -> list[dict[str, Any]]:
        user_id = quote(mailbox_user_id)
        payload = self.get_json(
            f"/users/{user_id}/mailFolders/inbox/messages",
            params={
                "$top": max(1, min(top, 50)),
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,receivedDateTime,from,isRead,bodyPreview,internetMessageId",
            },
        )
        return payload.get("value", [])

    def consume_message_delta_round(
        self,
        mailbox_user_id: str,
        *,
        delta_url: str | None,
        page_size: int = 25,
        created_only: bool = True,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Run one complete delta round and return (messages, new_delta_link).

        If delta_url is None, this performs the initial baseline synchronization.
        """
        user_id = quote(mailbox_user_id)
        next_url = delta_url or f"/users/{user_id}/mailFolders/inbox/messages/delta"
        params: dict[str, Any] | None
        if delta_url:
            params = None
        else:
            params = {
                "$top": max(1, min(page_size, 50)),
                "$select": "id,subject,receivedDateTime,from,isRead,bodyPreview,internetMessageId",
            }
            if created_only:
                params["changeType"] = "created"

        headers = {"Prefer": f"odata.maxpagesize={max(1, min(page_size, 50))}"}
        collected: list[dict[str, Any]] = []
        last_delta_link: str | None = None

        while True:
            payload = self.get_json(next_url, params=params, extra_headers=headers)
            for item in payload.get("value", []):
                if "@removed" in item:
                    continue
                collected.append(item)

            if "@odata.nextLink" in payload:
                next_url = payload["@odata.nextLink"]
                params = None
                continue

            last_delta_link = payload.get("@odata.deltaLink")
            if not last_delta_link:
                raise GraphApiError(
                    "Graph delta response did not contain @odata.deltaLink.",
                    status_code=500,
                    error_code="MissingDeltaLink",
                )
            break

        return collected, last_delta_link
