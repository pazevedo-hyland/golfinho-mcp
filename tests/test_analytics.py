"""Integration tests for analytics tools — call the tool functions directly.

These tools aggregate from multiple API endpoints internally, so we test
them by calling the Python functions (not raw HTTP) after authenticating.

Run:  pytest tests/test_analytics.py -v
Requires GGEST_* environment variables (reads .env automatically).
"""

from __future__ import annotations

import json

import pytest

from ggest_mcp.tools.analytics import (
    analise_cliente,
    analise_cobranca,
    analise_rentabilidade,
    comparacao_periodos,
    resumo_financeiro,
    top_clientes_revenue,
)

# All tests in this file need the authenticated singleton client.
pytestmark = pytest.mark.usefixtures("ggest_client")


class TestTopClientesRevenue:
    async def test_returns_ranked_clients(self) -> None:

        result = await top_clientes_revenue(
            da_data="2026-01-01", a_data="2026-03-31", top_n=5
        )
        data = json.loads(result)
        assert "clientes" in data
        assert "total_geral" in data
        assert "periodo" in data
        assert isinstance(data["clientes"], list)
        assert len(data["clientes"]) <= 5
        # If there are clients, verify structure
        if data["clientes"]:
            c = data["clientes"][0]
            assert "codigo" in c
            assert "descricao" in c
            assert "total_facturado" in c
            assert "percentagem_total" in c
            assert "n_documentos" in c

    async def test_ranking_is_descending(self) -> None:

        result = await top_clientes_revenue(
            da_data="2026-01-01", a_data="2026-03-31", top_n=10
        )
        data = json.loads(result)
        clients = data["clientes"]
        if len(clients) >= 2:
            for i in range(len(clients) - 1):
                assert clients[i]["total_facturado"] >= clients[i + 1]["total_facturado"]

    async def test_percentages_sum_correctly(self) -> None:

        result = await top_clientes_revenue(
            da_data="2026-01-01", a_data="2026-03-31", top_n=100
        )
        data = json.loads(result)
        if data["clientes"]:
            total_pct = sum(c["percentagem_total"] for c in data["clientes"])
            # Should be ~100% if we got all clients
            assert total_pct > 0
            assert total_pct <= 100.1  # rounding tolerance


class TestAnaliseCliente:
    async def test_returns_client_profile(self) -> None:

        # First find a client with sales
        ranking = json.loads(await top_clientes_revenue(
            da_data="2026-01-01", a_data="2026-03-31", top_n=1
        ))
        if not ranking["clientes"]:
            pytest.skip("No clients with sales in period")

        cliente_cod = ranking["clientes"][0]["codigo"]
        result = await analise_cliente(
            cliente=cliente_cod,
            da_data="2026-01-01",
            a_data="2026-03-31",
            top_n_artigos=5,
        )
        data = json.loads(result)

        # Verify structure
        assert "cliente" in data
        assert "revenue" in data
        assert "top_artigos" in data
        assert "saldo_pendente" in data
        assert data["cliente"]["codigo"] == cliente_cod
        assert data["revenue"]["total_facturado"] >= 0
        assert isinstance(data["top_artigos"], list)
        assert len(data["top_artigos"]) <= 5

    async def test_top_artigos_structure(self) -> None:

        ranking = json.loads(await top_clientes_revenue(
            da_data="2026-01-01", a_data="2026-03-31", top_n=1
        ))
        if not ranking["clientes"]:
            pytest.skip("No clients with sales in period")

        cliente_cod = ranking["clientes"][0]["codigo"]
        result = await analise_cliente(
            cliente=cliente_cod,
            da_data="2026-01-01",
            a_data="2026-03-31",
        )
        data = json.loads(result)

        if data["top_artigos"]:
            art = data["top_artigos"][0]
            assert "artigo" in art
            assert "descricao" in art
            assert "quantidade" in art
            assert "total_com_iva" in art


class TestResumoFinanceiro:
    async def test_returns_dashboard(self) -> None:

        result = await resumo_financeiro(ano=2026, top_n_artigos=5, top_n_clientes=3)
        data = json.loads(result)

        assert data["ano"] == 2026
        assert "revenue_total" in data
        assert "revenue_mensal" in data
        assert "comparacao_anual" in data
        assert "top_artigos" in data
        assert "top_clientes" in data
        assert "idade_saldos" in data
        assert "revenue_por_vendedor" in data

    async def test_top_clientes_limited(self) -> None:

        result = await resumo_financeiro(ano=2026, top_n_clientes=3)
        data = json.loads(result)
        assert len(data["top_clientes"]) <= 3

    async def test_comparacao_includes_both_years(self) -> None:

        result = await resumo_financeiro(ano=2026, ano_anterior=2025)
        data = json.loads(result)
        assert data["comparacao_anual"]["ano_atual"] == 2026
        assert data["comparacao_anual"]["ano_anterior"] == 2025


class TestAnaliseRentabilidade:
    async def test_returns_product_margins(self) -> None:

        result = await analise_rentabilidade(
            da_data="2026-01-01", a_data="2026-03-31", top_n=5
        )
        data = json.loads(result)

        assert "periodo" in data
        assert "total_vendas_sem_iva" in data
        assert "artigos" in data
        assert isinstance(data["artigos"], list)
        assert len(data["artigos"]) <= 5

    async def test_product_structure(self) -> None:

        result = await analise_rentabilidade(
            da_data="2026-01-01", a_data="2026-03-31", top_n=3
        )
        data = json.loads(result)
        if data["artigos"]:
            art = data["artigos"][0]
            assert "artigo" in art
            assert "descricao" in art
            assert "quantidade" in art
            assert "total_sem_iva" in art
            assert "preco_medio" in art

    async def test_descending_order(self) -> None:

        result = await analise_rentabilidade(
            da_data="2026-01-01", a_data="2026-03-31", top_n=10
        )
        data = json.loads(result)
        artigos = data["artigos"]
        if len(artigos) >= 2:
            for i in range(len(artigos) - 1):
                assert artigos[i]["total_sem_iva"] >= artigos[i + 1]["total_sem_iva"]


class TestAnaliseCobranca:
    async def test_returns_aging_and_risk(self) -> None:

        result = await analise_cobranca()
        data = json.loads(result)

        assert "idade_saldos" in data
        assert "clientes_em_risco" in data
        assert "total" in data["clientes_em_risco"]
        assert "detalhes" in data["clientes_em_risco"]
        assert isinstance(data["clientes_em_risco"]["detalhes"], list)

    async def test_risk_clients_structure(self) -> None:

        result = await analise_cobranca()
        data = json.loads(result)

        for cr in data["clientes_em_risco"]["detalhes"]:
            assert "codigo" in cr
            assert "descricao" in cr
            assert "estado_cobranca" in cr
            assert cr["estado_cobranca"] in ("Difícil", "Incobrável")


class TestComparacaoPeriodos:
    async def test_compares_two_months(self) -> None:

        result = await comparacao_periodos(
            periodo1_de="2026-01-01",
            periodo1_ate="2026-01-31",
            periodo2_de="2026-02-01",
            periodo2_ate="2026-02-28",
            top_n_artigos=5,
        )
        data = json.loads(result)

        assert "periodo_1" in data
        assert "periodo_2" in data
        assert "variacao" in data

        for key in ("periodo_1", "periodo_2"):
            p = data[key]
            assert "total_facturado" in p
            assert "n_documentos" in p
            assert "ticket_medio" in p
            assert "top_artigos" in p

        v = data["variacao"]
        assert "total_facturado_pct" in v
        assert "n_documentos_pct" in v
        assert "ticket_medio_pct" in v

    async def test_period_metadata(self) -> None:

        result = await comparacao_periodos(
            periodo1_de="2026-01-01",
            periodo1_ate="2026-01-31",
            periodo2_de="2026-02-01",
            periodo2_ate="2026-02-28",
        )
        data = json.loads(result)
        assert data["periodo_1"]["periodo"]["de"] == "2026-01-01"
        assert data["periodo_1"]["periodo"]["ate"] == "2026-01-31"
        assert data["periodo_2"]["periodo"]["de"] == "2026-02-01"
        assert data["periodo_2"]["periodo"]["ate"] == "2026-02-28"
