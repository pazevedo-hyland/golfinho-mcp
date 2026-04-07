"""Artigos tools — list, get, update articles/products."""

from __future__ import annotations

import json
from typing import Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def list_artigos(
    descricao: Optional[str] = None,
    codigo: Optional[str] = None,
    barras: Optional[str] = None,
) -> str:
    """Pesquisar artigos/produtos no gGest.

    Filtros opcionais:
    - descricao: texto parcial no nome do artigo
    - codigo: código exato ou parcial
    - barras: código de barras

    Devolve lista de artigos com código, descrição, preços, IVA e stock.
    """
    params: dict[str, str] = {}
    if descricao:
        params["descricao"] = descricao
    if codigo:
        params["codigo"] = codigo
    if barras:
        params["barras"] = barras

    data = await client.get_v1("/artigos", params=params or None)
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def get_artigo(codigo: str) -> str:
    """Obter a ficha completa de um artigo pelo seu código.

    Inclui: descrição, preços (pvp1-4), taxas de IVA, descontos,
    unidade, marca, grupo/família/subfamília, dimensões, stock,
    dados financeiros (última compra/venda, margens de lucro) e flags operacionais.
    """
    data = await client.get_v1(f"/artigos/{codigo}")
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def update_artigo(
    codigo: str,
    descricao: Optional[str] = None,
    preco1: Optional[float] = None,
    preco2: Optional[float] = None,
    preco3: Optional[float] = None,
    preco4: Optional[float] = None,
    iva_venda1_codigo: Optional[int] = None,
    unidade_principal: Optional[str] = None,
    marca: Optional[str] = None,
    grupo: Optional[str] = None,
    familia: Optional[str] = None,
    subfamilia: Optional[str] = None,
    observacao: Optional[str] = None,
    inativo: Optional[bool] = None,
    codigo_barras: Optional[str] = None,
    descricao_extensa: Optional[str] = None,
    referencia: Optional[str] = None,
) -> str:
    """Atualizar campos de um artigo existente.

    Apenas os campos fornecidos são alterados — os restantes mantêm-se.
    Campos comuns: descricao, preco1-4, IVA, unidade, marca, grupo/família,
    observação, inativo, código de barras, descrição extensa, referência.
    """
    payload: dict = {}
    if descricao is not None:
        payload["descricao"] = descricao
    if preco1 is not None:
        payload["preco1"] = preco1
    if preco2 is not None:
        payload["preco2"] = preco2
    if preco3 is not None:
        payload["preco3"] = preco3
    if preco4 is not None:
        payload["preco4"] = preco4
    if iva_venda1_codigo is not None:
        payload["iva_venda1_codigo"] = iva_venda1_codigo
    if unidade_principal is not None:
        payload["unidade_principal"] = unidade_principal
    if marca is not None:
        payload["marca"] = marca
    if grupo is not None:
        payload["grupo"] = grupo
    if familia is not None:
        payload["familia"] = familia
    if subfamilia is not None:
        payload["subfamilia"] = subfamilia
    if observacao is not None:
        payload["observacao"] = observacao
    if inativo is not None:
        payload["inativo"] = inativo
    if codigo_barras is not None:
        payload["codigo_barras"] = codigo_barras
    if descricao_extensa is not None:
        payload["descricao_extensa"] = descricao_extensa
    if referencia is not None:
        payload["referencia"] = referencia

    if not payload:
        return "Nenhum campo fornecido para atualizar."

    data = await client.put_v1(f"/artigos/{codigo}", json=payload)
    return json.dumps(data, ensure_ascii=False, default=str) if data else "Artigo atualizado com sucesso."
