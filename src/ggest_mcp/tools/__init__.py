"""Register all tool modules with the MCP server."""

import logging

from ggest_mcp.config import get_settings

# Read-only tools (always registered)
from ggest_mcp.tools import artigos  # noqa: F401
from ggest_mcp.tools import clientes  # noqa: F401
from ggest_mcp.tools import lookup  # noqa: F401
from ggest_mcp.tools import iva  # noqa: F401
from ggest_mcp.tools import mapas  # noqa: F401
from ggest_mcp.tools import sistema  # noqa: F401

logger = logging.getLogger(__name__)

# Remove update tools if read-only mode is active (default)
s = get_settings()
if s.readonly:
    from ggest_mcp.app import mcp

    for tool_name in ("update_artigo", "update_cliente"):
        try:
            mcp.local_provider.remove_tool(tool_name)
            logger.info("Read-only mode: removed tool '%s'", tool_name)
        except Exception:
            pass
else:
    logger.info("Read-write mode: update tools enabled")
