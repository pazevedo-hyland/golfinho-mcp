"""Async HTTP client for the gGest REST API (dual base URL, auto-refresh)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ggest_mcp.config import get_settings

logger = logging.getLogger(__name__)

# Intentionally no delete methods — structural safety guarantee.


class GGestClient:
    """Thin async wrapper around httpx that handles dual base URLs and auth."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._old_token: str | None = None
        self._http: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        """Lazily create the httpx client inside the running event loop."""
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=60.0, verify=True)
        return self._http

    # ── Token management ──────────────────────────────────────────────────

    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token

    def set_old_token(self, token: str) -> None:
        self._old_token = token

    @property
    def has_tokens(self) -> bool:
        return self._access_token is not None

    @property
    def has_old_token(self) -> bool:
        return self._old_token is not None

    @property
    def refresh_token_value(self) -> str | None:
        return self._refresh_token

    # ── Internal helpers ──────────────────────────────────────────────────

    def _auth_headers_v1(self) -> dict[str, str]:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def _auth_headers_old(self) -> dict[str, str]:
        if self._old_token:
            return {"Authorization": f"Bearer {self._old_token}"}
        return {}

    async def _request_v1(
        self,
        method: str,
        url: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        _retried: bool = False,
    ) -> Any:
        """Execute a v1 API request with auto-refresh on 401."""
        resp = await self._client.request(
            method,
            url,
            headers=self._auth_headers_v1(),
            json=json,
            params=params,
        )

        # Auto-refresh once on 401
        if resp.status_code == 401 and not _retried and self._refresh_token:
            logger.info("Got 401 on v1 — attempting token refresh")
            await self._do_refresh()
            return await self._request_v1(
                method, url, json=json, params=params, _retried=True
            )

        if resp.status_code >= 400:
            body = resp.text[:500]
            raise httpx.HTTPStatusError(
                f"gGest API error {resp.status_code}: {body}",
                request=resp.request,
                response=resp,
            )

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def _request_old(
        self,
        method: str,
        url: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        _retried: bool = False,
    ) -> Any:
        """Execute an old API request with re-login on 401."""
        resp = await self._client.request(
            method,
            url,
            headers=self._auth_headers_old(),
            json=json,
            params=params,
        )

        # Re-login once on 401 (old API has no refresh — just get a new token)
        if resp.status_code == 401 and not _retried:
            logger.info("Got 401 on old API — attempting re-login")
            from ggest_mcp.auth import login_old
            await login_old()
            return await self._request_old(
                method, url, json=json, params=params, _retried=True
            )

        if resp.status_code >= 400:
            body = resp.text[:500]
            raise httpx.HTTPStatusError(
                f"gGest API error {resp.status_code}: {body}",
                request=resp.request,
                response=resp,
            )

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def _do_refresh(self) -> None:
        """Refresh the access token using the stored refresh token."""
        url = f"{get_settings().base_url_v1}/auth/refresh-token"
        resp = await self._client.post(
            url, json={"refresh_token": self._refresh_token}
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Token refresh failed ({resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        self._access_token = data.get("access_token") or self._access_token
        self._refresh_token = data.get("refresh_token") or self._refresh_token
        logger.info("Token refreshed successfully")

    # ── New API (v1) ──────────────────────────────────────────────────────

    async def get_v1(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request_v1("GET", f"{get_settings().base_url_v1}{path}", params=params)

    async def put_v1(self, path: str, *, json: Any | None = None) -> Any:
        return await self._request_v1("PUT", f"{get_settings().base_url_v1}{path}", json=json)

    # POST on v1 only needed for auth (handled separately) — not exposed as general method

    # ── Old API ───────────────────────────────────────────────────────────

    async def get_old(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request_old("GET", f"{get_settings().base_url_old}{path}", params=params)

    async def post_old(self, path: str, *, json: Any | None = None) -> Any:
        return await self._request_old("POST", f"{get_settings().base_url_old}{path}", json=json)

    async def put_old(self, path: str, *, json: Any | None = None) -> Any:
        return await self._request_old("PUT", f"{get_settings().base_url_old}{path}", json=json)

    # ── Raw (no base URL prefix — for auth endpoints) ────────────────────

    async def post_raw(self, url: str, *, json: Any | None = None) -> Any:
        """POST to a full URL without auth headers (used for login)."""
        resp = await self._client.post(url, json=json)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Request failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.json()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None


# Singleton — shared across all tools
client = GGestClient()
