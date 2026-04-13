"""Integration tests — verify which gGest API endpoints are accessible with current credentials.

Run:  pytest tests/test_api_access.py -v
Requires GGEST_* environment variables (reads .env automatically).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dotenv() -> None:
    """Minimal .env loader — no extra dependency needed."""
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    env_path = os.path.abspath(env_path)
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not os.environ.get(key):
                os.environ[key] = value


_load_dotenv()

HOST = os.environ.get("GGEST_HOST", "golfinhosoftware.pcscloud.net")
USERNAME = os.environ.get("GGEST_USERNAME", "")
PASSWORD = os.environ.get("GGEST_PASSWORD", "")
DB_SERVIDOR = os.environ.get("GGEST_DB_SERVIDOR", "")
DB_PORTA = os.environ.get("GGEST_DB_PORTA", "")
DB_BASE_DADOS = os.environ.get("GGEST_DB_BASE_DADOS", "")
DB_UTILIZADOR = os.environ.get("GGEST_DB_UTILIZADOR", "")
DB_PASSWORD = os.environ.get("GGEST_DB_PASSWORD", "")

BASE_V1 = f"https://{HOST}/api/v1"
BASE_OLD = f"https://{HOST}/api"

# ---------------------------------------------------------------------------
# Module-level cache for the token (avoids re-login per test)
# ---------------------------------------------------------------------------

_cached_token: str | None = None
_cached_old_token: str | None = None
_db_configured: bool = False


async def _get_token() -> str:
    """Login once, cache the token for all tests."""
    global _cached_token
    if _cached_token:
        return _cached_token
    if not USERNAME or not PASSWORD:
        pytest.skip("GGEST_USERNAME / GGEST_PASSWORD not set")
    async with httpx.AsyncClient(timeout=30.0) as c:
        resp = await c.post(
            f"{BASE_V1}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
    assert resp.status_code == 200, (
        f"Login failed: {resp.status_code} {resp.text[:300]}"
    )
    data = resp.json()
    _cached_token = data.get("access_token")
    assert _cached_token, f"No access_token in response: {data}"
    return _cached_token


async def _get_old_token() -> str:
    """Login to the old API once, cache the token for all tests."""
    global _cached_old_token
    if _cached_old_token:
        return _cached_old_token
    if not USERNAME or not PASSWORD:
        pytest.skip("GGEST_USERNAME / GGEST_PASSWORD not set")
    async with httpx.AsyncClient(timeout=30.0) as c:
        resp = await c.post(
            f"{BASE_OLD}/pedirToken",
            json={"utilizador": USERNAME, "palavrapasse": PASSWORD},
        )
    assert resp.status_code == 200, (
        f"Old API login failed: {resp.status_code} {resp.text[:300]}"
    )
    data = resp.json()
    _cached_old_token = data.get("token")
    assert _cached_old_token, f"No token in old API response: {data}"
    return _cached_old_token


async def _ensure_db(token: str) -> None:
    """Configure DB once per session."""
    global _db_configured
    if _db_configured or not DB_SERVIDOR or not DB_BASE_DADOS:
        return
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as c:
        resp = await c.put(
            f"{BASE_OLD}/configurarAcessoBD",
            headers=headers,
            json={
                "hfsql_servidor": DB_SERVIDOR,
                "hfsql_porta": DB_PORTA,
                "hfsql_basedados": DB_BASE_DADOS,
                "hfsql_utilizador": DB_UTILIZADOR,
                "hfsql_palavrapasse": DB_PASSWORD,
            },
        )
    assert resp.status_code < 400, (
        f"DB config failed: {resp.status_code} {resp.text[:300]}"
    )
    _db_configured = True


# ---------------------------------------------------------------------------
# Helper to make requests (fresh client per call — no event loop issues)
# ---------------------------------------------------------------------------


async def _get(base: str, path: str, headers: dict[str, str]) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30.0) as c:
        return await c.get(f"{base}{path}", headers=headers)


async def _post(
    base: str, path: str, headers: dict[str, str], payload: dict[str, Any]
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30.0) as c:
        return await c.post(f"{base}{path}", headers=headers, json=payload)


@pytest.fixture
async def auth_headers() -> dict[str, str]:
    token = await _get_token()
    await _ensure_db(token)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def old_auth_headers() -> dict[str, str]:
    old_token = await _get_old_token()
    # DB config uses v1 token
    v1_token = await _get_token()
    await _ensure_db(v1_token)
    return {"Authorization": f"Bearer {old_token}"}


# ===========================================================================
# Tests — API v1 (New)
# ===========================================================================


class TestAuthEndpoint:
    async def test_login(self, auth_headers: dict) -> None:
        """Login works (implicitly verified by the auth_headers fixture)."""
        assert auth_headers


# -- Artigos ----------------------------------------------------------------


class TestArtigos:
    async def test_list_artigos(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/artigos", auth_headers)
        assert resp.status_code == 200, (
            f"list_artigos: {resp.status_code} {resp.text[:200]}"
        )

    async def test_get_artigo(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/artigos/1", auth_headers)
        # 200 = found, 404 = artigo 1 doesn't exist (both are valid access)
        assert resp.status_code in (200, 404), (
            f"get_artigo: {resp.status_code} {resp.text[:200]}"
        )


# -- Clientes ---------------------------------------------------------------


class TestClientes:
    async def test_list_clientes(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/clientes", auth_headers)
        assert resp.status_code == 200, (
            f"list_clientes: {resp.status_code} {resp.text[:200]}"
        )

    async def test_get_cliente(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/clientes/2", auth_headers)
        assert resp.status_code in (200, 404), (
            f"get_cliente: {resp.status_code} {resp.text[:200]}"
        )


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
    async def test_lookup(self, auth_headers: dict, entity: str) -> None:
        resp = await _get(BASE_V1, f"/{entity}", auth_headers)
        assert resp.status_code == 200, (
            f"lookup {entity}: {resp.status_code} {resp.text[:200]}"
        )


# -- IVA --------------------------------------------------------------------


class TestIVA:
    async def test_ivas(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/ivas", auth_headers)
        assert resp.status_code == 200, f"ivas: {resp.status_code} {resp.text[:200]}"

    async def test_isencoes_iva(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/isencoes_iva", auth_headers)
        assert resp.status_code == 200, (
            f"isencoes_iva: {resp.status_code} {resp.text[:200]}"
        )

    async def test_regimes_iva(self, auth_headers: dict) -> None:
        resp = await _get(BASE_V1, "/regimes_iva", auth_headers)
        assert resp.status_code == 200, (
            f"regimes_iva: {resp.status_code} {resp.text[:200]}"
        )


# ===========================================================================
# Tests — Old API
# ===========================================================================


class TestSistema:
    async def test_ler_data_hora(self, old_auth_headers: dict) -> None:
        resp = await _get(BASE_OLD, "/lerDataHora", old_auth_headers)
        assert resp.status_code == 200, (
            f"lerDataHora: {resp.status_code} {resp.text[:200]}"
        )

    async def test_pendentes_recibo(self, old_auth_headers: dict) -> None:
        resp = await _get(BASE_OLD, "/pendentesRecibo/2/EUR", old_auth_headers)
        assert resp.status_code == 200, (
            f"pendentesRecibo: {resp.status_code} {resp.text[:200]}"
        )


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
    async def test_mapa(self, old_auth_headers: dict, path: str, payload: dict) -> None:
        resp = await _post(BASE_OLD, path, old_auth_headers, payload)
        assert resp.status_code == 200, f"{path}: {resp.status_code} {resp.text[:300]}"
