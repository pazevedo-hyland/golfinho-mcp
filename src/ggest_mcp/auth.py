"""Authentication manager — login, token refresh, and DB configuration."""

from __future__ import annotations

import logging

from ggest_mcp.config import get_settings
from ggest_mcp.http_client import client

logger = logging.getLogger(__name__)

_authenticated = False


async def login() -> None:
    """Authenticate with the gGest API and store tokens."""
    s = get_settings()
    url = f"{s.base_url_v1}/auth/login"
    data = await client.post_raw(
        url,
        json={"username": s.username, "password": s.password},
    )
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    if not access_token:
        raise RuntimeError(f"Login failed — no access_token in response: {data}")
    client.set_tokens(access_token, refresh_token or "")
    logger.info("Successfully logged in to gGest API")


async def configure_db() -> None:
    """Configure database access via the old API endpoint."""
    s = get_settings()
    # Skip if required DB fields are missing
    if not s.db_servidor or not s.db_base_dados:
        logger.info(
            "DB config incomplete (servidor=%s, basedados=%s) — skipping configurarAcessoBD",
            s.db_servidor or "<empty>",
            s.db_base_dados or "<empty>",
        )
        return

    await client.put_old(
        "/configurarAcessoBD",
        json={
            "hfsql_servidor": s.db_servidor,
            "hfsql_porta": s.db_porta,
            "hfsql_basedados": s.db_base_dados,
            "hfsql_utilizador": s.db_utilizador,
            "hfsql_palavrapasse": s.db_password,
        },
    )
    logger.info("Database access configured successfully")


async def ensure_authenticated() -> None:
    """Login + configure DB on first call. No-op on subsequent calls."""
    global _authenticated
    if _authenticated:
        return
    await login()
    await configure_db()
    _authenticated = True
