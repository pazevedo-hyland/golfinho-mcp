"""IVA tools — list VAT rates, exemptions, and regimes."""

from __future__ import annotations

import json
from typing import Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def list_ivas(
    tipo: Optional[str] = None,
) -> str:
    """Consultar taxas de IVA, motivos de isenção e regimes de IVA.

    Parâmetro 'tipo' (opcional):
    - "taxas" (default): lista as taxas de IVA (código, taxa, tipo, regime)
    - "isencoes": lista os motivos de isenção de IVA (código, descrição, norma)
    - "regimes": lista os regimes de IVA (código, descrição, dedução, bens usados)
    - "todos": devolve as três listas combinadas num objeto

    Exemplos de uso:
    - "Qual a taxa de IVA normal?" → list_ivas(tipo="taxas")
    - "Que motivos de isenção existem?" → list_ivas(tipo="isencoes")
    """
    tipo = (tipo or "taxas").lower()

    if tipo == "taxas":
        data = await client.get_v1("/ivas")
        return json.dumps(data, ensure_ascii=False, default=str)

    if tipo == "isencoes":
        data = await client.get_v1("/isencoes_iva")
        return json.dumps(data, ensure_ascii=False, default=str)

    if tipo == "regimes":
        data = await client.get_v1("/regimes_iva")
        return json.dumps(data, ensure_ascii=False, default=str)

    if tipo == "todos":
        taxas = await client.get_v1("/ivas")
        isencoes = await client.get_v1("/isencoes_iva")
        regimes = await client.get_v1("/regimes_iva")
        combined = {
            "taxas_iva": taxas,
            "isencoes_iva": isencoes,
            "regimes_iva": regimes,
        }
        return json.dumps(combined, ensure_ascii=False, default=str)

    return f"Tipo '{tipo}' inválido. Use: taxas, isencoes, regimes, ou todos."
