"""Analytics tools — composite business intelligence from multiple API calls.

These tools aggregate data server-side so the LLM receives compact summaries
instead of thousands of raw records.
"""

from __future__ import annotations

import asyncio
import calendar
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from ggest_mcp.app import mcp
from ggest_mcp.http_client import client

_MAX_DAYS = 89  # mapaVendasGerais rejects ranges > 90 days
_MAX_CONCURRENT = 6  # limit concurrent API calls

_api_sem: asyncio.Semaphore | None = None


def _get_sem() -> asyncio.Semaphore:
    """Lazily create semaphore in the running event loop."""
    global _api_sem
    if _api_sem is None:
        _api_sem = asyncio.Semaphore(_MAX_CONCURRENT)
    return _api_sem


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as tools)
# ---------------------------------------------------------------------------


def _monthly_ranges(ano: int) -> list[tuple[str, str]]:
    """Return monthly date ranges covering a full year (each ≤ 31 days)."""
    ranges = []
    for month in range(1, 13):
        last_day = calendar.monthrange(ano, month)[1]
        ranges.append((f"{ano}-{month:02d}-01", f"{ano}-{month:02d}-{last_day:02d}"))
    return ranges


def _merge_top_artigos(raw: list[dict], top_n: int) -> list[dict]:
    """Merge quarterly top-artigos chunks by summing totals per article."""
    merged: dict[str, dict] = {}
    for item in raw:
        key = item.get("artigo") or item.get("codigo") or ""
        if key not in merged:
            merged[key] = {**item, "_total": item.get("total", 0) or 0}
        else:
            merged[key]["_total"] += item.get("total", 0) or 0
    ranked = sorted(merged.values(), key=lambda x: x["_total"], reverse=True)[:top_n]
    for r in ranked:
        r.pop("_total", None)
    return ranked


async def _vendas_gerais_raw(
    da_data_hora: str,
    a_data_hora: str,
    **extra: Any,
) -> list[dict]:
    """Fetch all sales docs for a period, batching in ≤90-day windows concurrently."""
    start = datetime.fromisoformat(da_data_hora)
    end = datetime.fromisoformat(a_data_hora)

    # Build list of windows
    windows: list[tuple[str, str]] = []
    window_start = start
    while window_start < end:
        window_end = min(window_start + timedelta(days=_MAX_DAYS), end)
        windows.append((window_start.isoformat(), window_end.isoformat()))
        window_start = window_end + timedelta(seconds=1)

    async def _fetch(w_start: str, w_end: str) -> list[dict]:
        async with _get_sem():
            payload: dict = {
                "Da_data_hora": w_start,
                "A_data_hora": w_end,
                "validos": True,
                "anulados": False,
                "vendas": True,
                "recibos": True,
                "contacorrente": True,
                **extra,
            }
            data = await client.post_old("/mapaVendasGerais", json=payload)
            if isinstance(data, dict):
                return data.get("dados", [])
            if isinstance(data, list):
                return data
            return []

    results = await asyncio.gather(*[_fetch(s, e) for s, e in windows])
    return [doc for chunk in results for doc in chunk]


async def _aggregate_by_client(
    da_data_hora: str,
    a_data_hora: str,
) -> dict[int, dict]:
    """Aggregate sales by client → {codigo: {descricao, total, n_docs, ...}}."""
    docs = await _vendas_gerais_raw(da_data_hora, a_data_hora)
    clients: dict[int, dict] = {}
    for doc in docs:
        cod = doc.get("entidade_codigo", 0)
        if cod not in clients:
            clients[cod] = {
                "codigo": cod,
                "descricao": doc.get("entidade_descricao", ""),
                "contribuinte": doc.get("entidade_contribuinte", ""),
                "total_facturado": 0.0,
                "total_iva": 0.0,
                "n_documentos": 0,
            }
        c = clients[cod]
        c["total_facturado"] += doc.get("total_documento", 0) or 0
        c["total_iva"] += doc.get("total_iva", 0) or 0
        c["n_documentos"] += 1
    return clients


# ---------------------------------------------------------------------------
# Tool 1: Top Clientes por Revenue
# ---------------------------------------------------------------------------


@mcp.tool()
async def top_clientes_revenue(
    da_data: str,
    a_data: str,
    top_n: int = 20,
) -> str:
    """Top clientes por facturação num período.

    Agrega internamente todos os documentos de venda e devolve um ranking
    compacto dos clientes que mais facturam.

    Parâmetros:
    - da_data: data início (ISO8601, ex: "2025-01-01")
    - a_data: data fim (ISO8601, ex: "2025-12-31")
    - top_n: número de clientes a mostrar (default 20, max 100)

    Devolve lista ordenada com: código, nome, NIF, total facturado,
    total IVA, nº documentos, e % do total geral.
    """
    top_n = max(1, min(top_n, 100))
    da = f"{da_data}T00:00:00"
    a = f"{a_data}T23:59:59"

    clients = await _aggregate_by_client(da, a)
    if not clients:
        return json.dumps({"clientes": [], "total_geral": 0, "periodo": {"de": da_data, "ate": a_data}})

    total_geral = sum(c["total_facturado"] for c in clients.values())
    ranked = sorted(clients.values(), key=lambda c: c["total_facturado"], reverse=True)[:top_n]

    for c in ranked:
        c["percentagem_total"] = round(c["total_facturado"] / total_geral * 100, 1) if total_geral else 0
        c["total_facturado"] = round(c["total_facturado"], 2)
        c["total_iva"] = round(c["total_iva"], 2)

    result = {
        "clientes": ranked,
        "total_geral": round(total_geral, 2),
        "total_clientes_com_vendas": len(clients),
        "periodo": {"de": da_data, "ate": a_data},
    }
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool 2: Análise de Cliente Individual
# ---------------------------------------------------------------------------


@mcp.tool()
async def analise_cliente(
    cliente: int,
    da_data: str,
    a_data: str,
    top_n_artigos: int = 10,
) -> str:
    """Perfil completo de um cliente: revenue, produtos que mais compra, saldo pendente.

    Faz internamente várias chamadas à API e devolve um resumo compacto.

    Parâmetros:
    - cliente: código numérico do cliente
    - da_data: data início do período de análise (ISO8601, ex: "2025-01-01")
    - a_data: data fim (ISO8601, ex: "2025-12-31")
    - top_n_artigos: quantos artigos mostrar no ranking (default 10)

    Devolve:
    - Dados do cliente (nome, NIF, grupo, vendedor, limite crédito, estado cobrança)
    - Revenue total e nº documentos no período
    - Top artigos comprados (código, descrição, quantidade, total)
    - Saldo pendente (documentos por pagar)
    """
    top_n_artigos = max(1, min(top_n_artigos, 50))
    da = f"{da_data}T00:00:00"
    a = f"{a_data}T23:59:59"

    # Run all 4 data fetches concurrently
    async def _fetch_ficha():
        resp = await client.get_v1(f"/clientes/{cliente}")
        return resp.get("data", resp) if isinstance(resp, dict) else resp

    async def _fetch_artigos():
        data = await client.post_old("/mapaVendasArtigosPorGrupo", json={
            "Da_data_hora": da,
            "A_data_hora": a,
            "cliente": cliente,
            "incluir_IVA": True,
            "somente_quantidades_superior_zero": True,
            "incluir_descontos_cabecalho": True,
        })
        return data.get("dados", []) if isinstance(data, dict) else data if isinstance(data, list) else []

    async def _fetch_pendentes():
        try:
            p = await client.get_old(f"/pendentesRecibo/{cliente}/EUR")
            if isinstance(p, list):
                return p
            if isinstance(p, dict):
                return p.get("dados", [])
        except Exception:
            pass
        return []

    ficha, artigos_list, docs, pendentes_list = await asyncio.gather(
        _fetch_ficha(),
        _fetch_artigos(),
        _vendas_gerais_raw(da, a, Do_cliente=cliente, Ao_cliente=cliente),
        _fetch_pendentes(),
    )

    # Ordenar por total e pegar top N
    artigos_sorted = sorted(artigos_list, key=lambda a: a.get("total_com_iva", 0) or 0, reverse=True)[:top_n_artigos]

    total_facturado = sum(d.get("total_documento", 0) or 0 for d in docs)
    n_docs = len(docs)

    saldo_pendente = sum(
        (p.get("total_documento", 0) or 0) - (p.get("total_liquidado", 0) or 0)
        for p in pendentes_list
    )

    # Build result
    difi_map = {0: "Normal", 1: "Difícil", 2: "Incobrável"}
    result = {
        "cliente": {
            "codigo": ficha.get("codigo"),
            "descricao": ficha.get("descricao"),
            "contribuinte": ficha.get("contribuinte"),
            "grupo": ficha.get("grupo"),
            "vendedor": ficha.get("vendedor"),
            "limite_credito": ficha.get("limitecredito"),
            "estado_cobranca": difi_map.get(ficha.get("difi_cobranca", 0), "Desconhecido"),
        },
        "periodo": {"de": da_data, "ate": a_data},
        "revenue": {
            "total_facturado": round(total_facturado, 2),
            "n_documentos": n_docs,
        },
        "top_artigos": [
            {
                "artigo": a.get("artigo_codigo"),
                "descricao": a.get("artigo_descricao"),
                "quantidade": a.get("total_quant"),
                "total_com_iva": round(a.get("total_com_iva", 0) or 0, 2),
                "grupo": a.get("grupo_descricao"),
            }
            for a in artigos_sorted
        ],
        "saldo_pendente": {
            "total": round(saldo_pendente, 2),
            "n_documentos_pendentes": len(pendentes_list),
        },
    }
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool 3: Resumo Financeiro (Dashboard)
# ---------------------------------------------------------------------------


@mcp.tool()
async def resumo_financeiro(
    ano: int,
    ano_anterior: Optional[int] = None,
    top_n_artigos: int = 20,
    top_n_clientes: int = 10,
) -> str:
    """Dashboard financeiro do negócio — resumo completo num só call.

    Agrega internamente vários relatórios e devolve:
    - Revenue mensal do ano
    - Comparação com ano anterior (se pedido)
    - Top artigos mais vendidos
    - Top clientes por facturação
    - Idade de saldos (receivables aging)
    - Revenue por vendedor

    Parâmetros:
    - ano: ano a analisar (ex: 2025)
    - ano_anterior: ano de comparação (default: ano-1)
    - top_n_artigos: quantos artigos no ranking (default 20)
    - top_n_clientes: quantos clientes no ranking (default 10)
    """
    top_n_artigos = max(1, min(top_n_artigos, 50))
    top_n_clientes = max(1, min(top_n_clientes, 50))
    ano_ant = ano_anterior or (ano - 1)

    # ── Define all data-fetch coroutines ──────────────────────────────────

    async def _fetch_volume_mensal():
        return await client.post_old("/mapaVolumeVendasPorMes", json={
            "do_mes": 1, "ao_mes": 12, "ano": ano,
        })

    async def _fetch_comparacao():
        return await client.post_old("/mapaComparacaoAnualVolumeVendas", json={
            "ano1": ano, "ano2": ano_ant, "periodo_analise": 2,
        })

    async def _fetch_top_artigos():
        """Monthly batching + gather for top artigos."""
        async def _one(start: str, end: str):
            async with _get_sem():
                chunk = await client.post_old("/mapaTopArtigosMaisVendidos", json={
                    "da_data": start, "a_data": end,
                    "numero_artigos": top_n_artigos,
                    "total_ou_quantidade": "T", "total_com_iva": True,
                })
                items = chunk.get("dados", chunk) if isinstance(chunk, dict) else chunk if isinstance(chunk, list) else []
                return items
        results = await asyncio.gather(*[_one(s, e) for s, e in _monthly_ranges(ano)])
        return _merge_top_artigos([i for sub in results for i in sub], top_n_artigos)

    async def _fetch_clients():
        return await _aggregate_by_client(
            f"{ano}-01-01T00:00:00", f"{ano}-12-31T23:59:59"
        )

    async def _fetch_idade_saldos():
        return await client.post_old("/mapaIdadeSaldosClientes", json={
            "cobranca_normal": True, "cobranca_em_dificuldade": True,
            "cobranca_incobravel": True, "incluir_entidades_inativas": False,
        })

    async def _fetch_volume_vendedor():
        """Monthly batching + gather for vendedor."""
        async def _one(start: str, end: str):
            async with _get_sem():
                chunk = await client.post_old("/mapaVolumeVendasPorVendedor", json={
                    "da_data": start, "a_data": end,
                })
                items = chunk.get("dados", chunk) if isinstance(chunk, dict) else chunk if isinstance(chunk, list) else []
                return items
        results = await asyncio.gather(*[_one(s, e) for s, e in _monthly_ranges(ano)])
        return [i for sub in results for i in sub]

    # ── Run all 6 blocks concurrently ─────────────────────────────────────

    (volume_mensal, comparacao, top_artigos,
     clients, idade_saldos, volume_vendedor) = await asyncio.gather(
        _fetch_volume_mensal(),
        _fetch_comparacao(),
        _fetch_top_artigos(),
        _fetch_clients(),
        _fetch_idade_saldos(),
        _fetch_volume_vendedor(),
    )

    # ── Post-process client ranking ───────────────────────────────────────

    total_revenue = sum(c["total_facturado"] for c in clients.values())
    top_clients = sorted(clients.values(), key=lambda c: c["total_facturado"], reverse=True)[:top_n_clientes]
    for c in top_clients:
        c["percentagem_total"] = round(c["total_facturado"] / total_revenue * 100, 1) if total_revenue else 0
        c["total_facturado"] = round(c["total_facturado"], 2)
        c["total_iva"] = round(c["total_iva"], 2)

    result = {
        "ano": ano,
        "revenue_total": round(total_revenue, 2),
        "total_clientes_ativos": len(clients),
        "revenue_mensal": volume_mensal,
        "comparacao_anual": {
            "ano_atual": ano,
            "ano_anterior": ano_ant,
            "dados": comparacao,
        },
        "top_artigos": top_artigos,
        "top_clientes": top_clients,
        "idade_saldos": idade_saldos,
        "revenue_por_vendedor": volume_vendedor,
    }
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool 4: Análise de Rentabilidade
# ---------------------------------------------------------------------------


@mcp.tool()
async def analise_rentabilidade(
    da_data: str,
    a_data: str,
    grupo: Optional[str] = None,
    top_n: int = 30,
) -> str:
    """Análise de rentabilidade por produto — cruza vendas com margens.

    Para cada artigo vendido no período, mostra:
    - Quantidade vendida e total facturado
    - Preço médio de venda
    - Margem de lucro (dos dados do artigo, se disponível)

    Parâmetros:
    - da_data / a_data: período (ISO8601, ex: "2025-01-01" / "2025-12-31")
    - grupo: filtrar por grupo de artigos (opcional)
    - top_n: quantos artigos mostrar (default 30, max 100)
    """
    top_n = max(1, min(top_n, 100))
    da = f"{da_data}T00:00:00"
    a = f"{a_data}T23:59:59"

    # 1) Vendas por artigo (resumo)
    payload: dict[str, Any] = {
        "Da_data_hora": da,
        "A_data_hora": a,
        "valores_sem_IVA": True,
        "retirar_descontos_cab": False,
    }
    if grupo:
        payload["grupo_codigo"] = grupo
    vendas = await client.post_old("/mapaVendasArtigosResumo", json=payload)
    vendas_list = vendas.get("dados", []) if isinstance(vendas, dict) else vendas if isinstance(vendas, list) else []

    # Sort by total descending
    vendas_sorted = sorted(vendas_list, key=lambda v: v.get("total", 0) or 0, reverse=True)[:top_n]

    # 2) For each top article, fetch margin data concurrently
    async def _enrich(v: dict) -> dict:
        art_code = v.get("artigo") or v.get("codigo")
        quant = v.get("quant", 0) or 0
        total = v.get("total", 0) or 0
        preco_medio = round(total / quant, 2) if quant else 0

        entry: dict[str, Any] = {
            "artigo": art_code,
            "descricao": v.get("descricao", ""),
            "grupo": v.get("grupo", ""),
            "grupo_descricao": v.get("grupo_descricao", ""),
            "quantidade": quant,
            "total_sem_iva": round(total, 2),
            "preco_medio": preco_medio,
        }

        # Try to get margin from product master (v1 wraps in {"data": ...})
        try:
            async with _get_sem():
                ficha_resp = await client.get_v1(f"/artigos/{art_code}")
            ficha = ficha_resp.get("data", ficha_resp) if isinstance(ficha_resp, dict) else ficha_resp
            entry["pvp1"] = ficha.get("pvp1")
            entry["lucro1"] = ficha.get("lucro1")
            entry["margem_lucro_sobre"] = ficha.get("margem_lucro_sobre")
        except Exception:
            pass

        return entry

    artigos_result = await asyncio.gather(*[_enrich(v) for v in vendas_sorted])

    total_vendas = sum(a["total_sem_iva"] for a in artigos_result)
    result = {
        "periodo": {"de": da_data, "ate": a_data},
        "total_vendas_sem_iva": round(total_vendas, 2),
        "artigos": artigos_result,
    }
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool 5: Análise de Cobrança
# ---------------------------------------------------------------------------


@mcp.tool()
async def analise_cobranca() -> str:
    """Análise de risco de cobrança — clientes com saldos vencidos e dificuldade de cobrança.

    Combina:
    - Idade de saldos (aging buckets: não vencidos, <30d, 30-60d, 61-90d, >90d)
    - Lista de clientes com estado de cobrança difícil ou incobrável
    - Extrato resumido dos clientes em risco

    Não requer parâmetros — analisa o estado atual.

    Devolve:
    - Resumo global de aging
    - Lista de clientes em cobrança difícil/incobrável com saldos
    """
    # 1) Aging global + client list concurrently
    async def _fetch_aging():
        return await client.post_old("/mapaIdadeSaldosClientes", json={
            "cobranca_normal": True, "cobranca_em_dificuldade": True,
            "cobranca_incobravel": True, "incluir_entidades_inativas": False,
        })

    async def _fetch_clientes():
        return await client.get_v1("/clientes")

    idade_saldos, clientes_data = await asyncio.gather(_fetch_aging(), _fetch_clientes())

    clientes_list = clientes_data if isinstance(clientes_data, list) else clientes_data.get("dados", []) if isinstance(clientes_data, dict) else []

    difi_map = {0: "Normal", 1: "Difícil", 2: "Incobrável"}
    clientes_risco = []
    for cl in clientes_list:
        difi = cl.get("difi_cobranca", 0) or 0
        if difi > 0:
            clientes_risco.append({
                "codigo": cl.get("codigo"),
                "descricao": cl.get("descricao"),
                "contribuinte": cl.get("contribuinte"),
                "estado_cobranca": difi_map.get(difi, str(difi)),
                "limite_credito": cl.get("limitecredito"),
                "vendedor": cl.get("vendedor"),
            })

    # 2) Fetch pending amounts for risk clients concurrently
    async def _fetch_pending(cr: dict) -> None:
        try:
            async with _get_sem():
                pendentes = await client.get_old(f"/pendentesRecibo/{cr['codigo']}/EUR")
            plist = pendentes if isinstance(pendentes, list) else pendentes.get("dados", []) if isinstance(pendentes, dict) else []
            cr["saldo_pendente"] = round(
                sum((p.get("total_documento", 0) or 0) - (p.get("total_liquidado", 0) or 0) for p in plist), 2
            )
            cr["n_docs_pendentes"] = len(plist)
        except Exception:
            cr["saldo_pendente"] = None
            cr["n_docs_pendentes"] = None

    await asyncio.gather(*[_fetch_pending(cr) for cr in clientes_risco[:20]])

    result = {
        "idade_saldos": idade_saldos,
        "clientes_em_risco": {
            "total": len(clientes_risco),
            "detalhes": clientes_risco,
        },
    }
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool 6: Comparação de Períodos
# ---------------------------------------------------------------------------


@mcp.tool()
async def comparacao_periodos(
    periodo1_de: str,
    periodo1_ate: str,
    periodo2_de: str,
    periodo2_ate: str,
    top_n_artigos: int = 10,
) -> str:
    """Compara dois períodos: revenue, nº documentos, ticket médio, top artigos.

    Útil para comparar mês a mês, trimestre a trimestre, ou qualquer intervalo.

    Parâmetros:
    - periodo1_de / periodo1_ate: primeiro período (ISO8601 datas)
    - periodo2_de / periodo2_ate: segundo período
    - top_n_artigos: quantos artigos mostrar em cada período (default 10)

    Devolve para cada período:
    - Total facturado, nº documentos, ticket médio
    - Top artigos
    - Variação % entre períodos
    """
    top_n_artigos = max(1, min(top_n_artigos, 50))

    async def _period_stats(de: str, ate: str) -> dict:
        da = f"{de}T00:00:00"
        a = f"{ate}T23:59:59"

        docs = await _vendas_gerais_raw(da, a)
        total = sum(d.get("total_documento", 0) or 0 for d in docs)
        n_docs = len(docs)
        ticket_medio = round(total / n_docs, 2) if n_docs else 0

        top = await client.post_old("/mapaTopArtigosMaisVendidos", json={
            "da_data": de,
            "a_data": ate,
            "numero_artigos": top_n_artigos,
            "total_ou_quantidade": "T",
            "total_com_iva": True,
        })

        return {
            "periodo": {"de": de, "ate": ate},
            "total_facturado": round(total, 2),
            "n_documentos": n_docs,
            "ticket_medio": ticket_medio,
            "top_artigos": top,
        }

    p1, p2 = await asyncio.gather(
        _period_stats(periodo1_de, periodo1_ate),
        _period_stats(periodo2_de, periodo2_ate),
    )

    # Calculate variation
    var_total = None
    if p2["total_facturado"]:
        var_total = round((p1["total_facturado"] - p2["total_facturado"]) / p2["total_facturado"] * 100, 1)

    var_docs = None
    if p2["n_documentos"]:
        var_docs = round((p1["n_documentos"] - p2["n_documentos"]) / p2["n_documentos"] * 100, 1)

    var_ticket = None
    if p2["ticket_medio"]:
        var_ticket = round((p1["ticket_medio"] - p2["ticket_medio"]) / p2["ticket_medio"] * 100, 1)

    result = {
        "periodo_1": p1,
        "periodo_2": p2,
        "variacao": {
            "total_facturado_pct": var_total,
            "n_documentos_pct": var_docs,
            "ticket_medio_pct": var_ticket,
        },
    }
    return json.dumps(result, ensure_ascii=False, default=str)
