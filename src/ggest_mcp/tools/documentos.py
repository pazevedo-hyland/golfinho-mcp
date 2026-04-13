"""Documentos tools — gravar documentos comerciais e recibos."""

from __future__ import annotations

import json
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def gravar_documento(
    codigo: str,
    entidade_codigo: int,
    posto: int,
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
    linhas: Optional[list[dict[str, Any]]] = None,
    formas_pag: Optional[list[dict[str, Any]]] = None,
    matricula: Optional[str] = None,
    data_carga: Optional[str] = None,
    morada_carga: Optional[str] = None,
    data_descarga: Optional[str] = None,
    morada_descarga: Optional[str] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar/gravar um documento comercial no gGest.

    Esta é uma tool universal para todos os tipos de documentos:
    faturas, notas de crédito, orçamentos, faturas pro forma,
    guias de transporte, faturas de compra, etc. O tipo é determinado
    pelo parâmetro 'codigo' (código do tipo de documento).

    Parâmetros obrigatórios:
    - codigo: código do tipo de documento. Exemplos comuns:
        "FT" = Fatura
        "FS" = Fatura Simplificada
        "NC" = Nota de Crédito
        "OR" = Orçamento
        "FP" = Fatura Pro Forma
        "GT" = Guia de Transporte
        "FC" = Fatura de Compra
      (usar lookup_entity("documentos") para ver todos os tipos disponíveis)
    - entidade_codigo: código numérico do cliente/fornecedor
    - posto: código do posto/caixa (ex: 1)
    - moeda: código da moeda (default: "EUR")

    Parâmetros opcionais:
    - serie: código da série documental (ex: "2026")
    - data_doc: data do documento (formato "YYYY-MM-DD")
    - data_venc: data de vencimento (formato "YYYY-MM-DD")
    - prazo_pagamento: código do prazo de pagamento
    - vendedor: código do vendedor
    - iva_inc: true se os preços já incluem IVA
    - observacao: texto livre de observações
    - referencia: referência externa (ex: nº encomenda do cliente)
    - descritivo: descritivo/nota no cabeçalho

    Linhas do documento (lista de dicts):
    - linhas: cada linha deve ter pelo menos:
        - artigo: código do artigo
        - quantidade: quantidade
        - preco: preço unitário
      Opcionais por linha:
        - cod_iva: código da taxa IVA (se diferente do default do artigo)
        - armazem: código do armazém
        - desc_lin_per1..5: descontos percentuais por linha (1 a 5)
        - movstock: se movimenta stock (bool)

    Formas de pagamento (lista de dicts):
    - formas_pag: cada forma deve ter:
        - tipo: código do tipo de pagamento (ex: "NU" = numerário)
        - valor: montante pago nessa forma

    Campos de transporte (para guias GT):
    - matricula: matrícula do veículo
    - data_carga / morada_carga: data e local de carga
    - data_descarga / morada_descarga: data e local de descarga

    - extras: dict com campos avançados não listados acima

    Exemplo — fatura simples:
        gravar_documento(
            codigo="FT",
            entidade_codigo=1,
            posto=1,
            linhas=[
                {"artigo": "CAFE-001", "quantidade": 10, "preco": 1.20},
                {"artigo": "BOLO-002", "quantidade": 5, "preco": 2.50},
            ],
        )

    Exemplo — orçamento com desconto e prazo:
        gravar_documento(
            codigo="OR",
            entidade_codigo=42,
            posto=1,
            prazo_pagamento="PP01",
            vendedor=3,
            observacao="Válido por 30 dias",
            linhas=[
                {"artigo": "SERV-010", "quantidade": 1, "preco": 500.00,
                 "desc_lin_per1": 10},
            ],
        )

    Exemplo — guia de transporte:
        gravar_documento(
            codigo="GT",
            entidade_codigo=5,
            posto=1,
            matricula="AA-00-BB",
            data_carga="2026-04-15",
            morada_carga="Rua do Armazém, 1, Lisboa",
            data_descarga="2026-04-15",
            morada_descarga="Av. do Cliente, 20, Porto",
            linhas=[
                {"artigo": "PROD-100", "quantidade": 50, "preco": 10.00},
            ],
        )
    """
    payload: dict[str, Any] = {
        "codigo": codigo,
        "entidade_codigo": entidade_codigo,
        "moeda": moeda,
        "posto": posto,
    }
    if serie is not None:
        payload["serie"] = serie
    if data_doc is not None:
        payload["data_doc"] = data_doc
    if data_venc is not None:
        payload["data_venc"] = data_venc
    if prazo_pagamento is not None:
        payload["prazo_pagamento"] = prazo_pagamento
    if vendedor is not None:
        payload["vendedor"] = vendedor
    if iva_inc is not None:
        payload["iva_inc"] = iva_inc
    if observacao is not None:
        payload["observacao"] = observacao
    if referencia is not None:
        payload["referencia"] = referencia
    if descritivo is not None:
        payload["descritivo"] = descritivo
    if linhas is not None:
        # Auto-fill data_mov on lines if missing (API requires it)
        from datetime import datetime
        default_dt = data_doc or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for linha in linhas:
            if "data_mov" not in linha:
                linha["data_mov"] = default_dt
        payload["linhas"] = linhas
    if formas_pag is not None:
        payload["formas_pag"] = formas_pag

    # Transport fields (guias de transporte)
    if matricula is not None:
        payload["matricula"] = matricula
    if data_carga is not None:
        payload["data_carga"] = data_carga
    if morada_carga is not None:
        payload["morada_carga"] = morada_carga
    if data_descarga is not None:
        payload["data_descarga"] = data_descarga
    if morada_descarga is not None:
        payload["morada_descarga"] = morada_descarga

    if extras:
        payload.update(extras)

    data = await client.post_old("/gravarDocumento", json=payload)
    return json.dumps(data, ensure_ascii=False, default=str) if data else "Documento gravado com sucesso."


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
    Workflow típico:
    1. Chamar get_pendentes_recibo(cliente, moeda) para obter os documentos em aberto
    2. Chamar gravar_recibo() com as linhas dos documentos a liquidar

    Parâmetros obrigatórios:
    - codigo: código do tipo de recibo (ex: "RC" — usar lookup_entity("documentos")
      para ver tipos disponíveis)
    - entidade: código numérico do cliente
    - posto: código do posto/caixa (ex: 1)
    - moeda: código da moeda (default: "EUR")

    Parâmetros opcionais:
    - serie: código da série documental
    - data_doc: data do recibo (formato "YYYY-MM-DD")
    - observacao: texto livre
    - valor_por_conta: valor parcial por conta (quando não se liquida a totalidade)
    - processamento: tipo de processamento (int)

    Linhas — documentos a liquidar (lista de dicts):
    - linhas: cada linha identifica um documento pendente:
        - codigo: código do tipo de documento original (ex: "FT")
        - numero: número do documento
        - serie: série do documento
        - ano: ano do documento
        - valor_liquidar: montante a liquidar deste documento
        - valor_desconto: desconto financeiro aplicado (opcional)

    Formas de pagamento (lista de dicts):
    - formas_pag: cada forma deve ter:
        - tipo: código do tipo de pagamento (ex: "NU" = numerário, "TB" = transferência)
        - valor: montante pago nessa forma

    - extras: dict com campos avançados não listados acima

    Exemplo — recibo simples por transferência:
        # Primeiro: obter pendentes
        pendentes = get_pendentes_recibo(cliente=1)
        # Depois: liquidar a fatura FT nº 100
        gravar_recibo(
            codigo="RC",
            entidade=1,
            posto=1,
            linhas=[
                {"codigo": "FT", "numero": 100, "serie": "2026", "ano": 2026,
                 "valor_liquidar": 150.00},
            ],
            formas_pag=[
                {"tipo": "TB", "valor": 150.00},
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
    return json.dumps(data, ensure_ascii=False, default=str) if data else "Recibo gravado com sucesso."
