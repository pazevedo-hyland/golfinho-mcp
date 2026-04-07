"""Clientes tools — list, get, update customers."""

from __future__ import annotations

import json
from typing import Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def list_clientes(
    descricao: Optional[str] = None,
    contribuinte: Optional[str] = None,
    telefone: Optional[str] = None,
) -> str:
    """Pesquisar clientes no gGest.

    Filtros opcionais:
    - descricao: nome parcial do cliente
    - contribuinte: NIF/contribuinte
    - telefone: número de telefone

    Devolve lista de clientes com código, nome, NIF, morada, contactos.
    """
    params: dict[str, str] = {}
    if descricao:
        params["descricao"] = descricao
    if contribuinte:
        params["contribuinte"] = contribuinte
    if telefone:
        params["telefone"] = telefone

    data = await client.get_v1("/clientes", params=params or None)
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def get_cliente(codigo: int) -> str:
    """Obter a ficha completa de um cliente pelo seu código numérico.

    Inclui: nome, morada, NIF, contactos (telefone, email, fax),
    condições comerciais (preço, descontos, prazo pagamento, expedição),
    vendedor, moeda, limite de crédito, observações, dados pessoais,
    faturação eletrónica, e flags operacionais.
    """
    data = await client.get_v1(f"/clientes/{codigo}")
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def update_cliente(
    codigo: int,
    descricao: Optional[str] = None,
    morada: Optional[str] = None,
    morada2: Optional[str] = None,
    codpostal: Optional[str] = None,
    pais: Optional[str] = None,
    telefone1: Optional[str] = None,
    telemovel1: Optional[str] = None,
    email1: Optional[str] = None,
    contribuinte: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    expedicao: Optional[str] = None,
    vendedor: Optional[int] = None,
    moeda: Optional[str] = None,
    obs: Optional[str] = None,
    inativo: Optional[bool] = None,
    zona: Optional[str] = None,
    grupo: Optional[str] = None,
) -> str:
    """Atualizar campos de um cliente existente.

    Apenas os campos fornecidos são alterados — os restantes mantêm-se.
    Campos comuns: nome, morada, código postal, país, telefone, email,
    NIF, prazo pagamento, expedição, vendedor, moeda, observações, inativo.
    """
    payload: dict = {}
    if descricao is not None:
        payload["descricao"] = descricao
    if morada is not None:
        payload["morada"] = morada
    if morada2 is not None:
        payload["morada2"] = morada2
    if codpostal is not None:
        payload["codpostal"] = codpostal
    if pais is not None:
        payload["pais"] = pais
    if telefone1 is not None:
        payload["telefone1"] = telefone1
    if telemovel1 is not None:
        payload["telemovel1"] = telemovel1
    if email1 is not None:
        payload["email1"] = email1
    if contribuinte is not None:
        payload["contribuinte"] = contribuinte
    if prazo_pagamento is not None:
        payload["prazo_pagamento"] = prazo_pagamento
    if expedicao is not None:
        payload["expedicao"] = expedicao
    if vendedor is not None:
        payload["vendedor"] = vendedor
    if moeda is not None:
        payload["moeda"] = moeda
    if obs is not None:
        payload["obs"] = obs
    if inativo is not None:
        payload["inativo"] = inativo
    if zona is not None:
        payload["zona"] = zona
    if grupo is not None:
        payload["grupo"] = grupo

    if not payload:
        return "Nenhum campo fornecido para atualizar."

    data = await client.put_v1(f"/clientes/{codigo}", json=payload)
    return json.dumps(data, ensure_ascii=False, default=str) if data else "Cliente atualizado com sucesso."
