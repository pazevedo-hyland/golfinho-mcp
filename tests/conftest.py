"""Shared test configuration — env loading, session-scoped auth fixtures."""

from __future__ import annotations

import os
import sys

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "src"))


# ---------------------------------------------------------------------------
# Shared .env loader (runs once at import time)
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    env_path = os.path.abspath(env_path)
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


# ---------------------------------------------------------------------------
# Session-scoped fixture: authenticated GGestClient singleton
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def ggest_client():
    """Authenticate the singleton GGestClient once per session.

    The httpx.AsyncClient is lazily created inside the session event loop,
    so all tests share one loop and one connection pool.
    """
    username = os.environ.get("GGEST_USERNAME", "")
    password = os.environ.get("GGEST_PASSWORD", "")
    if not username or not password:
        pytest.skip("GGEST_USERNAME / GGEST_PASSWORD not set")

    from ggest_mcp.auth import configure_db, login, login_old
    from ggest_mcp.http_client import client

    await login()
    await login_old()
    await configure_db()
    yield client
    await client.close()
