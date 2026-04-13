# gGest MCP Server

MCP server para o ERP gGest — acesso seguro à API REST do gGest via Claude ou qualquer cliente MCP.

## Funcionalidades

**27 tools** — 19 read-only, 6 analytics (read-only) e 8 write:

> **Legenda**: 🟢 read-only (sempre ativa) · 🔵 analytics/read-only · 🟠 write (requer `GGEST_READONLY=false`)

### Artigos / Produtos
| Tool | Tipo | Descrição |
|------|------|-----------|
| `list_artigos` | 🟢 read | Pesquisar artigos por nome, código ou código de barras |
| `get_artigo` | 🟢 read | Ficha completa de um artigo |
| `update_artigo` | 🟠 write | Atualizar preço, descrição, flags de um artigo |
| `create_artigo` | 🟠 write | Criar um novo artigo/produto |

### Clientes
| Tool | Tipo | Descrição |
|------|------|-----------|
| `list_clientes` | 🟢 read | Pesquisar clientes por nome, NIF, telefone |
| `get_cliente` | 🟢 read | Ficha completa de um cliente |
| `update_cliente` | 🟠 write | Atualizar morada, contactos, condições de um cliente |
| `create_cliente` | 🟠 write | Criar um novo cliente |

### Entidades de Referência & IVA
| Tool | Tipo | Descrição |
|------|------|-----------|
| `lookup_entity` | 🟢 read | Consultar qualquer entidade de referência (24 tipos: armazéns, vendedores, zonas, marcas, moedas, países, séries, etc.) |
| `list_ivas` | 🟢 read | Consultar taxas de IVA, isenções e regimes |

### Relatórios / Mapas
| Tool | Tipo | Descrição |
|------|------|-----------|
| `mapa_vendas_gerais` | 🟢 read | Relatório de vendas gerais por período |
| `mapa_extrato_clientes` | 🟢 read | Extrato de conta corrente de clientes |
| `mapa_idade_saldos` | 🟢 read | Aging report — saldos por antiguidade |
| `mapa_top_artigos` | 🟢 read | Top artigos mais vendidos |
| `mapa_vendas_artigos` | 🟢 read | Vendas por grupo de artigo ou resumo |
| `mapa_volume_vendas` | 🟢 read | Volume de vendas por data/mês/vendedor/posto/estabelecimento |

### Analytics (compostas — agregam múltiplos endpoints)
| Tool | Tipo | Descrição |
|------|------|-----------|
| `top_clientes_revenue` | 🔵 analytics | Ranking de clientes por faturação num período |
| `analise_cliente` | 🔵 analytics | Perfil completo de um cliente (vendas, artigos, pendentes) |
| `resumo_financeiro` | 🔵 analytics | Dashboard financeiro anual (receita mensal, YoY, top artigos/clientes, aging) |
| `analise_rentabilidade` | 🔵 analytics | Análise de rentabilidade por artigo com margens |
| `analise_cobranca` | 🔵 analytics | Análise de risco de cobrança (clientes com saldos vencidos) |
| `comparacao_periodos` | 🔵 analytics | Comparar dois períodos quaisquer (receita, docs, ticket médio, top artigos) |

### Documentos Comerciais
| Tool | Tipo | Descrição |
|------|------|-----------|
| `gravar_documento` | 🟠 write | Criar qualquer documento comercial: faturas, notas de crédito, orçamentos, pro formas, guias de transporte, faturas de compra |
| `gravar_recibo` | 🟠 write | Criar recibos (pagamentos) — liquida documentos pendentes |

### Assistência Técnica & Produção
| Tool | Tipo | Descrição |
|------|------|-----------|
| `assistencia_tecnica` | 🟠 write | Gestão de assistência técnica: pedidos, intervenções e ordens de serviço (3 operações numa tool) |
| `criar_producao` | 🟠 write | Criar folhas de produção (composto + componentes) |

### Sistema
| Tool | Tipo | Descrição |
|------|------|-----------|
| `get_pendentes_recibo` | 🟢 read | Documentos pendentes de pagamento de um cliente |

**Segurança**: sem deletes, todas as 8 tools de escrita (🟠) desativadas por defeito (`GGEST_READONLY=true`). Mudar para `false` para as ativar.

## Cobertura de Casos de Uso

Mapeamento entre as necessidades reais dos utilizadores e as tools disponíveis:

| Necessidade | Estado | Como fazer |
|---|---|---|
| **Gestão de dados** | | |
| Criar artigos | ✅ | `create_artigo` |
| Criar clientes | ✅ | `create_cliente` |
| Criar fornecedores | ❌ | API sem endpoint (ver [Lacuna #1](#1-fornecedores--credores)) |
| Criar credores | ❌ | API sem endpoint (ver [Lacuna #1](#1-fornecedores--credores)) |
| **Faturação e recibos** | | |
| Faturas de venda a pronto | ✅ | `gravar_documento(codigo="FT", ...)` + `formas_pag` |
| Faturas de venda a crédito | ✅ | `gravar_documento(codigo="FT", ...)` sem formas_pag |
| Recibos | ✅ | `get_pendentes_recibo` → `gravar_recibo` |
| Criar avenças | ❌ | API sem endpoint (ver [Lacuna #2](#2-avenças-faturas-recorrentes)) |
| Faturar avenças | ❌ | Idem |
| **Compras e despesas** | | |
| Lançar fatura de compra | ✅ | `gravar_documento(codigo="FC", ...)` |
| Lançar despesas | ⚠️ | Depende do tipo de documento — verificar com `lookup_entity("documentos")` |
| **Produção e serviços** | | |
| Folhas de produção | ✅ | `criar_producao` |
| Assistências técnicas | ✅ | `assistencia_tecnica` (pedido + intervenção + ordem de serviço) |
| Empréstimos técnicos | ❌ | API sem endpoint (ver [Lacuna #3](#3-empréstimos-de-equipamento)) |
| **Logística** | | |
| Guias de transporte | ✅ | `gravar_documento(codigo="GT", matricula=..., ...)` |
| **Documentos comerciais** | | |
| Orçamentos | ✅ | `gravar_documento(codigo="OR", ...)` |
| Faturas pro forma | ✅ | `gravar_documento(codigo="FP", ...)` |
| **Comunicação com clientes** | | |
| Enviar extrato de conta | ❌ | API sem endpoint (ver [Lacuna #4](#4-email--notificações)) |
| Avisos de vencimento | ❌ | Idem |
| Notificar renovação SAG | ❌ | Idem |

> **Resumo**: ✅ 11 cobertos · ⚠️ 1 parcial · ❌ 6 bloqueados por falta de API

## Setup

### 1. Configurar variáveis de ambiente

Copiar `.env.example` para `.env` e preencher:

```bash
cp .env.example .env
```

```env
GGEST_HOST=golfinhosoftware.pcscloud.net
GGEST_USERNAME=o_teu_username
GGEST_PASSWORD=a_tua_password

# Modo read-only (default: true)
# Mudar para false para ativar update_artigo e update_cliente
GGEST_READONLY=true

# Base de dados (opcional — necessário se a BD ainda não estiver configurada)
GGEST_DB_SERVIDOR=servidor
GGEST_DB_PORTA=4900
GGEST_DB_BASE_DADOS=nome_bd
GGEST_DB_UTILIZADOR=user_bd
GGEST_DB_PASSWORD=pass_bd
```

### 2. Correr com Docker

```bash
docker compose up --build -d
```

O server fica acessível em `http://localhost:8000/mcp`.

### 3. Correr localmente (sem Docker)

```bash
pip install -e .
python -m ggest_mcp.server
```

## Exemplos de perguntas

Depois de ligar o MCP server ao teu cliente (VS Code, Claude Desktop, etc.), experimenta:

**Artigos / Produtos**
- "Mostra-me os artigos que contenham 'café' na descrição"
- "Qual o preço e stock do artigo COM-001?"
- "Atualiza o preço1 do artigo COM-001 para 12.50€"
- "Que artigos têm o código de barras 5601234567890?"

**Clientes**
- "Lista os clientes com 'Silva' no nome"
- "Dá-me a ficha completa do cliente 1"
- "Atualiza o email do cliente 1 para novo@email.pt"
- "Que clientes têm o NIF 123456789?"

**Entidades de Referência**
- "Que grupos de artigos existem?"
- "Lista os vendedores disponíveis"
- "Mostra as famílias do grupo G01"
- "Que formas de pagamento existem?"

**IVA**
- "Quais são as taxas de IVA em vigor?"
- "Lista os motivos de isenção de IVA"

**Relatórios / Mapas**
- "Relatório de vendas gerais de janeiro a março de 2026"
- "Extrato de conta corrente do cliente 5 no último trimestre"
- "Mostra o mapa de idade de saldos dos clientes"
- "Quais os 10 artigos mais vendidos em 2026?"
- "Vendas por grupo de artigos de janeiro a março de 2026"
- "Volume de vendas mensal no primeiro semestre de 2026"

**Analytics**
- "Quais os meus 5 melhores clientes por faturação em 2026?"
- "Faz uma análise completa do cliente 42"
- "Resumo financeiro de 2026 com comparação ao ano anterior"
- "Análise de rentabilidade dos artigos do grupo BEBIDAS"
- "Que clientes têm saldos vencidos? Análise de cobrança"
- "Compara o 1º trimestre de 2025 com o 1º trimestre de 2026"

**Documentos Comerciais** (requer `GGEST_READONLY=false`)
- "Cria uma fatura para o cliente 1 com 10 unidades do artigo CAFE-001 a 1.20€"
- "Faz um orçamento para o cliente 42 com os artigos X, Y e Z"
- "Cria uma guia de transporte para o cliente 5 com matrícula AA-00-BB"
- "Emite um recibo para liquidar a fatura 100 do cliente 1"

**Assistência Técnica** (requer `GGEST_READONLY=false`)
- "Abre um pedido de assistência para o cliente 42 — impressora avariada"
- "Adiciona uma intervenção ao pedido 15 — fonte substituída, 1.5h"
- "Cria uma ordem de serviço para faturar a reparação"

**Produção** (requer `GGEST_READONLY=false`)
- "Cria uma folha de produção de 50 bolos com os componentes farinha, chocolate e ovos"

**Sistema**
- "Que documentos tem o cliente 3 pendentes de recibo?"

## Configurar no Claude Desktop

Adicionar ao ficheiro de configuração do Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ggest": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Arquitetura

```
src/ggest_mcp/
├── server.py          # FastMCP + Streamable HTTP + lifespan auth
├── auth.py            # Login automático + refresh + config BD
├── http_client.py     # httpx async (dual base URL, sem métodos delete)
├── config.py          # Env vars via pydantic-settings
├── pagination.py      # Client-side pagination para respostas grandes
└── tools/
    ├── artigos.py     # list, get, create, update artigos
    ├── clientes.py    # list, get, create, update clientes
    ├── lookup.py      # lookup genérico para 24+ entidades
    ├── iva.py         # taxas, isenções, regimes IVA
    ├── mapas.py       # 6 relatórios de vendas
    ├── analytics.py   # 6 tools analytics compostas
    ├── documentos.py  # gravar documentos e recibos
    ├── servicos.py    # assistência técnica (3 operações)
    ├── producao.py    # folhas de produção
    └── sistema.py     # pendentes recibo
```

### Fluxo de autenticação

1. **Startup**: POST `/api/v1/auth/login` → tokens guardados em memória
2. **Config BD**: PUT `/api/configurarAcessoBD` (endpoint antigo)
3. **Cada request**: Bearer token injetado automaticamente
4. **Se 401**: refresh automático + retry

### Routing API

- **API nova (`/api/v1/`)**: CRUD artigos, clientes, entidades de referência, IVA
- **API antiga (`/api/`)**: relatórios/mapas, documentos comerciais, recibos, assistência técnica, produção, pendentes, data/hora, config BD

## Lacunas da API — Endpoints em Falta

As funcionalidades abaixo foram solicitadas por utilizadores do gGest mas **não têm endpoints disponíveis** na API atual. Esta secção serve de referência para o developer do gGest expor estes endpoints.

### 1. Fornecedores & Credores
Atualmente não existe CRUD separado para fornecedores e credores — apenas `/clientes`.
- **Pedido**: `POST/GET/PUT /api/v1/fornecedores`, `POST/GET/PUT /api/v1/credores`
- **Casos de uso**: criar fornecedores, consultar dados de fornecedor, atualizar condições comerciais de compra

### 2. Avenças (Faturas Recorrentes)
Não existem endpoints para gerir contratos de avença nem para gerar automaticamente faturas a partir deles.
- **Pedido**: `POST/GET/PUT /api/v1/avencas`, `POST /api/v1/avencas/{id}/faturar`
- **Casos de uso**: criar avença mensal para cliente, listar avenças ativas, gerar fatura do mês a partir da avença

### 3. Empréstimos de Equipamento
Não existem endpoints para registar empréstimos de material/equipamento e respetivas devoluções.
- **Pedido**: `POST/GET/PUT /api/v1/emprestimos`
- **Casos de uso**: registar empréstimo de equipamento a cliente, consultar empréstimos em aberto, registar devolução

### 4. Email / Notificações
Os campos de email dos clientes existem (`email1-4`, `mail_faturacao_eletronica`) mas não há endpoints para enviar emails ou notificações.
- **Pedido**: `POST /api/enviarExtratoCliente/{cliente}`, `POST /api/enviarAvisoVencimento/{cliente}`, `POST /api/enviarEmail`
- **Casos de uso**: enviar extrato de conta corrente ao cliente, enviar aviso de vencimento/pagamento em atraso, enviar notificação de renovação de contrato SAG

### 5. Consulta de Documentos Emitidos
Não é possível obter os dados de um documento específico (fatura, recibo, etc.) por tipo/número/série/ano. Só existem relatórios agregados (mapas).
- **Pedido**: `GET /api/v1/documentos_emitidos/{tipo}/{serie}/{numero}/{ano}`
- **Casos de uso**: consultar os detalhes e linhas de uma fatura específica, verificar dados de um recibo emitido

### 6. Anulação de Documentos
Não existe endpoint para anular/cancelar documentos via API.
- **Pedido**: `POST /api/anularDocumento` (com campos: tipo, número, série, ano, motivo)
- **Casos de uso**: anular uma fatura emitida por engano, cancelar um orçamento expirado
