"""gGest MCP Server — entry point with Streamable HTTP transport."""

from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Import tool modules so they register with the shared mcp instance
import ggest_mcp.tools  # noqa: E402, F401

from ggest_mcp.app import mcp  # noqa: E402


def main() -> None:
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
