"""Documentos tools — gravar documentos comerciais e recibos.

5 tools especializadas por tipo de documento + gravar_recibo.
Todas chamam internamente POST /api/gravarDocumento via _gravar_documento().
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


# ---------------------------------------------------------------------------
# Helper privado (NÃO é tool MCP)
# ---------------------------------------------------------------------------

async def _gravar_documento(payload: dict[str, Any]) -> str:
    """Envia payload para POST /api/gravarDocumento e devolve resultado JSON."""
    # Auto-fill data_mov on lines if missing (API requires it)
    if "linhas" in payload:
        default_dt = payload.get("data_doc") or datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        for linha in payload["linhas"]:
            if "data_mov" not in linha:
                linha["data_mov"] = default_dt

    data = await client.post_old("/gravarDocumento", json=payload)
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Documento gravado com sucesso."
    )


def _build_payload(
    codigo: str,
    entidade_codigo: int,
    posto: int,
    moeda: str,
    *,
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    data_venc: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    vendedor: Optional[int] = None,
    iva_inc: Optional[bool] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    descritivo: Optional[str] = None,
    linhas: Optional[list[dict[str, Any]]] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
    **transport: Any,
) -> dict[str, Any]:
    """Constrói o payload comum a todos os tipos de documento."""
    payload: dict[str, Any] = {
        "codigo": codigo,
        "entidade_codigo": entidade_codigo,
        "moeda": moeda,
        "posto": posto,
    }
    _optionals = {
        "serie": serie,
        "data_doc": data_doc,
        "data_venc": data_venc,
        "prazo_pagamento": prazo_pagamento,
        "vendedor": vendedor,
        "iva_inc": iva_inc,
        "observacao": observacao,
        "referencia": referencia,
        "descritivo": descritivo,
        "linhas": linhas,
        "formas_pag": formas_pag,
        "entidade_descricao": entidade_descricao,
        "entidade_morada": entidade_morada,
        "entidade_codpostal": entidade_codpostal,
        "entidade_contribuinte": entidade_contribuinte,
        "entidade_pais": entidade_pais,
    }
    for k, v in _optionals.items():
        if v is not None:
            payload[k] = v
    for k, v in transport.items():
        if v is not None:
            payload[k] = v
    if extras:
        payload.update(extras)
    return payload


# ---------------------------------------------------------------------------
# TOOL 1 — criar_fatura  (FR / FT / FS)
# ---------------------------------------------------------------------------

@mcp.tool()
async def criar_fatura(
    entidade_codigo: int,
    posto: int,
    linhas: list[dict[str, Any]],
    codigo: str = "FR",
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    data_venc: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    vendedor: Optional[int] = None,
    iva_inc: Optional[bool] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    descritivo: Optional[str] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar uma fatura de venda (FR, FT ou FS).

    Tipos suportados (parâmetro 'codigo'):
      "FR" = Fatura-Recibo (default) — venda a pronto, a mais simples
      "FT" = Fatura — pode exigir dados de transporte conforme a série
      "FS" = Fatura Simplificada — exige NIF válido no cliente

    ╔══ WORKFLOW ══╗
    ║ 1. lookup_entity("series")          → série (ex: "2026")         ║
    ║ 2. get_artigo(codigo)               → confirmar código e preço   ║
    ║ 3. list_ivas(tipo="taxas")          → códigos de IVA (cod_iva)   ║
    ║ 4. lookup_entity("tipos_pagamento") → formas pag (NUM, TRFB…)   ║
    ╚══════════════════════════════════════════════════════════════════╝

    Parâmetros obrigatórios:
    - entidade_codigo: código numérico do cliente
    - posto: posto/caixa (ex: 1)
    - linhas: lista de artigos — cada linha deve ter:
        - artigo: código do artigo (str)
        - descricao: descrição (str, mín. 2 caracteres — obrigatório!)
        - quantidade: quantidade (float)
        - preco: preço unitário (float)
        - cod_iva: código IVA (int, opcional — default do artigo)

    Formas de pagamento (obrigatório para FR e FS):
    - formas_pag: lista de dicts, cada um com:
        - forma_pag: código (ex: "NUM", "TRFB", "MB", "CC")
        - valor: montante (float)
      ⚠ O campo chama-se "forma_pag" (NÃO "tipo").
      Se omitido → documento fica a crédito (conta corrente).

    Dados da entidade (sobrepõem ficha do cliente — só se necessário):
    - entidade_descricao: nome (NÃO "nome")
    - entidade_morada: morada
    - entidade_codpostal: código postal (NÃO "cod_postal")
    - entidade_contribuinte: NIF (NÃO "contribuinte")
    - entidade_pais: código do país

    Exemplo — Fatura-Recibo a pronto:
        criar_fatura(
            entidade_codigo=1,
            posto=1,
            serie="2026",
            linhas=[
                {"artigo": "C13T03U24020",
                 "descricao": "Tinteiro Epson Cyan 603",
                 "quantidade": 1, "preco": 8.24, "cod_iva": 16},
            ],
            formas_pag=[{"forma_pag": "NUM", "valor": 10.14}],
        )

    Exemplo — Fatura a crédito (sem pagamento):
        criar_fatura(
            codigo="FT",
            entidade_codigo=1,
            posto=1,
            linhas=[
                {"artigo": "CAFE-001", "descricao": "Café Expresso",
                 "quantidade": 10, "preco": 1.20},
            ],
        )
    """
    payload = _build_payload(
        codigo, entidade_codigo, posto, moeda,
        serie=serie, data_doc=data_doc, data_venc=data_venc,
        prazo_pagamento=prazo_pagamento, vendedor=vendedor, iva_inc=iva_inc,
        observacao=observacao, referencia=referencia, descritivo=descritivo,
        linhas=linhas, formas_pag=formas_pag,
        entidade_descricao=entidade_descricao, entidade_morada=entidade_morada,
        entidade_codpostal=entidade_codpostal,
        entidade_contribuinte=entidade_contribuinte,
        entidade_pais=entidade_pais, extras=extras,
    )
    return await _gravar_documento(payload)


# ---------------------------------------------------------------------------
# TOOL 2 — criar_orcamento  (OR / FP)
# ---------------------------------------------------------------------------

@mcp.tool()
async def criar_orcamento(
    entidade_codigo: int,
    posto: int,
    linhas: list[dict[str, Any]],
    codigo: str = "OR",
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    data_venc: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    vendedor: Optional[int] = None,
    iva_inc: Optional[bool] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    descritivo: Optional[str] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar um orçamento (OR) ou fatura pro forma (FP).

    Tipos suportados (parâmetro 'codigo'):
      "OR" = Orçamento (default)
      "FP" = Fatura Pro Forma

    Estes documentos NÃO têm formas de pagamento — não geram movimento
    financeiro. São documentos de proposta/previsão.

    Parâmetros obrigatórios:
    - entidade_codigo: código numérico do cliente
    - posto: posto/caixa (ex: 1)
    - linhas: lista de artigos (ver criar_fatura para estrutura)

    Exemplo — Orçamento com desconto:
        criar_orcamento(
            entidade_codigo=42,
            posto=1,
            vendedor=3,
            observacao="Válido por 30 dias",
            linhas=[
                {"artigo": "SERV-010", "descricao": "Consultoria IT",
                 "quantidade": 1, "preco": 500.00, "desc_lin_per1": 10},
            ],
        )
    """
    payload = _build_payload(
        codigo, entidade_codigo, posto, moeda,
        serie=serie, data_doc=data_doc, data_venc=data_venc,
        prazo_pagamento=prazo_pagamento, vendedor=vendedor, iva_inc=iva_inc,
        observacao=observacao, referencia=referencia, descritivo=descritivo,
        linhas=linhas,
        entidade_descricao=entidade_descricao, entidade_morada=entidade_morada,
        entidade_codpostal=entidade_codpostal,
        entidade_contribuinte=entidade_contribuinte,
        entidade_pais=entidade_pais, extras=extras,
    )
    return await _gravar_documento(payload)


# ---------------------------------------------------------------------------
# TOOL 3 — criar_nota_credito  (NC)
# ---------------------------------------------------------------------------

@mcp.tool()
async def criar_nota_credito(
    entidade_codigo: int,
    posto: int,
    linhas: list[dict[str, Any]],
    codigo: str = "NC",
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    vendedor: Optional[int] = None,
    iva_inc: Optional[bool] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    descritivo: Optional[str] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar uma nota de crédito (NC).

    Usado para anular ou corrigir parcialmente uma fatura anterior.
    Indicar em 'referencia' ou 'observacao' qual a fatura de origem.

    Parâmetros obrigatórios:
    - entidade_codigo: código numérico do cliente
    - posto: posto/caixa (ex: 1)
    - linhas: artigos a creditar (ver criar_fatura para estrutura)

    Exemplo — NC referente à fatura FT 100:
        criar_nota_credito(
            entidade_codigo=1,
            posto=1,
            serie="2026",
            referencia="Ref. FT nº 100",
            observacao="Devolução de artigo defeituoso",
            linhas=[
                {"artigo": "C13T03U24020",
                 "descricao": "Tinteiro Epson Cyan 603",
                 "quantidade": 1, "preco": 8.24, "cod_iva": 16},
            ],
        )
    """
    payload = _build_payload(
        codigo, entidade_codigo, posto, moeda,
        serie=serie, data_doc=data_doc,
        vendedor=vendedor, iva_inc=iva_inc,
        observacao=observacao, referencia=referencia, descritivo=descritivo,
        linhas=linhas, formas_pag=formas_pag,
        entidade_descricao=entidade_descricao, entidade_morada=entidade_morada,
        entidade_codpostal=entidade_codpostal,
        entidade_contribuinte=entidade_contribuinte,
        entidade_pais=entidade_pais, extras=extras,
    )
    return await _gravar_documento(payload)


# ---------------------------------------------------------------------------
# TOOL 4 — criar_guia_transporte  (GT)
# ---------------------------------------------------------------------------

@mcp.tool()
async def criar_guia_transporte(
    entidade_codigo: int,
    posto: int,
    linhas: list[dict[str, Any]],
    matricula: str,
    morada_carga: str,
    morada_descarga: str,
    codigo: str = "GT",
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    data_carga: Optional[str] = None,
    data_descarga: Optional[str] = None,
    vendedor: Optional[int] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar uma guia de transporte (GT).

    Documento obrigatório para acompanhar mercadorias em trânsito.
    Requer matrícula e moradas de carga/descarga.

    Parâmetros obrigatórios:
    - entidade_codigo: código numérico do cliente
    - posto: posto/caixa (ex: 1)
    - linhas: artigos transportados (ver criar_fatura para estrutura)
    - matricula: matrícula do veículo (ex: "AA-00-BB")
    - morada_carga: local de carga (ex: "Rua do Armazém, 1, Lisboa")
    - morada_descarga: local de descarga

    Opcionais:
    - data_carga / data_descarga: datas (formato "YYYY-MM-DD")

    Exemplo:
        criar_guia_transporte(
            entidade_codigo=5,
            posto=1,
            serie="2026",
            matricula="AA-00-BB",
            morada_carga="Rua do Armazém, 1, Lisboa",
            morada_descarga="Av. do Cliente, 20, Porto",
            data_carga="2026-04-15",
            data_descarga="2026-04-15",
            linhas=[
                {"artigo": "PROD-100", "descricao": "Widget Industrial",
                 "quantidade": 50, "preco": 10.00},
            ],
        )
    """
    payload = _build_payload(
        codigo, entidade_codigo, posto, moeda,
        serie=serie, data_doc=data_doc,
        vendedor=vendedor, observacao=observacao, referencia=referencia,
        linhas=linhas,
        entidade_descricao=entidade_descricao, entidade_morada=entidade_morada,
        entidade_codpostal=entidade_codpostal,
        entidade_contribuinte=entidade_contribuinte,
        entidade_pais=entidade_pais, extras=extras,
        matricula=matricula, data_carga=data_carga,
        morada_carga=morada_carga, data_descarga=data_descarga,
        morada_descarga=morada_descarga,
    )
    return await _gravar_documento(payload)


# ---------------------------------------------------------------------------
# TOOL 5 — criar_fatura_compra  (FC)
# ---------------------------------------------------------------------------

@mcp.tool()
async def criar_fatura_compra(
    entidade_codigo: int,
    posto: int,
    linhas: list[dict[str, Any]],
    codigo: str = "FC",
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    data_venc: Optional[str] = None,
    prazo_pagamento: Optional[str] = None,
    iva_inc: Optional[bool] = None,
    observacao: Optional[str] = None,
    referencia: Optional[str] = None,
    descritivo: Optional[str] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    entidade_descricao: Optional[str] = None,
    entidade_morada: Optional[str] = None,
    entidade_codpostal: Optional[str] = None,
    entidade_contribuinte: Optional[str] = None,
    entidade_pais: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Lançar uma fatura de compra (FC) de um fornecedor.

    Regista no sistema uma fatura recebida de um fornecedor.

    Parâmetros obrigatórios:
    - entidade_codigo: código numérico do fornecedor
    - posto: posto/caixa (ex: 1)
    - linhas: artigos comprados (ver criar_fatura para estrutura)

    Exemplo:
        criar_fatura_compra(
            entidade_codigo=10,
            posto=1,
            serie="2026",
            referencia="Fatura fornecedor nº 4521",
            linhas=[
                {"artigo": "MAT-001", "descricao": "Matéria Prima X",
                 "quantidade": 100, "preco": 2.50, "cod_iva": 23},
            ],
        )
    """
    payload = _build_payload(
        codigo, entidade_codigo, posto, moeda,
        serie=serie, data_doc=data_doc, data_venc=data_venc,
        prazo_pagamento=prazo_pagamento, iva_inc=iva_inc,
        observacao=observacao, referencia=referencia, descritivo=descritivo,
        linhas=linhas, formas_pag=formas_pag,
        entidade_descricao=entidade_descricao, entidade_morada=entidade_morada,
        entidade_codpostal=entidade_codpostal,
        entidade_contribuinte=entidade_contribuinte,
        entidade_pais=entidade_pais, extras=extras,
    )
    return await _gravar_documento(payload)


@mcp.tool()
async def gravar_recibo(
    codigo: str,
    entidade: int,
    posto: int,
    moeda: str = "EUR",
    serie: Optional[str] = None,
    data_doc: Optional[str] = None,
    observacao: Optional[str] = None,
    valor_por_conta: Optional[float] = None,
    processamento: Optional[int] = None,
    linhas: Optional[list[dict[str, Any]]] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar um recibo (pagamento) no gGest.

    Um recibo liquida um ou mais documentos pendentes de um cliente.

    ╔══ WORKFLOW RECOMENDADO (3 passos) ══╗
    ║ 1. get_pendentes_recibo(cliente=X, moeda="EUR")                   ║
    ║    → obtém lista de docs pendentes com: codigo, numero, serie,   ║
    ║      ano, total_documento, total_liquidado                       ║
    ║ 2. Escolher quais documentos liquidar e calcular valores         ║
    ║ 3. gravar_recibo() com as linhas e formas_pag correspondentes   ║
    ╚════════════════════════════════════════════════════════════════╝

    Parâmetros obrigatórios:
    - codigo: código do tipo de recibo — depende da configuração da BD.
      Usar lookup_entity("documentos") para ver tipos disponíveis.
      Exemplos comuns: "RC" (Recibo Cliente), "RCLI" (Recibo)
    - entidade: código numérico do cliente
    - posto: código do posto/caixa (ex: 1)
    - moeda: código da moeda (default: "EUR")

    Parâmetros opcionais:
    - serie: código da série documental (ex: "2026")
    - data_doc: data do recibo (formato "YYYY-MM-DD")
    - observacao: texto livre
    - valor_por_conta: valor parcial por conta (quando não se liquida a totalidade)
    - processamento: tipo de processamento (int)

    Linhas — documentos a liquidar (lista de dicts):
    - linhas: cada linha identifica um documento pendente (usar dados de
      get_pendentes_recibo):
        - codigo: código do tipo de documento original (ex: "FT")
        - numero: número do documento (int)
        - serie: série do documento (str)
        - ano: ano do documento (int)
        - valor_liquidar: montante a liquidar deste documento (float)
        - valor_desconto: desconto financeiro aplicado (float, opcional)

    Formas de pagamento (lista de dicts):
    - formas_pag: cada forma deve ter:
        - forma_pag: código do tipo de pagamento
          (usar lookup_entity("tipos_pagamento") para ver códigos válidos;
           exemplos: "NUM" = numerário, "TRFB" = transferência,
           "MB" = multibanco, "CC" = cartão crédito)
        - valor: montante pago nessa forma (float)
      ⚠ O campo chama-se "forma_pag" (NÃO "tipo") — a API ignora "tipo".
      A soma dos valores deve igualar a soma dos valor_liquidar.

    - extras: dict com campos avançados não listados acima

    Retorna (JSON):
        {"doc_codigo": "RC", "doc_numero": 45, "doc_serie": "2026",
         "doc_ano": 2026, "doc_entidade": 1}
    ou mensagem de sucesso se a API não devolver corpo.

    Exemplo — recibo simples por transferência:
        # Passo 1: obter pendentes
        pendentes = get_pendentes_recibo(cliente=1)
        # Passo 2: escolher a fatura FT nº 100 (valor 150.00€)
        # Passo 3: liquidar
        gravar_recibo(
            codigo="RC",
            entidade=1,
            posto=1,
            serie="2026",
            linhas=[
                {"codigo": "FT", "numero": 100, "serie": "2026", "ano": 2026,
                 "valor_liquidar": 150.00},
            ],
            formas_pag=[
                {"forma_pag": "TRFB", "valor": 150.00},
            ],
        )
    """
    payload: dict[str, Any] = {
        "codigo": codigo,
        "entidade": entidade,
        "moeda": moeda,
        "posto": posto,
    }
    if serie is not None:
        payload["serie"] = serie
    if data_doc is not None:
        payload["data_doc"] = data_doc
    if observacao is not None:
        payload["observacao"] = observacao
    if valor_por_conta is not None:
        payload["valor_por_conta"] = valor_por_conta
    if processamento is not None:
        payload["processamento"] = processamento
    if linhas is not None:
        payload["linhas"] = linhas
    if formas_pag is not None:
        payload["formas_pag"] = formas_pag
    if extras:
        payload.update(extras)

    data = await client.post_old("/gravarRecibo", json=payload)
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Recibo gravado com sucesso."
    )
