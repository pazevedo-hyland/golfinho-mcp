"""Shared FastMCP application instance — imported by server.py and all tool modules."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastmcp import FastMCP


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Startup: authenticate with gGest. Shutdown: close HTTP client."""
    from ggest_mcp.auth import ensure_authenticated
    from ggest_mcp.http_client import client

    await ensure_authenticated()
    try:
        yield
    finally:
        await client.close()


mcp = FastMCP(
    "ggest",
    instructions=(
        "MCP server para o ERP gGest. "
        "Permite consultar artigos, clientes, entidades de referência, "
        "taxas de IVA, relatórios de vendas e extratos de clientes. "
        "Também permite atualizar dados de artigos e clientes. "
        "Não suporta criação, eliminação ou operações fiscais (documentos, caixa, etc.)."
    ),
    lifespan=lifespan,
)
