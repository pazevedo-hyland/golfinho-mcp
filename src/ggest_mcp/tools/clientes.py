"""Clientes tools — list, get, create, update customers."""

from __future__ import annotations

import json
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def list_clientes(
    descricao: Optional[str] = None,
    contribuinte: Optional[str] = None,
    telefone: Optional[str] = None,
) -> str:
    """Pesquisar clientes no gGest.

    Filtros opcionais (pelo menos um recomendado para limitar resultados):
    - descricao: nome parcial do cliente (ex: "Silva")
    - contribuinte: NIF/contribuinte (ex: "123456789")
    - telefone: número de telefone
    Se nenhum filtro for passado, devolve todos os clientes.

    Retorna (JSON) — lista de clientes, cada um com:
    - codigo, descricao (nome), contribuinte (NIF)
    - morada, morada2, codpostal, pais
    - telefone1..4, telemovel1..4, email1..4, fax, web
    - vendedor, moeda, prazo_pagamento, expedicao
    - grupo, zona, inativo, difi_cobranca
    - limitecredito, docs_bloqueados

    Exemplo:
        list_clientes(descricao="Silva")
        list_clientes(contribuinte="123456789")
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

    Retorna (JSON) — todos os campos do cliente, incluindo:
    - Identificação: codigo, descricao (nome), descricao2, contribuinte (NIF)
    - Endereço: morada, morada2, codpostal, pais, latitude, longitude
    - Contactos: telefone1..4, telemovel1..4, email1..4, fax, web
    - Comercial: preco (tabela de preço), desct_art, prazo_pagamento,
      expedicao, vendedor, vendedor_fixo, moeda
    - Crédito: limitecredito, limite_vencimento, limite_emitido,
      docs_bloqueados, difi_cobranca (0=Normal, 1=Difícil, 2=Incobrável)
    - Classificação: grupo, zona, rota, area_negocio, idioma
    - Fiscal: espaco_fiscal, sujeito_passivo, iva_isencao, retencao,
      retencao_taxa, enviar_faturacao_eletronica, mail_faturacao_eletronica
    - Pessoal: bi, bi_validade, seg_social, utente_saude, data_nascimento, sexo
    - Flags: inativo, administracao_publica, ecovalor, resumo_faturas

    Exemplo:
        get_cliente(codigo=1)
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
    Usar get_cliente() primeiro para ver os valores atuais.

    Retorna (JSON): cliente atualizado com todos os campos (mesma
    estrutura de get_cliente), ou "Cliente atualizado com sucesso."

    Exemplo — atualizar contacto:
        update_cliente(codigo=1, email1="novo@email.pt", telemovel1="912345678")

    Exemplo — alterar condições comerciais:
        update_cliente(codigo=42, prazo_pagamento="PP30", vendedor=3)

    Exemplo — desativar cliente:
        update_cliente(codigo=99, inativo=True)
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
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Cliente atualizado com sucesso."
    )


@mcp.tool()
async def create_cliente(
    descricao: str,
    codigo: Optional[int] = None,
    morada: Optional[str] = None,
    morada2: Optional[str] = None,
    codpostal: Optional[str] = None,
    pais: Optional[str] = None,
    contribuinte: Optional[str] = None,
    telefone1: Optional[str] = None,
    telemovel1: Optional[str] = None,
    email1: Optional[str] = None,
    espaco_fiscal: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    expedicao: Optional[str] = None,
    vendedor: Optional[int] = None,
    moeda: Optional[str] = None,
    zona: Optional[str] = None,
    grupo: Optional[str] = None,
    obs: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar um novo cliente no gGest.

    Parâmetros obrigatórios:
    - descricao: nome do cliente (ex: "João Silva, Lda.")

    Parâmetros opcionais mais comuns:
    - codigo: código numérico (None = atribuição automática pelo servidor)
    - morada, morada2, codpostal, pais: endereço
    - contribuinte: NIF / número de contribuinte
    - telefone1, telemovel1, email1: contactos principais
    - espaco_fiscal: espaço fiscal (ex: "PT")
    - prazo_pagamento: código do prazo de pagamento
      → usar lookup_entity("prazos_pagamento") para ver códigos válidos
    - expedicao: código do método de expedição
    - vendedor: código do vendedor associado
      → usar lookup_entity("vendedores") para ver códigos válidos
    - moeda: código da moeda (ex: "EUR")
    - zona, grupo: classificação do cliente
      → usar lookup_entity("zonas"), lookup_entity("grupos_entidade")
    - obs: observações de texto livre
    - extras: campos adicionais em formato dict (para campos avançados
      não listados acima, ex: {"retencao": true, "retencao_taxa": 25.0})

    Retorna (JSON): cliente criado com todos os campos (mesma estrutura
    de get_cliente), ou "Cliente criado com sucesso."
    O servidor atribui o próximo código disponível se codigo=None.

    Exemplo — cliente empresa:
        create_cliente(
            descricao="Padaria Central, Lda.",
            contribuinte="123456789",
            morada="Rua da Padaria, 10",
            codpostal="1000-001",
            pais="PT",
            email1="padaria@email.pt",
            moeda="EUR",
        )

    Exemplo — cliente particular (mínimo):
        create_cliente(descricao="Maria Santos")
    """
    payload: dict[str, Any] = {"descricao": descricao}
    if codigo is not None:
        payload["codigo"] = codigo
    if morada is not None:
        payload["morada"] = morada
    if morada2 is not None:
        payload["morada2"] = morada2
    if codpostal is not None:
        payload["codpostal"] = codpostal
    if pais is not None:
        payload["pais"] = pais
    if contribuinte is not None:
        payload["contribuinte"] = contribuinte
    if telefone1 is not None:
        payload["telefone1"] = telefone1
    if telemovel1 is not None:
        payload["telemovel1"] = telemovel1
    if email1 is not None:
        payload["email1"] = email1
    if espaco_fiscal is not None:
        payload["espaco_fiscal"] = espaco_fiscal
    if prazo_pagamento is not None:
        payload["prazo_pagamento"] = prazo_pagamento
    if expedicao is not None:
        payload["expedicao"] = expedicao
    if vendedor is not None:
        payload["vendedor"] = vendedor
    if moeda is not None:
        payload["moeda"] = moeda
    if zona is not None:
        payload["zona"] = zona
    if grupo is not None:
        payload["grupo"] = grupo
    if obs is not None:
        payload["obs"] = obs
    if extras:
        payload.update(extras)

    data = await client.post_v1("/clientes", json=payload)
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Cliente criado com sucesso."
    )
