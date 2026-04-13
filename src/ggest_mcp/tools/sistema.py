"""Sistema tools — system date/time and pending receipts."""

from __future__ import annotations

import json

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def get_pendentes_recibo(cliente: int, moeda: str = "EUR") -> str:
    """Listar documentos pendentes de pagamento (para recibo) de um cliente.

    Útil para: (1) verificar quanto um cliente deve, (2) preparar dados
    para gravar_recibo() — os campos codigo, numero, serie e ano de cada
    documento pendente são usados diretamente nas linhas do recibo.

    Parâmetros:
    - cliente: código numérico do cliente
    - moeda: código da moeda (default: "EUR")

    Retorna (JSON) — lista de documentos pendentes, cada um com:
    - tipo: tipo abreviado (ex: "Fatura")
    - descricao: descrição do tipo de documento
    - codigo: código do tipo (ex: "FT") → usar em gravar_recibo(linhas)
    - numero: número do documento (int) → usar em gravar_recibo(linhas)
    - serie: série do documento (str) → usar em gravar_recibo(linhas)
    - ano: ano do documento (int) → usar em gravar_recibo(linhas)
    - data_doc: data de emissão
    - data_venc: data de vencimento
    - total_documento: valor total do documento (€)
    - total_liquidado: valor já pago (€)
    - total_iva: total de IVA
    - observacao: observações do documento
    O valor em dívida = total_documento - total_liquidado.

    Exemplo:
        get_pendentes_recibo(cliente=1)
        get_pendentes_recibo(cliente=42, moeda="USD")
    """
    data = await client.get_old(f"/pendentesRecibo/{cliente}/{moeda}")
    return json.dumps(data, ensure_ascii=False, default=str)
