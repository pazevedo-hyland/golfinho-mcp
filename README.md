# gGest MCP Server

MCP server para o ERP gGest — acesso seguro (read-heavy) à API REST do gGest via Claude ou qualquer cliente MCP.

## Funcionalidades

**16 tools** (14 read-only + 2 update):

| Tool | Descrição |
|------|-----------|
| `list_artigos` | Pesquisar artigos por nome, código ou código de barras |
| `get_artigo` | Ficha completa de um artigo |
| `update_artigo` | Atualizar preço, descrição, flags de um artigo |
| `list_clientes` | Pesquisar clientes por nome, NIF, telefone |
| `get_cliente` | Ficha completa de um cliente |
| `update_cliente` | Atualizar morada, contactos, condições de um cliente |
| `lookup_entity` | Consultar qualquer entidade de referência (22 tipos: armazéns, vendedores, zonas, marcas, moedas, países, séries, etc.) |
| `list_ivas` | Consultar taxas de IVA, isenções e regimes |
| `mapa_vendas_gerais` | Relatório de vendas gerais por período |
| `mapa_extrato_clientes` | Extrato de conta corrente de clientes |
| `mapa_idade_saldos` | Aging report — saldos por antiguidade |
| `mapa_top_artigos` | Top artigos mais vendidos |
| `mapa_vendas_artigos` | Vendas por grupo de artigo ou resumo |
| `mapa_volume_vendas` | Volume de vendas por data/mês/vendedor/posto/estabelecimento |
| `ler_data_hora` | Data e hora do sistema |
| `get_pendentes_recibo` | Documentos pendentes de pagamento de um cliente |

**Segurança**: zero deletes, zero criação de documentos fiscais, zero operações de caixa.

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

**Sistema**
- "Qual a data e hora atual do sistema gGest?"
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
└── tools/
    ├── artigos.py     # list, get, update artigos
    ├── clientes.py    # list, get, update clientes
    ├── lookup.py      # lookup genérico para 22+ entidades
    ├── iva.py         # taxas, isenções, regimes IVA
    ├── mapas.py       # 6 relatórios de vendas
    └── sistema.py     # data/hora, pendentes recibo
```

### Fluxo de autenticação

1. **Startup**: POST `/api/v1/auth/login` → tokens guardados em memória
2. **Config BD**: PUT `/api/configurarAcessoBD` (endpoint antigo)
3. **Cada request**: Bearer token injetado automaticamente
4. **Se 401**: refresh automático + retry

### Routing API

- **API nova (`/api/v1/`)**: CRUD artigos, clientes, entidades de referência, IVA
- **API antiga (`/api/`)**: relatórios/mapas, pendentes, data/hora, config BD
