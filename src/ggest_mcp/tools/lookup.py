"""Generic entity lookup tool — single tool for ~22 reference entity types."""

from __future__ import annotations

import json
from typing import Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp

# Whitelist of supported entity types and their v1 API paths
_ENTITY_PATHS: dict[str, str] = {
    "areas_negocio": "/areas_negocio",
    "armazens": "/armazens",
    "documentos": "/documentos",
    "expedicoes": "/expedicoes",
    "formulas": "/formulas",
    "grupos": "/grupos",
    "grupos_entidade": "/grupos_entidade",
    "idiomas": "/idiomas",
    "marcas": "/marcas",
    "moedas": "/moedas",
    "paises": "/paises",
    "prefixos_paises": "/prefixos_paises",
    "postos": "/postos",
    "prazos_pagamento": "/prazos_pagamento",
    "series": "/series",
    "textos": "/textos",
    "tipos_artigo": "/tipos_artigo",
    "tipos_pagamento": "/tipos_pagamento",
    "unidades": "/unidades",
    "unidades_unece": "/unidades_unece",
    "vendedores": "/vendedores",
    "zonas": "/zonas",
}


@mcp.tool()
async def lookup_entity(
    entity_type: str,
    codigo: Optional[str] = None,
    grupo: Optional[str] = None,
    familia: Optional[str] = None,
) -> str:
    """Consultar qualquer entidade de referência do gGest.

    Tipos suportados (entity_type):
      areas_negocio, armazens, documentos, expedicoes, formulas, grupos,
      grupos_entidade, idiomas, marcas, moedas, paises, prefixos_paises,
      postos, prazos_pagamento, series, textos, tipos_artigo, tipos_pagamento,
      unidades, unidades_unece, vendedores, zonas, familias, subfamilias.

    Para entidades hierárquicas:
    - familias: requer 'grupo' (ex: lookup_entity("familias", grupo="G01"))
    - subfamilias: requer 'grupo' e 'familia'

    Se 'codigo' for fornecido, devolve o detalhe dessa entidade.
    Caso contrário, devolve a lista completa.

    Retorna (JSON): lista de entidades ou detalhe de uma entidade.
    Cada entidade tem tipicamente: codigo, descricao, e campos específicos
    do tipo (ex: taxa para IVA, prefixo para países).

    ╔══ Tipos mais usados para workflows de escrita ══╗
    ║ "documentos"       → tipos de doc válidos (FT, OR, GT, FC…)  ║
    ║ "series"           → séries documentais ativas ("2026"…)      ║
    ║ "tipos_pagamento"  → formas de pagamento (NUM, TRFB, MB…)    ║
    ║ "vendedores"       → vendedores disponíveis                   ║
    ║ "armazens"         → armazéns para linhas de documentos       ║
    ║ "prazos_pagamento" → prazos para faturas a crédito           ║
    ╚════════════════════════════════════════════════════════════╝

    Exemplo:
        lookup_entity("documentos")  # todos os tipos de documento
        lookup_entity("tipos_pagamento")  # formas de pagamento
        lookup_entity("vendedores", codigo="3")  # detalhe do vendedor 3
        lookup_entity("familias", grupo="G01")  # famílias do grupo G01
    """
    # Handle hierarchical entities (famílias, subfamílias)
    if entity_type == "familias":
        if not grupo:
            return "Erro: para consultar famílias, é necessário fornecer o parâmetro 'grupo'."
        path = f"/grupos/{grupo}/familias"
        if codigo:
            path += f"/{codigo}"
        data = await client.get_v1(path)
        return json.dumps(data, ensure_ascii=False, default=str)

    if entity_type == "subfamilias":
        if not grupo or not familia:
            return "Erro: para consultar subfamílias, é necessário fornecer 'grupo' e 'familia'."
        path = f"/grupos/{grupo}/familias/{familia}/subfamilias"
        if codigo:
            path += f"/{codigo}"
        data = await client.get_v1(path)
        return json.dumps(data, ensure_ascii=False, default=str)

    # Standard flat entities
    base_path = _ENTITY_PATHS.get(entity_type)
    if base_path is None:
        supported = ", ".join(
            sorted(_ENTITY_PATHS.keys()) + ["familias", "subfamilias"]
        )
        return f"Tipo de entidade '{entity_type}' não suportado. Tipos válidos: {supported}"

    path = base_path
    if codigo:
        path += f"/{codigo}"

    data = await client.get_v1(path)
    return json.dumps(data, ensure_ascii=False, default=str)
