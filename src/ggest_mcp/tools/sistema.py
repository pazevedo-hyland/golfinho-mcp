"""Sistema tools — system date/time and pending receipts."""

from __future__ import annotations

import json

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def ler_data_hora() -> str:
    """Obter a data e hora atuais do sistema gGest."""
    data = await client.get_old("/lerDataHora")
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def get_pendentes_recibo(cliente: int, moeda: str = "EUR") -> str:
    """Listar documentos pendentes de pagamento (para recibo) de um cliente.

    Parâmetros:
    - cliente: código numérico do cliente
    - moeda: código da moeda (default: "EUR")

    Devolve lista de documentos pendentes com tipo, número, data,
    data de vencimento, total do documento e total liquidado.
    Útil para verificar quanto um cliente deve.
    """
    data = await client.get_old(f"/pendentesRecibo/{cliente}/{moeda}")
    return json.dumps(data, ensure_ascii=False, default=str)
