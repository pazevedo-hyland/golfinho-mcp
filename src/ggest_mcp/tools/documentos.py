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

    ╔══ WORKFLOW RECOMENDADO (antes de chamar esta tool) ══╗
    ║ 1. lookup_entity("documentos") → tipos de doc válidos (FT, OR, GT…)  ║
    ║ 2. lookup_entity("series")     → séries disponíveis (ex: "2026")     ║
    ║ 3. list_ivas(tipo="taxas")     → códigos de IVA (campo cod_iva)      ║
    ║ 4. lookup_entity("tipos_pagamento") → formas de pagamento (NUM, TB…) ║
    ║ 5. get_artigo(codigo)          → confirmar código e preço do artigo  ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Parâmetros obrigatórios:
    - codigo: código do tipo de documento. Exemplos comuns:
        "FT" = Fatura  (pode exigir dados de transporte em certas séries)
        "FR" = Fatura-Recibo  (fatura + pagamento imediato — mais simples)
        "FS" = Fatura Simplificada  (exige NIF válido no cliente)
        "NC" = Nota de Crédito
        "OR" = Orçamento
        "FP" = Fatura Pro Forma
        "GT" = Guia de Transporte  (requer matricula + moradas)
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
        - artigo: código do artigo (str)
        - quantidade: quantidade (float)
        - preco: preço unitário (float)
        - descricao: descrição da linha (str, mínimo 2 caracteres — obrigatório)
      Opcionais por linha:
        - cod_iva: código da taxa IVA (int — se omitido usa o default do artigo;
          obter códigos válidos com list_ivas())
        - armazem: código do armazém
        - desc_lin_per1..5: descontos percentuais por linha (1 a 5)
        - movstock: se movimenta stock (bool)
      Nota: data_mov é preenchido automaticamente — não é preciso enviar.

    Formas de pagamento (lista de dicts) — obrigatório para vendas a pronto:
    - formas_pag: cada forma deve ter:
        - tipo: código do tipo de pagamento
          (usar lookup_entity("tipos_pagamento") para ver códigos válidos;
           exemplos comuns: "NUM" = numerário, "TRFB" = transferência,
           "MB" = multibanco, "CC" = cartão crédito)
        - valor: montante pago nessa forma (float)
      Se omitido, o documento fica a crédito (conta corrente).

    Campos de transporte (para guias GT):
    - matricula: matrícula do veículo
    - data_carga / morada_carga: data e local de carga
    - data_descarga / morada_descarga: data e local de descarga

    - extras: dict com campos avançados não listados acima

    Retorna (JSON):
        {"doc_codigo": "FT", "doc_numero": 123, "doc_serie": "2026",
         "doc_ano": 2026, "doc_entidade": 1}
    ou mensagem de sucesso se a API não devolver corpo.

    ⚠ Notas importantes:
    - O campo 'descricao' em cada linha é frequentemente obrigatório (mín. 2
      caracteres) — a API rejeita sem ele.
    - Fatura Simplificada (FS) exige NIF válido configurado no cliente.
    - Fatura (FT) pode exigir dados de transporte conforme a série — se só
      precisa de uma venda simples, prefira FR (Fatura-Recibo).
    - Mensagens de erro da API podem aparecer em francês (backend WinDev).

    Exemplo — fatura a crédito:
        gravar_documento(
            codigo="FT",
            entidade_codigo=1,
            posto=1,
            linhas=[
                {"artigo": "CAFE-001", "descricao": "Café Expresso",
                 "quantidade": 10, "preco": 1.20},
                {"artigo": "BOLO-002", "descricao": "Bolo de Chocolate",
                 "quantidade": 5, "preco": 2.50},
            ],
        )

    Exemplo — fatura a pronto (com pagamento imediato em numerário):
        gravar_documento(
            codigo="FR",
            entidade_codigo=1,
            posto=1,
            serie="2026",
            linhas=[
                {"artigo": "CAFE-001", "descricao": "Café Expresso",
                 "quantidade": 10, "preco": 1.20, "cod_iva": 23},
            ],
            formas_pag=[
                {"tipo": "NUM", "valor": 14.76},
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
                {"artigo": "SERV-010", "descricao": "Consultoria IT",
                 "quantidade": 1, "preco": 500.00, "desc_lin_per1": 10},
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
                {"artigo": "PROD-100", "descricao": "Widget Industrial",
                 "quantidade": 50, "preco": 10.00},
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
    return (
        json.dumps(data, ensure_ascii=False, default=str)
        if data
        else "Documento gravado com sucesso."
    )


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
        - tipo: código do tipo de pagamento
          (usar lookup_entity("tipos_pagamento") para ver códigos válidos;
           exemplos: "NUM" = numerário, "TRFB" = transferência,
           "MB" = multibanco, "CC" = cartão crédito)
        - valor: montante pago nessa forma (float)
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
                {"tipo": "TRFB", "valor": 150.00},
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
