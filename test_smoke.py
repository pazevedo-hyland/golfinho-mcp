"""Smoke test — connect to the running MCP server and exercise all tools."""

import asyncio

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


async def test():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. List tools
            tools = await session.list_tools()
            print(f"=== Tools found: {len(tools.tools)} ===")
            for t in tools.tools:
                print(f"  - {t.name}")

            # 2. ler_data_hora
            print("\n=== ler_data_hora ===")
            result = await session.call_tool("ler_data_hora", {})
            print(result.content[0].text[:300])

            # 3. list_artigos (no filter — first page)
            print("\n=== list_artigos ===")
            result = await session.call_tool("list_artigos", {})
            print(result.content[0].text[:500] + "...")

            # 4. list_clientes (no filter)
            print("\n=== list_clientes ===")
            result = await session.call_tool("list_clientes", {})
            print(result.content[0].text[:500] + "...")

            # 5. lookup_entity — vendedores
            print("\n=== lookup_entity: vendedores ===")
            result = await session.call_tool("lookup_entity", {"entity_type": "vendedores"})
            print(result.content[0].text[:500] + "...")

            # 6. list_ivas
            print("\n=== list_ivas ===")
            result = await session.call_tool("list_ivas", {"tipo": "taxas"})
            print(result.content[0].text[:500] + "...")

            print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(test())
