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
from ggest_mcp.tools import analytics  # noqa: F401

# Write tools (registered but removed in read-only mode)
from ggest_mcp.tools import documentos  # noqa: F401
from ggest_mcp.tools import servicos  # noqa: F401
from ggest_mcp.tools import producao  # noqa: F401

logger = logging.getLogger(__name__)

# Remove write tools if read-only mode is active (default)
_WRITE_TOOLS = (
    "update_artigo",
    "update_cliente",
    "create_artigo",
    "create_cliente",
    "gravar_documento",
    "gravar_recibo",
    "assistencia_tecnica",
    "criar_producao",
)

s = get_settings()
if s.readonly:
    from ggest_mcp.app import mcp

    for tool_name in _WRITE_TOOLS:
        try:
            mcp.local_provider.remove_tool(tool_name)
            logger.info("Read-only mode: removed tool '%s'", tool_name)
        except Exception:
            pass
else:
    logger.info("Read-write mode: all %d write tools enabled", len(_WRITE_TOOLS))
