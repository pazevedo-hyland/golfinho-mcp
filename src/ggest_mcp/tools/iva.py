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
    - "taxas" (default): lista as taxas de IVA
    - "isencoes": lista os motivos de isenção de IVA
    - "regimes": lista os regimes de IVA
    - "todos": devolve as três listas combinadas num objeto

    Retorna (JSON):
    - tipo="taxas": lista com {codigo, descricao, taxa, tipo, regime}
      O campo 'codigo' (int) é o valor a usar em cod_iva nas linhas de
      criar_fatura, criar_orcamento, etc. e gravar_recibo.
    - tipo="isencoes": lista com {codigo, descricao, norma_legal}
    - tipo="regimes": lista com {codigo, descricao, deducao, bens_usados}
    - tipo="todos": {taxas_iva: [...], isencoes_iva: [...], regimes_iva: [...]}

    Exemplos:
        list_ivas()                    # taxas de IVA (default)
        list_ivas(tipo="taxas")        # mesma coisa, explícito
        list_ivas(tipo="isencoes")     # motivos de isenção
        list_ivas(tipo="todos")        # tudo de uma vez
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
