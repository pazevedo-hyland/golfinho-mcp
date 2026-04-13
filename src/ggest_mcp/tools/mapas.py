"""Mapas/Reports tools — sales reports, client statements, aging, top products."""

from __future__ import annotations

import json
from typing import Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp
from ggest_mcp.pagination import paginate_response


@mcp.tool()
async def mapa_vendas_gerais(
    da_data_hora: str,
    a_data_hora: str,
    vendedor: Optional[int] = None,
    do_cliente: Optional[int] = None,
    ao_cliente: Optional[int] = None,
    lista_series: Optional[list[str]] = None,
    lista_postos: Optional[list[int]] = None,
    validos: bool = True,
    anulados: bool = False,
    vendas: bool = True,
    recibos: bool = True,
    contacorrente: bool = True,
    pagina: int = 1,
    itens_por_pagina: int = 50,
) -> str:
    """Relatório de vendas gerais — lista todos os documentos comerciais num período.

    Parâmetros obrigatórios:
    - da_data_hora: data/hora início (ISO8601, ex: "2026-01-01T00:00:00")
    - a_data_hora: data/hora fim (ISO8601, ex: "2026-03-31T23:59:59")

    Filtros opcionais:
    - vendedor: código do vendedor (0 = todos)
    - do_cliente/ao_cliente: intervalo de códigos de cliente
    - lista_series: séries específicas (ex: ["F2026"])
    - lista_postos: postos específicos (ex: [1, 2])
    - validos/anulados/vendas/recibos/contacorrente: tipos a incluir

    Paginação (client-side, resultados podem ser muitos):
    - pagina: número da página (default 1)
    - itens_por_pagina: itens por página (default 50, max 200)

    Retorna (JSON):
    - dados: lista de documentos, cada um com:
        - doc_codigo, doc_numero, doc_serie, doc_ano
        - entidade_codigo, entidade_descricao, entidade_contribuinte
        - total_documento, total_iva, total_sem_iva
        - data_doc, data_venc, vendedor, posto
    - _paginacao: {pagina, itens_por_pagina, total_itens, total_paginas}

    Exemplo:
        mapa_vendas_gerais(
            da_data_hora="2026-01-01T00:00:00",
            a_data_hora="2026-03-31T23:59:59",
        )
    """
    payload: dict = {
        "Da_data_hora": da_data_hora,
        "A_data_hora": a_data_hora,
        "validos": validos,
        "anulados": anulados,
        "vendas": vendas,
        "recibos": recibos,
        "contacorrente": contacorrente,
    }
    if vendedor is not None:
        payload["vendedor"] = vendedor
    if do_cliente is not None:
        payload["Do_cliente"] = do_cliente
    if ao_cliente is not None:
        payload["Ao_cliente"] = ao_cliente
    if lista_series:
        payload["lista_series"] = lista_series
    if lista_postos:
        payload["lista_postos"] = lista_postos

    data = await client.post_old("/mapaVendasGerais", json=payload)
    return paginate_response(data, pagina=pagina, itens_por_pagina=itens_por_pagina)


@mcp.tool()
async def mapa_extrato_clientes(
    da_data: str,
    a_data: str,
    cliente: Optional[int] = None,
    moeda: Optional[str] = None,
    grupo: Optional[str] = None,
    zona: Optional[str] = None,
    vendedor: Optional[int] = None,
    apenas_clientes_ativos: bool = True,
    documentos_procurar: int = 1,
    mostrar_saldo_anterior: bool = True,
    pagina: int = 1,
    itens_por_pagina: int = 50,
) -> str:
    """Extrato de conta corrente de clientes — movimentos de débito e crédito.

    Parâmetros obrigatórios:
    - da_data: data início (ISO8601, ex: "2026-01-01")
    - a_data: data fim (ISO8601, ex: "2026-03-31")

    Filtros opcionais:
    - cliente: código do cliente (0 ou omitir = todos)
    - moeda: código da moeda
    - grupo/zona/vendedor: filtros adicionais
    - documentos_procurar: 1=Todos, 2=Pendentes, 3=Pendentes até data fim
    - mostrar_saldo_anterior: incluir saldo anterior à data início

    Paginação (client-side, resultados podem ser muitos):
    - pagina: número da página (default 1)
    - itens_por_pagina: itens por página (default 50, max 200)

    Retorna (JSON):
    - dados: lista de movimentos, cada um com:
        - entidade_codigo, entidade_descricao
        - doc_codigo, doc_numero, doc_serie, doc_ano
        - data_doc, data_venc
        - debito, credito, saldo_acumulado
        - descricao_documento
    - _paginacao: {pagina, itens_por_pagina, total_itens, total_paginas}

    Exemplo:
        mapa_extrato_clientes(da_data="2026-01-01", a_data="2026-03-31", cliente=5)
    """
    payload: dict = {
        "da_data": da_data,
        "a_data": a_data,
        "apenas_clientes_ativos": apenas_clientes_ativos,
        "documentos_procurar": documentos_procurar,
        "mostrar_saldo_anterior": mostrar_saldo_anterior,
        "cobranca_normal": True,
        "cobranca_em_dificuldade": True,
        "cobranca_incobravel": True,
    }
    if cliente is not None:
        payload["cliente"] = cliente
    if moeda:
        payload["moeda"] = moeda
    if grupo:
        payload["grupo"] = grupo
    if zona:
        payload["zona"] = zona
    if vendedor is not None:
        payload["vendedor"] = vendedor

    data = await client.post_old("/mapaExtratoClientes", json=payload)
    return paginate_response(data, pagina=pagina, itens_por_pagina=itens_por_pagina)


@mcp.tool()
async def mapa_idade_saldos(
    incluir_entidades_inativas: bool = False,
) -> str:
    """Mapa de idade de saldos de clientes (aging report).

    Mostra os saldos de cada cliente agrupados por antiguidade do vencimento.

    Parâmetro opcional:
    - incluir_entidades_inativas: incluir clientes inativos (default: false)

    Retorna (JSON) — lista de clientes com saldos, cada um com:
    - entidade_codigo, entidade_descricao
    - nao_vencido: montante ainda dentro do prazo
    - ate_30_dias: vencido há menos de 30 dias
    - de_30_a_60_dias: vencido entre 30 e 60 dias
    - de_61_a_90_dias: vencido entre 61 e 90 dias
    - mais_de_90_dias: vencido há mais de 90 dias
    - total: saldo total do cliente

    Exemplo:
        mapa_idade_saldos()
        mapa_idade_saldos(incluir_entidades_inativas=True)
    """
    payload = {
        "cobranca_normal": True,
        "cobranca_em_dificuldade": True,
        "cobranca_incobravel": True,
        "incluir_entidades_inativas": incluir_entidades_inativas,
    }
    data = await client.post_old("/mapaIdadeSaldosClientes", json=payload)
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def mapa_top_artigos(
    da_data: str,
    a_data: str,
    numero_artigos: int = 20,
    total_ou_quantidade: str = "T",
    total_com_iva: bool = True,
) -> str:
    """Top artigos mais vendidos num período.

    Parâmetros obrigatórios:
    - da_data: data início (ISO8601, ex: "2026-01-01")
    - a_data: data fim (ISO8601, ex: "2026-03-31")

    Opcionais:
    - numero_artigos: quantos artigos mostrar (1-50, default 20)
    - total_ou_quantidade: "T" = ordenar por valor total, "Q" = por quantidade
    - total_com_iva: valores com IVA incluído (default: true)

    Retorna (JSON) — lista dos artigos mais vendidos, cada um com:
    - artigo (código), descricao
    - quantidade: total vendido no período
    - total: valor total de vendas (com ou sem IVA conforme parâmetro)

    Exemplo:
        mapa_top_artigos(da_data="2026-01-01", a_data="2026-06-30", numero_artigos=10)
    """
    payload = {
        "da_data": da_data,
        "a_data": a_data,
        "numero_artigos": min(max(numero_artigos, 1), 50),
        "total_ou_quantidade": total_ou_quantidade,
        "total_com_iva": total_com_iva,
    }
    data = await client.post_old("/mapaTopArtigosMaisVendidos", json=payload)
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
async def mapa_vendas_artigos(
    da_data_hora: str,
    a_data_hora: str,
    modo: str = "grupo",
    vendedor: Optional[int] = None,
    marca: Optional[str] = None,
    cliente: Optional[int] = None,
    grupo_codigo: Optional[str] = None,
    familia_codigo: Optional[str] = None,
    subfamilia_codigo: Optional[str] = None,
    lista_series: Optional[list[str]] = None,
    lista_postos: Optional[list[int]] = None,
    incluir_iva: bool = True,
    pagina: int = 1,
    itens_por_pagina: int = 50,
) -> str:
    """Vendas de artigos — por grupo ou resumo individual.

    Parâmetros obrigatórios:
    - da_data_hora: data/hora início (ISO8601, ex: "2026-01-01T00:00:00")
    - a_data_hora: data/hora fim (ISO8601, ex: "2026-03-31T23:59:59")
    - modo: "grupo" ou "resumo"

    Modo "grupo" — vendas agrupadas por grupo de artigo:
      Filtros: vendedor, marca, cliente, lista_series, lista_postos
      Retorna por grupo: grupo_codigo, grupo_descricao, total_com_iva,
      total_sem_iva, total_quant (quantidade total do grupo)

    Modo "resumo" — vendas individuais por artigo:
      Filtros adicionais: grupo_codigo, familia_codigo, subfamilia_codigo
      Retorna por artigo: artigo (código), descricao, quant, total,
      total_com_iva, grupo, grupo_descricao

    Paginação (client-side):
    - pagina: número da página (default 1)
    - itens_por_pagina: itens por página (default 50, max 200)

    Retorna (JSON):
    - dados: lista (conforme modo acima)
    - _paginacao: {pagina, itens_por_pagina, total_itens, total_paginas}

    Exemplo — vendas por grupo:
        mapa_vendas_artigos(
            da_data_hora="2026-01-01T00:00:00",
            a_data_hora="2026-03-31T23:59:59",
            modo="grupo",
        )

    Exemplo — vendas do grupo BEBIDAS por artigo:
        mapa_vendas_artigos(
            da_data_hora="2026-01-01T00:00:00",
            a_data_hora="2026-03-31T23:59:59",
            modo="resumo",
            grupo_codigo="BEBIDAS",
        )
    """
    if modo == "grupo":
        payload: dict = {
            "Da_data_hora": da_data_hora,
            "A_data_hora": a_data_hora,
            "incluir_IVA": incluir_iva,
            "somente_quantidades_superior_zero": True,
            "incluir_descontos_cabecalho": True,
        }
        if vendedor is not None:
            payload["vendedor"] = vendedor
        if marca:
            payload["marca"] = marca
        if cliente is not None:
            payload["cliente"] = cliente
        if lista_series:
            payload["lista_series"] = lista_series
        if lista_postos:
            payload["lista_postos"] = lista_postos

        data = await client.post_old("/mapaVendasArtigosPorGrupo", json=payload)

    elif modo == "resumo":
        payload = {
            "Da_data_hora": da_data_hora,
            "A_data_hora": a_data_hora,
            "valores_sem_IVA": not incluir_iva,
            "retirar_descontos_cab": False,
        }
        if vendedor is not None:
            payload["vendedor"] = vendedor
        if marca:
            payload["marca_codigo"] = marca
        if grupo_codigo:
            payload["grupo_codigo"] = grupo_codigo
        if familia_codigo:
            payload["familia_codigo"] = familia_codigo
        if subfamilia_codigo:
            payload["subfamilia_codigo"] = subfamilia_codigo
        if lista_series:
            payload["lista_series"] = lista_series
        if lista_postos:
            payload["lista_postos"] = lista_postos

        data = await client.post_old("/mapaVendasArtigosResumo", json=payload)

    else:
        return f"Modo '{modo}' inválido. Use 'grupo' ou 'resumo'."

    return paginate_response(data, pagina=pagina, itens_por_pagina=itens_por_pagina)


@mcp.tool()
async def mapa_volume_vendas(
    dimensao: str,
    da_data: Optional[str] = None,
    a_data: Optional[str] = None,
    ano1: Optional[int] = None,
    ano2: Optional[int] = None,
    do_mes: Optional[int] = None,
    ao_mes: Optional[int] = None,
    ano: Optional[int] = None,
    vendedor: Optional[int] = None,
    posto: Optional[int] = None,
    estabelecimento: Optional[int] = None,
    periodo_analise: int = 1,
) -> str:
    """Volume de vendas por diferentes dimensões.

    Parâmetro obrigatório:
    - dimensao: escolher uma de:
      - "data": vendas por dia (requer da_data, a_data)
      - "mes": vendas por mês (requer do_mes, ao_mes, ano)
      - "vendedor": vendas por vendedor (requer da_data, a_data; opcional: vendedor)
      - "posto": vendas por posto (requer da_data, a_data; opcional: posto)
      - "estabelecimento": por estabelecimento (requer da_data, a_data)
      - "comparacao_anual": comparar dois anos (requer ano1, ano2;
        opcional: periodo_analise 1=até data sistema, 2=ano completo)

    Retorna (JSON) — lista de registos com valores com e sem IVA.
    Os campos variam por dimensão, mas incluem tipicamente:
    - total_com_iva, total_sem_iva, total_iva
    - Chave da dimensão: data, mes, vendedor_codigo, posto, estabelecimento, etc.

    Exemplo — vendas diárias num período:
        mapa_volume_vendas(
            dimensao="data",
            da_data="2026-01-01",
            a_data="2026-01-31",
        )

    Exemplo — vendas mensais de um ano:
        mapa_volume_vendas(dimensao="mes", do_mes=1, ao_mes=12, ano=2026)

    Exemplo — comparação entre dois anos:
        mapa_volume_vendas(dimensao="comparacao_anual", ano1=2026, ano2=2025)
    """
    if dimensao == "data":
        payload = {"da_data": da_data, "a_data": a_data}
        data = await client.post_old("/mapaVolumeVendasPorData", json=payload)

    elif dimensao == "mes":
        payload = {"do_mes": do_mes, "ao_mes": ao_mes, "ano": ano}
        data = await client.post_old("/mapaVolumeVendasPorMes", json=payload)

    elif dimensao == "vendedor":
        payload: dict = {"da_data": da_data, "a_data": a_data}
        if vendedor is not None:
            payload["vendedor"] = vendedor
        data = await client.post_old("/mapaVolumeVendasPorVendedor", json=payload)

    elif dimensao == "posto":
        payload = {"da_data": da_data, "a_data": a_data}
        if posto is not None:
            payload["posto"] = posto
        data = await client.post_old("/mapaVolumeVendasPorPosto", json=payload)

    elif dimensao == "estabelecimento":
        payload = {"da_data": da_data, "a_data": a_data}
        if estabelecimento is not None:
            payload["estabelecimento"] = estabelecimento
        data = await client.post_old(
            "/mapaVolumeVendasPorEstabelecimento", json=payload
        )

    elif dimensao == "comparacao_anual":
        payload = {
            "ano1": ano1,
            "ano2": ano2,
            "periodo_analise": periodo_analise,
        }
        data = await client.post_old("/mapaComparacaoAnualVolumeVendas", json=payload)

    else:
        return (
            f"Dimensão '{dimensao}' inválida. "
            "Use: data, mes, vendedor, posto, estabelecimento, ou comparacao_anual."
        )

    return json.dumps(data, ensure_ascii=False, default=str)
