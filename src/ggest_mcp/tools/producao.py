"""Produção tools — criação de folhas de produção."""

from __future__ import annotations

import json
from typing import Any, Optional

from ggest_mcp.http_client import client
from ggest_mcp.app import mcp


@mcp.tool()
async def criar_producao(
    codigo: str,
    numero: int,
    serie: str,
    ano: int,
    entidade_codigo: int,
    posto: int,
    data: Optional[str] = None,
    descritivo: Optional[str] = None,
    observacao: Optional[str] = None,
    moeda: Optional[str] = None,
    estado_producao: Optional[int] = None,
    composto: Optional[dict[str, Any]] = None,
    componentes: Optional[list[dict[str, Any]]] = None,
    extras: Optional[dict[str, Any]] = None,
) -> str:
    """Criar uma folha de produção no gGest.

    Uma folha de produção regista a transformação de componentes (matérias-primas)
    num produto composto (produto acabado). Ideal para manufatura, cozinha, montagem, etc.

    Parâmetros obrigatórios:
    - codigo: código do tipo de documento de produção
    - numero: número da folha de produção
    - serie: série documental (ex: "2026")
    - ano: ano da produção (ex: 2026)
    - entidade_codigo: código do cliente/entidade associada
    - posto: código do posto/caixa

    Parâmetros opcionais:
    - data: data da produção (formato "YYYY-MM-DD")
    - descritivo: descrição da produção
    - observacao: notas adicionais
    - moeda: código da moeda (default: "EUR")
    - estado_producao: estado inicial (código numérico)

    Linhas — produto composto (o que se produz):
    - composto: dict com os dados do produto acabado:
        - artigo: código do artigo produzido
        - quantidade: quantidade produzida
        - preco: custo unitário estimado
        - armazem: armazém de destino
        Opcionais: lote, tamanho, cor

    Linhas — componentes (matérias-primas consumidas):
    - componentes: lista de dicts, cada um com:
        - artigo: código da matéria-prima
        - quantidade: quantidade consumida
        - preco: custo unitário
        - armazem: armazém de origem
        Opcionais: lote, tamanho, cor

    - extras: dict com campos avançados não listados acima

    Exemplo — produção de bolos:
        criar_producao(
            codigo="PR",
            numero=1,
            serie="2026",
            ano=2026,
            entidade_codigo=1,
            posto=1,
            data="2026-04-15",
            descritivo="Produção semanal de bolos",
            composto={"artigo": "BOLO-CHOC", "quantidade": 50, "preco": 3.50,
                     "armazem": "PA"},
            componentes=[
                {"artigo": "FARINHA", "quantidade": 25, "preco": 0.80,
                 "armazem": "MP"},
                {"artigo": "CHOCOLATE", "quantidade": 10, "preco": 2.50,
                 "armazem": "MP"},
                {"artigo": "OVOS", "quantidade": 100, "preco": 0.15,
                 "armazem": "MP"},
            ],
        )
    """
    payload: dict[str, Any] = {
        "codigo": codigo,
        "numero": numero,
        "serie": serie,
        "ano": ano,
        "entidade_codigo": entidade_codigo,
        "posto": posto,
    }
    if data is not None:
        payload["data"] = data
    if descritivo is not None:
        payload["descritivo"] = descritivo
    if observacao is not None:
        payload["observacao"] = observacao
    if moeda is not None:
        payload["moeda"] = moeda
    if estado_producao is not None:
        payload["estado_producao"] = estado_producao
    if composto is not None:
        payload["composto"] = composto
    if componentes is not None:
        payload["componentes"] = componentes
    if extras:
        payload.update(extras)

    data_resp = await client.post_old("/producaoNova", json=payload)
    return json.dumps(data_resp, ensure_ascii=False, default=str) if data_resp else "Folha de produção criada com sucesso."
