"""Integration tests — verify which gGest API endpoints are accessible with current credentials.

Run:  pytest tests/test_api_access.py -v
Fast: pytest tests/test_api_access.py -v -n auto   (parallel with xdist)
Requires GGEST_* environment variables (reads .env automatically via conftest).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from ggest_mcp.http_client import client

# All tests use the session-scoped authenticated client (connection pooling + shared auth)
pytestmark = pytest.mark.usefixtures("ggest_client")


# ---------------------------------------------------------------------------
# Helper — allows specific status codes (e.g. 404 for "get by code")
# ---------------------------------------------------------------------------


async def _expect_ok(coro, *, allow_404: bool = False) -> Any:
    """Await an API call; optionally accept 404 as valid."""
    try:
        return await coro
    except httpx.HTTPStatusError as e:
        if allow_404 and e.response.status_code == 404:
            return None
        raise


# ===========================================================================
# Tests — API v1 (New)
# ===========================================================================


class TestAuthEndpoint:
    async def test_login(self) -> None:
        """Login works (implicitly verified by the ggest_client fixture)."""
        assert client.has_tokens


# -- Artigos ----------------------------------------------------------------


class TestArtigos:
    async def test_list_artigos(self) -> None:
        data = await client.get_v1("/artigos")
        assert data is not None

    async def test_get_artigo(self) -> None:
        await _expect_ok(client.get_v1("/artigos/1"), allow_404=True)


# -- Clientes ---------------------------------------------------------------


class TestClientes:
    async def test_list_clientes(self) -> None:
        data = await client.get_v1("/clientes")
        assert data is not None

    async def test_get_cliente(self) -> None:
        await _expect_ok(client.get_v1("/clientes/2"), allow_404=True)


# -- Lookup entities --------------------------------------------------------

LOOKUP_ENTITIES = [
    "areas_negocio",
    "armazens",
    "documentos",
    "expedicoes",
    "formulas",
    "grupos",
    "grupos_entidade",
    "idiomas",
    "marcas",
    "moedas",
    "paises",
    "prefixos_paises",
    "postos",
    "prazos_pagamento",
    "series",
    "textos",
    "tipos_artigo",
    "tipos_pagamento",
    "unidades",
    "unidades_unece",
    "vendedores",
    "zonas",
]


class TestLookupEntities:
    @pytest.mark.parametrize("entity", LOOKUP_ENTITIES)
    async def test_lookup(self, entity: str) -> None:
        data = await client.get_v1(f"/{entity}")
        assert data is not None


# -- IVA --------------------------------------------------------------------


class TestIVA:
    async def test_ivas(self) -> None:
        data = await client.get_v1("/ivas")
        assert data is not None

    async def test_isencoes_iva(self) -> None:
        data = await client.get_v1("/isencoes_iva")
        assert data is not None

    async def test_regimes_iva(self) -> None:
        data = await client.get_v1("/regimes_iva")
        assert data is not None


# ===========================================================================
# Tests — Old API
# ===========================================================================


class TestSistema:
    async def test_ler_data_hora(self) -> None:
        data = await client.get_old("/lerDataHora")
        assert data is not None

    async def test_pendentes_recibo(self) -> None:
        data = await client.get_old("/pendentesRecibo/2/EUR")
        assert data is not None


# -- Mapas / Reports -------------------------------------------------------

# Minimal valid payloads for each report endpoint
_MAPA_PAYLOADS: dict[str, dict[str, Any]] = {
    "/mapaVendasGerais": {
        "Da_data_hora": "2026-01-01T00:00:00",
        "A_data_hora": "2026-01-31T23:59:59",
        "validos": True,
        "anulados": False,
        "vendas": True,
        "recibos": True,
        "contacorrente": True,
    },
    "/mapaExtratoClientes": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
        "apenas_clientes_ativos": True,
        "documentos_procurar": 1,
        "mostrar_saldo_anterior": True,
        "cobranca_normal": True,
        "cobranca_em_dificuldade": True,
        "cobranca_incobravel": True,
    },
    "/mapaIdadeSaldosClientes": {
        "cobranca_normal": True,
        "cobranca_em_dificuldade": True,
        "cobranca_incobravel": True,
        "incluir_entidades_inativas": False,
    },
    "/mapaTopArtigosMaisVendidos": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
        "numero_artigos": 5,
        "total_ou_quantidade": "T",
        "total_com_iva": True,
    },
    "/mapaVendasArtigosPorGrupo": {
        "Da_data_hora": "2026-01-01T00:00:00",
        "A_data_hora": "2026-01-31T23:59:59",
        "incluir_IVA": True,
        "somente_quantidades_superior_zero": True,
        "incluir_descontos_cabecalho": True,
    },
    "/mapaVendasArtigosResumo": {
        "Da_data_hora": "2026-01-01T00:00:00",
        "A_data_hora": "2026-01-31T23:59:59",
        "valores_sem_IVA": False,
        "retirar_descontos_cab": False,
    },
    "/mapaVolumeVendasPorData": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
    },
    "/mapaVolumeVendasPorMes": {
        "do_mes": 1,
        "ao_mes": 3,
        "ano": 2026,
    },
    "/mapaVolumeVendasPorVendedor": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
    },
    "/mapaVolumeVendasPorPosto": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
    },
    "/mapaVolumeVendasPorEstabelecimento": {
        "da_data": "2026-01-01",
        "a_data": "2026-01-31",
    },
    "/mapaComparacaoAnualVolumeVendas": {
        "ano1": 2026,
        "ano2": 2025,
        "periodo_analise": 1,
    },
}


class TestMapas:
    @pytest.mark.parametrize(
        "path,payload", list(_MAPA_PAYLOADS.items()), ids=list(_MAPA_PAYLOADS.keys())
    )
    async def test_mapa(self, path: str, payload: dict) -> None:
        data = await client.post_old(path, json=payload)
        assert data is not None
