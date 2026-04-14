"""Offline unit tests — validate tool payload construction and schema correctness.

These tests mock the HTTP client and verify that each tool builds the correct
payload with correct field names, types, and required fields.
NO gGest server or credentials needed — runs in CI.

Run:  pytest tests/test_tool_schemas.py -v
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — capture the payload sent to the HTTP client
# ---------------------------------------------------------------------------

def _mock_post_old() -> AsyncMock:
    """Mock client.post_old — returns a dummy success response."""
    m = AsyncMock(return_value={"status": "ok"})
    return m


def _mock_post_v1() -> AsyncMock:
    m = AsyncMock(return_value={"codigo": 999, "descricao": "mock"})
    return m


def _mock_put_v1() -> AsyncMock:
    m = AsyncMock(return_value={"codigo": 1, "descricao": "updated"})
    return m


# ---------------------------------------------------------------------------
# Documentos — criar_fatura
# ---------------------------------------------------------------------------

class TestCriarFaturaPayload:
    """Validate criar_fatura builds correct payloads."""

    async def test_minimal_fr_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
            )

        mock.assert_called_once()
        payload = mock.call_args.kwargs["json"]

        # Required fields present with correct values
        assert payload["codigo"] == "FR"
        assert payload["entidade_codigo"] == 1
        assert payload["posto"] == 1
        assert payload["moeda"] == "EUR"
        assert len(payload["linhas"]) == 1

        # Optional fields excluded
        for key in ("serie", "data_doc", "data_venc", "vendedor", "observacao",
                     "referencia", "descritivo", "prazo_pagamento"):
            assert key not in payload, f"Optional field '{key}' should not be in payload"

    async def test_data_mov_auto_filled_on_lines(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                    {"artigo": "ART-002", "descricao": "Teste 2", "quantidade": 2, "preco": 5.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        for linha in payload["linhas"]:
            assert "data_mov" in linha, "data_mov should be auto-filled on every line"

    async def test_data_mov_uses_data_doc_when_provided(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                data_doc="2026-04-13",
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["linhas"][0]["data_mov"] == "2026-04-13"

    async def test_formas_pag_field_name_is_forma_pag(self) -> None:
        """The field must be 'forma_pag', not 'tipo' — API ignores 'tipo'."""
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
                formas_pag=[{"forma_pag": "NUM", "valor": 12.30}],
            )

        payload = mock.call_args.kwargs["json"]
        assert "formas_pag" in payload
        assert payload["formas_pag"][0]["forma_pag"] == "NUM"
        assert "tipo" not in payload["formas_pag"][0]

    async def test_entidade_fields_are_top_level(self) -> None:
        """entidade_descricao etc. must be top-level keys, not nested in extras."""
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
                entidade_descricao="Henrique Gaiao",
                entidade_morada="Rua pandeleira 123",
                entidade_codpostal="1000-001 Lisboa",
                entidade_contribuinte="231622031",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["entidade_descricao"] == "Henrique Gaiao"
        assert payload["entidade_morada"] == "Rua pandeleira 123"
        assert payload["entidade_codpostal"] == "1000-001 Lisboa"
        assert payload["entidade_contribuinte"] == "231622031"

    async def test_ft_codigo(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                codigo="FT",
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "FT"

    async def test_extras_merged_into_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
                extras={"campo_custom": "valor"},
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["campo_custom"] == "valor"

    async def test_endpoint_is_gravar_documento(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura

            await criar_fatura(
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
            )

        # First positional arg is the endpoint path
        assert mock.call_args.args[0] == "/gravarDocumento"


# ---------------------------------------------------------------------------
# Documentos — criar_orcamento
# ---------------------------------------------------------------------------

class TestCriarOrcamentoPayload:

    async def test_or_payload_no_formas_pag(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_orcamento

            await criar_orcamento(
                entidade_codigo=42,
                posto=1,
                linhas=[
                    {"artigo": "SERV-010", "descricao": "Consultoria", "quantidade": 1, "preco": 500.0},
                ],
                vendedor=3,
                observacao="Válido 30 dias",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "OR"
        assert payload["entidade_codigo"] == 42
        assert payload["vendedor"] == 3
        assert payload["observacao"] == "Válido 30 dias"
        assert "formas_pag" not in payload

    async def test_fp_codigo(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_orcamento

            await criar_orcamento(
                codigo="FP",
                entidade_codigo=1,
                posto=1,
                linhas=[
                    {"artigo": "ART-001", "descricao": "Teste", "quantidade": 1, "preco": 10.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "FP"


# ---------------------------------------------------------------------------
# Documentos — criar_nota_credito
# ---------------------------------------------------------------------------

class TestCriarNotaCreditoPayload:

    async def test_nc_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_nota_credito

            await criar_nota_credito(
                entidade_codigo=1,
                posto=1,
                serie="2026",
                referencia="Ref. FT nº 100",
                linhas=[
                    {"artigo": "ART-001", "descricao": "Devolução", "quantidade": 1, "preco": 8.24},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "NC"
        assert payload["referencia"] == "Ref. FT nº 100"
        assert payload["serie"] == "2026"


# ---------------------------------------------------------------------------
# Documentos — criar_guia_transporte
# ---------------------------------------------------------------------------

class TestCriarGuiaTransportePayload:

    async def test_gt_has_required_transport_fields(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_guia_transporte

            await criar_guia_transporte(
                entidade_codigo=5,
                posto=1,
                matricula="AA-00-BB",
                morada_carga="Rua do Armazém, 1, Lisboa",
                morada_descarga="Av. do Cliente, 20, Porto",
                linhas=[
                    {"artigo": "PROD-100", "descricao": "Widget", "quantidade": 50, "preco": 10.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "GT"
        assert payload["matricula"] == "AA-00-BB"
        assert payload["morada_carga"] == "Rua do Armazém, 1, Lisboa"
        assert payload["morada_descarga"] == "Av. do Cliente, 20, Porto"

    async def test_gt_optional_dates(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_guia_transporte

            await criar_guia_transporte(
                entidade_codigo=5,
                posto=1,
                matricula="AA-00-BB",
                morada_carga="Lisboa",
                morada_descarga="Porto",
                data_carga="2026-04-15",
                data_descarga="2026-04-15",
                linhas=[
                    {"artigo": "PROD-100", "descricao": "Widget", "quantidade": 50, "preco": 10.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["data_carga"] == "2026-04-15"
        assert payload["data_descarga"] == "2026-04-15"


# ---------------------------------------------------------------------------
# Documentos — criar_fatura_compra
# ---------------------------------------------------------------------------

class TestCriarFaturaCompraPayload:

    async def test_fc_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import criar_fatura_compra

            await criar_fatura_compra(
                entidade_codigo=10,
                posto=1,
                serie="2026",
                referencia="Fatura fornecedor nº 4521",
                linhas=[
                    {"artigo": "MAT-001", "descricao": "Matéria Prima X",
                     "quantidade": 100, "preco": 2.50, "cod_iva": 23},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "FC"
        assert payload["entidade_codigo"] == 10
        assert payload["referencia"] == "Fatura fornecedor nº 4521"


# ---------------------------------------------------------------------------
# Documentos — gravar_recibo
# ---------------------------------------------------------------------------

class TestGravarReciboPayload:

    async def test_recibo_endpoint_is_gravar_recibo(self) -> None:
        """gravar_recibo must POST to /gravarRecibo, not /gravarDocumento."""
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import gravar_recibo

            await gravar_recibo(
                codigo="RC",
                entidade=1,
                posto=1,
                linhas=[
                    {"codigo": "FT", "numero": 100, "serie": "2026", "ano": 2026,
                     "valor_liquidar": 150.0},
                ],
                formas_pag=[{"forma_pag": "TRFB", "valor": 150.0}],
            )

        assert mock.call_args.args[0] == "/gravarRecibo"

    async def test_recibo_payload_structure(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.documentos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.documentos import gravar_recibo

            await gravar_recibo(
                codigo="RC",
                entidade=1,
                posto=1,
                serie="2026",
                linhas=[
                    {"codigo": "FT", "numero": 100, "serie": "2026", "ano": 2026,
                     "valor_liquidar": 150.0},
                ],
                formas_pag=[{"forma_pag": "TRFB", "valor": 150.0}],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "RC"
        assert payload["entidade"] == 1
        assert payload["moeda"] == "EUR"
        assert payload["posto"] == 1
        assert payload["serie"] == "2026"
        assert len(payload["linhas"]) == 1
        assert payload["formas_pag"][0]["forma_pag"] == "TRFB"


# ---------------------------------------------------------------------------
# Clientes — create_cliente
# ---------------------------------------------------------------------------

class TestCreateClientePayload:

    async def test_minimal_create_no_codigo(self) -> None:
        """Old API auto-assigns codigo — payload must NOT include it."""
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.clientes import create_cliente

            await create_cliente(descricao="Maria Santos")

        payload = mock.call_args.kwargs["json"]
        assert payload["descricao"] == "Maria Santos"
        assert "codigo" not in payload, "Old API auto-assigns codigo"

    async def test_full_create_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.clientes import create_cliente

            await create_cliente(
                descricao="Henrique Gaiao",
                contribuinte="231622031",
                morada="Rua pandeleira 123",
                codpostal="1000-001",
                pais="PT",
                email1="henrique@email.pt",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["descricao"] == "Henrique Gaiao"
        assert payload["contribuinte"] == "231622031"
        assert payload["morada"] == "Rua pandeleira 123"
        assert payload["codpostal"] == "1000-001"
        assert payload["pais"] == "PT"
        assert payload["email1"] == "henrique@email.pt"
        assert "codigo" not in payload

    async def test_endpoint_is_criarCliente(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.clientes import create_cliente

            await create_cliente(descricao="Test")

        assert mock.call_args.args[0] == "/criarCliente"

    async def test_extras_merged(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.clientes import create_cliente

            await create_cliente(
                descricao="Test",
                extras={"retencao": True, "retencao_taxa": 25.0},
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["retencao"] is True
        assert payload["retencao_taxa"] == 25.0


# ---------------------------------------------------------------------------
# Clientes — update_cliente
# ---------------------------------------------------------------------------

class TestUpdateClientePayload:

    async def test_empty_update_returns_message(self) -> None:
        """Calling update_cliente with no fields should NOT hit the API."""
        from ggest_mcp.tools.clientes import update_cliente

        result = await update_cliente(codigo=1)
        assert "nenhum campo" in result.lower()

    async def test_partial_update_payload(self) -> None:
        mock = _mock_put_v1()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.put_v1 = mock
            from ggest_mcp.tools.clientes import update_cliente

            await update_cliente(codigo=1, email1="novo@email.pt", inativo=True)

        payload = mock.call_args.kwargs["json"]
        assert payload["email1"] == "novo@email.pt"
        assert payload["inativo"] is True
        # Only the changed fields — no extraneous keys
        assert "morada" not in payload
        assert "contribuinte" not in payload

    async def test_endpoint_includes_codigo(self) -> None:
        mock = _mock_put_v1()
        with patch("ggest_mcp.tools.clientes.client") as c:
            c.put_v1 = mock
            from ggest_mcp.tools.clientes import update_cliente

            await update_cliente(codigo=42, descricao="Novo Nome")

        assert mock.call_args.args[0] == "/clientes/42"


# ---------------------------------------------------------------------------
# Artigos — create_artigo
# ---------------------------------------------------------------------------

class TestCreateArtigoPayload:

    async def test_minimal_create(self) -> None:
        mock = _mock_post_v1()
        with patch("ggest_mcp.tools.artigos.client") as c:
            c.post_v1 = mock
            from ggest_mcp.tools.artigos import create_artigo

            await create_artigo(codigo="ART-001", descricao="Artigo Teste")

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "ART-001"
        assert payload["descricao"] == "Artigo Teste"

    async def test_full_create_with_prices(self) -> None:
        mock = _mock_post_v1()
        with patch("ggest_mcp.tools.artigos.client") as c:
            c.post_v1 = mock
            from ggest_mcp.tools.artigos import create_artigo

            await create_artigo(
                codigo="CAFE-001",
                descricao="Café Expresso",
                preco1=1.20,
                preco2=1.50,
                iva_venda1_codigo=1,
                unidade_principal="UN",
                grupo="BEBIDAS",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["preco1"] == 1.20
        assert payload["preco2"] == 1.50
        assert payload["iva_venda1_codigo"] == 1
        assert payload["unidade_principal"] == "UN"
        assert payload["grupo"] == "BEBIDAS"

    async def test_endpoint_is_artigos(self) -> None:
        mock = _mock_post_v1()
        with patch("ggest_mcp.tools.artigos.client") as c:
            c.post_v1 = mock
            from ggest_mcp.tools.artigos import create_artigo

            await create_artigo(codigo="X", descricao="Y")

        assert mock.call_args.args[0] == "/artigos"


# ---------------------------------------------------------------------------
# Artigos — update_artigo
# ---------------------------------------------------------------------------

class TestUpdateArtigoPayload:

    async def test_empty_update_returns_message(self) -> None:
        from ggest_mcp.tools.artigos import update_artigo

        result = await update_artigo(codigo="ART-001")
        assert "nenhum campo" in result.lower()

    async def test_partial_update(self) -> None:
        mock = _mock_put_v1()
        with patch("ggest_mcp.tools.artigos.client") as c:
            c.put_v1 = mock
            from ggest_mcp.tools.artigos import update_artigo

            await update_artigo(codigo="ART-001", preco1=15.99, inativo=True)

        payload = mock.call_args.kwargs["json"]
        assert payload["preco1"] == 15.99
        assert payload["inativo"] is True
        assert "descricao" not in payload


# ---------------------------------------------------------------------------
# Assistência Técnica — validation (no API calls)
# ---------------------------------------------------------------------------

class TestAssistenciaTecnicaValidation:

    async def test_invalid_operacao(self) -> None:
        from ggest_mcp.tools.servicos import assistencia_tecnica

        result = await assistencia_tecnica(operacao="invalida", codigo="XX", posto=1)
        assert "inválida" in result.lower()

    async def test_pedido_requires_entidade(self) -> None:
        from ggest_mcp.tools.servicos import assistencia_tecnica

        result = await assistencia_tecnica(operacao="pedido", codigo="PA", posto=1)
        assert "obrigatório" in result.lower()

    async def test_intervencao_requires_numero_serie_ano(self) -> None:
        from ggest_mcp.tools.servicos import assistencia_tecnica

        result = await assistencia_tecnica(operacao="intervencao", codigo="PA", posto=1)
        assert "obrigatório" in result.lower()

    async def test_ordem_servico_requires_entidade_codigo(self) -> None:
        from ggest_mcp.tools.servicos import assistencia_tecnica

        result = await assistencia_tecnica(operacao="ordem_servico", codigo="OS", posto=1)
        assert "obrigatório" in result.lower()

    async def test_pedido_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.servicos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.servicos import assistencia_tecnica

            await assistencia_tecnica(
                operacao="pedido",
                codigo="PA",
                entidade=42,
                posto=1,
                avaria_descrita="Impressora não liga",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "PA"
        assert payload["entidade"] == 42
        assert payload["posto"] == 1
        assert payload["avaria_descrita"] == "Impressora não liga"
        assert mock.call_args.args[0] == "/assistecPedidoAssistenciaNovo"

    async def test_intervencao_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.servicos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.servicos import assistencia_tecnica

            await assistencia_tecnica(
                operacao="intervencao",
                codigo="PA",
                numero=15,
                serie="2026",
                ano=2026,
                posto=1,
                tecnico=3,
                reparacao_efetuada="Fonte substituída",
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["numero"] == 15
        assert payload["serie"] == "2026"
        assert payload["ano"] == 2026
        assert payload["intervencao"]["reparacao_efetuada"] == "Fonte substituída"
        assert payload["intervencao"]["tecnico"] == 3
        assert mock.call_args.args[0] == "/assistecPedidoAssistenciaIntervencaoNova"

    async def test_ordem_servico_payload(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.servicos.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.servicos import assistencia_tecnica

            await assistencia_tecnica(
                operacao="ordem_servico",
                codigo="OS",
                entidade_codigo=42,
                moeda="EUR",
                posto=1,
                linhas=[
                    {"artigo": "MO-001", "descricao": "Mão de obra", "quantidade": 1.5, "preco": 35.0},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "OS"
        assert payload["entidade_codigo"] == 42
        assert payload["moeda"] == "EUR"
        assert len(payload["linhas"]) == 1
        # data_mov should be auto-filled
        assert "data_mov" in payload["linhas"][0]
        assert mock.call_args.args[0] == "/assistecOrdemServicoNova"


# ---------------------------------------------------------------------------
# Produção — criar_producao
# ---------------------------------------------------------------------------

class TestCriarProducaoPayload:

    async def test_all_required_fields_present(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.producao.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.producao import criar_producao

            await criar_producao(
                codigo="PR",
                numero=1,
                serie="2026",
                ano=2026,
                entidade_codigo=1,
                posto=1,
            )

        payload = mock.call_args.kwargs["json"]
        assert payload["codigo"] == "PR"
        assert payload["numero"] == 1
        assert payload["serie"] == "2026"
        assert payload["ano"] == 2026
        assert payload["entidade_codigo"] == 1
        assert payload["posto"] == 1

    async def test_composto_is_dict_not_list(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.producao.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.producao import criar_producao

            await criar_producao(
                codigo="PR",
                numero=1,
                serie="2026",
                ano=2026,
                entidade_codigo=1,
                posto=1,
                composto={"artigo": "BOLO", "quantidade": 50, "preco": 3.50},
                componentes=[
                    {"artigo": "FARINHA", "quantidade": 25, "preco": 0.80},
                ],
            )

        payload = mock.call_args.kwargs["json"]
        assert isinstance(payload["composto"], dict)
        assert isinstance(payload["componentes"], list)

    async def test_endpoint_is_producao_nova(self) -> None:
        mock = _mock_post_old()
        with patch("ggest_mcp.tools.producao.client") as c:
            c.post_old = mock
            from ggest_mcp.tools.producao import criar_producao

            await criar_producao(
                codigo="PR", numero=1, serie="2026", ano=2026,
                entidade_codigo=1, posto=1,
            )

        assert mock.call_args.args[0] == "/producaoNova"
