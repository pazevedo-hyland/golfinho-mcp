"""Artigos tools — list, get, create, update articles/products."""

from __future__ import annotations

import json
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def list_artigos(
    descricao: Optional[str] = None,
    codigo: Optional[str] = None,
    barras: Optional[str] = None,
) -> str:
    """Pesquisar artigos/produtos no gGest.

    Filtros opcionais (pelo menos um recomendado para limitar resultados):
    - descricao: texto parcial no nome do artigo (ex: "café")
    - codigo: código exato ou parcial (ex: "CAFE" encontra "CAFE-001")
    - barras: código de barras EAN
    Se nenhum filtro for passado, devolve todos os artigos.

    Retorna (JSON) — lista de artigos, cada um com:
    - codigo, descricao, descricao_extensa, referencia
    - preco1, preco2, preco3, preco4 (tabelas de preço)
    - iva_venda1_codigo, iva_venda1_taxa (IVA de venda)
    - unidade_principal, marca, grupo, familia, subfamilia
    - movimenta_stock, inativo
    - codigo_barras, observacao

    Exemplo:
        list_artigos(descricao="café")
        list_artigos(codigo="SERV")
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

    Retorna (JSON) — todos os campos do artigo, incluindo:
    - Identificação: codigo, descricao, descricao_extensa, codigo_barras, referencia
    - Preços: preco1, preco2, preco3, preco4 (4 tabelas de PVP)
    - IVA: iva_venda1_codigo, iva_venda1_taxa, iva_compra_codigo, iva_compra_taxa
    - Classificação: unidade_principal, marca, grupo, familia, subfamilia, tipo
    - Dimensões: dimensoes (peso, volume, etc.)
    - Financeiro: financeiro (margens de lucro, última compra/venda, PMC)
    - Flags: movimenta_stock, inativo, lancar_por_valor, pedir_preco, pedir_quantidade
    - Fornecedor: fornecedor_principal
    - Descontos: descontos (estrutura de descontos por tabela)

    Exemplo:
        get_artigo(codigo="CAFE-001")
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
    Usar get_artigo() primeiro para ver os valores atuais.

    Retorna (JSON): artigo atualizado com todos os campos (mesma
    estrutura de get_artigo), ou "Artigo atualizado com sucesso."

    Exemplo — atualizar preço:
        update_artigo(codigo="CAFE-001", preco1=1.50)

    Exemplo — desativar artigo:
        update_artigo(codigo="PROD-OLD", inativo=True)

    Exemplo — mudar grupo e família:
        update_artigo(codigo="ART-001", grupo="BEBIDAS", familia="QUENTES")
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
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Artigo atualizado com sucesso."
    )


@mcp.tool()
async def create_artigo(
    codigo: str,
    descricao: str,
    codigo_barras: Optional[str] = None,
    descricao_extensa: Optional[str] = None,
    referencia: Optional[str] = None,
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
    movimenta_stock: Optional[bool] = None,
    inativo: Optional[bool] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar um novo artigo/produto no gGest.

    Parâmetros obrigatórios:
    - codigo: código único do artigo (ex: "ART-001", "SERV-010")
    - descricao: nome/descrição curta do artigo

    Parâmetros opcionais mais comuns:
    - codigo_barras: EAN/código de barras
    - descricao_extensa: descrição longa para documentos
    - referencia: referência interna ou do fornecedor
    - preco1..preco4: até 4 tabelas de preço (€)
    - iva_venda1_codigo: código da taxa de IVA de venda (int)
      → usar list_ivas(tipo="taxas") para obter códigos válidos
    - unidade_principal: unidade de medida (ex: "UN", "KG", "LT")
    - marca, grupo, familia, subfamilia: classificação do artigo
      → usar lookup_entity("grupos"), lookup_entity("marcas") para ver códigos
    - movimenta_stock: se o artigo afeta stock (default: sim)
    - inativo: criar já como inativo
    - extras: campos adicionais em formato dict (para campos avançados
      não listados acima, ex: {"natureza": "M", "comissao": 5.0})

    Retorna (JSON): artigo criado com todos os campos (mesma estrutura
    de get_artigo), ou "Artigo criado com sucesso."
    Se o código já existir, a API devolve erro 409 (conflito).

    Exemplo — artigo simples:
        create_artigo(
            codigo="CAFE-001",
            descricao="Café Expresso",
            preco1=1.20,
            iva_venda1_codigo=1,
            unidade_principal="UN",
            grupo="BEBIDAS",
        )

    Exemplo — serviço (sem stock):
        create_artigo(
            codigo="SERV-010",
            descricao="Consultoria IT (hora)",
            preco1=75.00,
            unidade_principal="HH",
            movimenta_stock=False,
        )
    """
    payload: dict[str, Any] = {"codigo": codigo, "descricao": descricao}
    if codigo_barras is not None:
        payload["codigo_barras"] = codigo_barras
    if descricao_extensa is not None:
        payload["descricao_extensa"] = descricao_extensa
    if referencia is not None:
        payload["referencia"] = referencia
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
    if movimenta_stock is not None:
        payload["movimenta_stock"] = movimenta_stock
    if inativo is not None:
        payload["inativo"] = inativo
    if extras:
        payload.update(extras)

    data = await client.post_v1("/artigos", json=payload)
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Artigo criado com sucesso."
    )
