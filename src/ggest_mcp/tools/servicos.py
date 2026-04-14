"""Serviços tools — assistência técnica (pedidos, intervenções, ordens de serviço)."""

from __future__ import annotations

import json
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def assistencia_tecnica(
    operacao: str,
    codigo: str,
    posto: int,
    # — Entidade (campo varia conforme o endpoint) —
    entidade: Optional[int] = None,
    entidade_codigo: Optional[int] = None,
    # — Identificação do pedido (para intervenção) —
    numero: Optional[int] = None,
    serie: Optional[str] = None,
    ano: Optional[int] = None,
    # — Pedido de assistência —
    artigo: Optional[str] = None,
    contrato: Optional[str] = None,
    equipamento: Optional[str] = None,
    tipo_equipamento: Optional[str] = None,
    marca: Optional[str] = None,
    modelo: Optional[str] = None,
    numero_serie: Optional[str] = None,
    tecnico: Optional[int] = None,
    urgente: Optional[bool] = None,
    avaria_descrita: Optional[str] = None,
    pedido_via: Optional[int] = None,
    # — Intervenção —
    descricao: Optional[str] = None,
    estado: Optional[int] = None,
    avaria_encontrada: Optional[str] = None,
    reparacao_efetuada: Optional[str] = None,
    horas_gastas: Optional[float] = None,
    kms_percorridos: Optional[float] = None,
    observacao: Optional[str] = None,
    # — Ordem de serviço —
    moeda: Optional[str] = None,
    linhas: Optional[list[dict[str, Any]]] = None,
    # — Catch-all —
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Gestão de assistência técnica no gGest — pedidos, intervenções e ordens de serviço.

    Uma tool multiplexada com 3 operações (parâmetro 'operacao').
    Todas as operações retornam (JSON):
        {"doc_codigo": "PA", "doc_numero": 7, "doc_serie": "2026",
         "doc_ano": 2026, "doc_entidade": 42}
    ou mensagem de sucesso se a API não devolver corpo.

    ━━━ operacao="pedido" ━━━
    Criar um pedido de assistência técnica.

    Parâmetros obrigatórios:
    - codigo: código do tipo de pedido (usar lookup_entity("documentos")
      para ver tipos disponíveis)
    - entidade: código do cliente
    - posto: código do posto

    Parâmetros opcionais:
    - artigo, equipamento, tipo_equipamento: identificação do equipamento
    - marca, modelo, numero_serie: detalhes do equipamento
    - contrato: código do contrato de manutenção
    - tecnico: código do técnico atribuído
    - urgente: true se é urgente
    - avaria_descrita: descrição da avaria reportada pelo cliente
    - pedido_via: como o pedido chegou (1=telefone, 2=email, 3=presencial)

    Exemplo:
        assistencia_tecnica(
            operacao="pedido",
            codigo="PA",
            entidade=42,
            posto=1,
            equipamento="IMP-001",
            marca="HP",
            modelo="LaserJet Pro",
            numero_serie="SN12345",
            avaria_descrita="Impressora não liga após pico de corrente",
            urgente=True,
            pedido_via=1,
        )

    ━━━ operacao="intervencao" ━━━
    Adicionar uma intervenção a um pedido de assistência existente.

    Parâmetros obrigatórios:
    - codigo: código do tipo de pedido (mesmo tipo do pedido original)
    - numero: número do pedido existente (int)
    - serie: série do pedido (str)
    - ano: ano do pedido (int)
    - posto: código do posto

    Parâmetros opcionais:
    - descricao: resumo da intervenção
    - tecnico: código do técnico que interveio
    - estado: novo estado do pedido (código numérico)
    - avaria_encontrada: diagnóstico real
    - reparacao_efetuada: trabalho realizado
    - horas_gastas: horas de trabalho (float)
    - kms_percorridos: quilómetros deslocação (float)
    - observacao: notas adicionais

    Exemplo:
        assistencia_tecnica(
            operacao="intervencao",
            codigo="PA",
            numero=15,
            serie="2026",
            ano=2026,
            posto=1,
            tecnico=3,
            avaria_encontrada="Fonte de alimentação queimada",
            reparacao_efetuada="Substituída fonte de alimentação",
            horas_gastas=1.5,
            kms_percorridos=30,
        )

    ━━━ operacao="ordem_servico" ━━━
    Criar uma ordem de serviço (documento faturável a partir da assistência).

    Parâmetros obrigatórios:
    - codigo: código do tipo de ordem (usar lookup_entity("documentos"))
    - entidade_codigo: código do cliente
    - moeda: código da moeda (ex: "EUR")
    - posto: código do posto

    Parâmetros opcionais:
    - linhas: lista de artigos/serviços (estrutura igual a criar_fatura).
      Cada linha: {"artigo": "...", "descricao": "...", "quantidade": N,
                   "preco": X.XX}
      Nota: data_mov é preenchido automaticamente — não é preciso enviar.

    Exemplo:
        assistencia_tecnica(
            operacao="ordem_servico",
            codigo="OS",
            entidade_codigo=42,
            moeda="EUR",
            posto=1,
            linhas=[
                {"artigo": "MO-001", "descricao": "Mão de obra (hora)",
                 "quantidade": 1.5, "preco": 35.00},
                {"artigo": "FONTE-HP", "descricao": "Fonte de alimentação HP",
                 "quantidade": 1, "preco": 45.00},
            ],
        )
    """
    operacao = operacao.lower().strip()

    if operacao == "pedido":
        if entidade is None:
            return "Erro: parâmetro 'entidade' é obrigatório para operação 'pedido'."
        payload: dict[str, Any] = {
            "codigo": codigo,
            "entidade": entidade,
            "posto": posto,
        }
        for key, val in [
            ("artigo", artigo),
            ("contrato", contrato),
            ("equipamento", equipamento),
            ("tipo_equipamento", tipo_equipamento),
            ("marca", marca),
            ("modelo", modelo),
            ("numero_serie", numero_serie),
            ("tecnico", tecnico),
            ("urgente", urgente),
            ("avaria_descrita", avaria_descrita),
            ("pedido_via", pedido_via),
        ]:
            if val is not None:
                payload[key] = val
        if extras:
            payload.update(extras)

        data = await client.post_old("/assistecPedidoAssistenciaNovo", json=payload)
        return (
            json.dumps(data, ensure_ascii=False, default=str)
            if data
            else "Pedido de assistência criado com sucesso."
        )

    if operacao == "intervencao":
        if numero is None or serie is None or ano is None:
            return "Erro: parâmetros 'numero', 'serie' e 'ano' são obrigatórios para operação 'intervencao'."
        intervencao: dict[str, Any] = {}
        for key, val in [
            ("descricao", descricao),
            ("tecnico", tecnico),
            ("estado", estado),
            ("avaria_encontrada", avaria_encontrada),
            ("reparacao_efetuada", reparacao_efetuada),
            ("horas_gastas", horas_gastas),
            ("kms_percorridos", kms_percorridos),
            ("observacao", observacao),
        ]:
            if val is not None:
                intervencao[key] = val

        payload = {
            "codigo": codigo,
            "numero": numero,
            "serie": serie,
            "ano": ano,
            "posto": posto,
            "intervencao": intervencao,
        }
        if extras:
            payload.update(extras)

        data = await client.post_old(
            "/assistecPedidoAssistenciaIntervencaoNova", json=payload
        )
        return (
            json.dumps(data, ensure_ascii=False, default=str)
            if data
            else "Intervenção adicionada com sucesso."
        )

    if operacao == "ordem_servico":
        if entidade_codigo is None:
            return "Erro: parâmetro 'entidade_codigo' é obrigatório para operação 'ordem_servico'."
        payload = {
            "codigo": codigo,
            "entidade_codigo": entidade_codigo,
            "moeda": moeda or "EUR",
            "posto": posto,
        }
        if linhas is not None:
            # Auto-fill data_mov on lines if missing (API requires it)
            from datetime import datetime

            default_dt = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            for linha in linhas:
                if "data_mov" not in linha:
                    linha["data_mov"] = default_dt
            payload["linhas"] = linhas
        if extras:
            payload.update(extras)

        data = await client.post_old("/assistecOrdemServicoNova", json=payload)
        return (
            json.dumps(data, ensure_ascii=False, default=str)
            if data
            else "Ordem de serviço criada com sucesso."
        )

    tipos_validos = "pedido, intervencao, ordem_servico"
    return f"Operação '{operacao}' inválida. Operações válidas: {tipos_validos}"
