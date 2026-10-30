# Retail Analytics: Gestão de Vendas e Estoque

Projeto de análise de dados de varejo construído sobre o banco **RYStore**. O objetivo é montar um pipeline que sai dos arquivos CSV originais, passa pelo Supabase (o OLTP simulado da empresa) e chega a um lakehouse no Databricks, em arquitetura medalhão, com um modelo dimensional pronto para indicadores de vendas, estoque e inteligência de negócio.

> **Fonte dos dados:** [RYStore Retail Dataset](https://github.com/ryanariefe/RYStore-Retail-Dataset)

---

## Sumário

- [Arquitetura do pipeline](#arquitetura-do-pipeline)
- [Modelo de dados](#modelo-de-dados)
- [Análises possíveis](#análises-possíveis)
- [Como executar](#como-executar)
- [Skills](#skills)
- [Estrutura do repositório](#estrutura-do-repositório)

---

## Arquitetura do pipeline

O **Supabase** simula o sistema transacional (OLTP) da empresa e é a origem dos dados. O **Databricks** é a plataforma de dados: lá construímos o lakehouse em arquitetura medalhão, no catálogo `lh_retail_analytics`.

```
┌──────────────┐   ┌───────────────────┐   ┌──────────────────────────── Databricks ─────────────────────────────┐   ┌──────────┐
│ Arquivos CSV │──▶│ Supabase          │──▶│ notebook Python ──▶ bronze ──▶ silver ──▶ gold                      │──▶│ Consumo  │
│ RYStore      │   │ OLTP + Storage S3 │   │ (boto3)            brutos     limpos     modelo dimensional         │   │ (Genie)  │
└──────────────┘   └───────────────────┘   └─────────────────────────────────────────────────────────────────────┘   └──────────┘
```

| Etapa | Onde | Responsabilidade |
|---|---|---|
| **Fonte** | Arquivos CSV | Dados originais do RYStore |
| **Origem (OLTP)** | Supabase | Banco transacional simulado da empresa; arquivos expostos pela API compatível com S3 do Supabase Storage |
| **Ingestão** | Databricks, notebook Python | Lê o Supabase com `boto3`, com as credenciais do `.env` guardadas nos *secrets* do Databricks, e grava no volume `bronze.raw` |
| **Bronze** | `lh_retail_analytics.bronze` | Dados como chegam da origem, sem regra de negócio |
| **Silver** | `lh_retail_analytics.silver` | Dados limpos, tipados e integrados |
| **Gold** | `lh_retail_analytics.gold` | Modelo dimensional pronto para indicadores |
| **Consumo** | Chat Genie One | Consumo e análise dos dados modelados |

---

## Modelo de dados

### Modelo de origem (RYStore)

Relacionamentos entre as tabelas do dataset original:

```
lojas
 ├── estoque
 └── pedidos ──── clientes
       │
   itens_pedido ──── promocoes
       │
    produtos
       ├── fornecedores
       └── categorias
```

### Modelo dimensional (camada gold)

| Tabela | Tipo | Finalidade |
|---|---|---|
| `dim_produto` | Dimensão | Cadastro de produtos |
| `dim_cliente` | Dimensão | Cadastro de clientes |
| `dim_loja` | Dimensão | Filiais |
| `dim_fornecedor` | Dimensão | Fornecedores |
| `dim_data` | Dimensão | Calendário |
| `fato_vendas` | Fato | Vendas realizadas |
| `fato_estoque` | Fato | Posição de estoque |
| `fato_pedidos` | Fato | Pedidos e movimentações |

---

## Análises possíveis

### Vendas
- Faturamento mensal e anual
- Ticket médio
- Quantidade de vendas
- Produtos mais vendidos
- Margem de lucro
- Desempenho por loja

### Estoque
- Produtos com estoque baixo
- Produtos sem movimentação
- Giro de estoque
- Cobertura de estoque em dias
- Ruptura de estoque
- Necessidade de reposição

### Inteligência de negócio
- Sazonalidade das vendas
- Curva ABC de produtos
- Previsão de demanda
- Comparação entre lojas
- Relação entre promoções e vendas

---

## Como executar

### Pré-requisitos

- [Python 3.12+](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/) para gerenciar ambiente e dependências
- Um projeto no [Supabase](https://supabase.com/) (PostgreSQL)

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/alerrandrofrederik/Retail_Analytics.git
cd Retail_Analytics

# Configurar as credenciais do Supabase
cp .env.example .env   # depois edite o .env com suas chaves

# Criar o ambiente virtual e instalar as dependências
uv sync

# Executar
uv run main.py
```

### Databricks CLI

Este projeto usa sempre o perfil **`pessoal`** do Databricks CLI (workspace pessoal). O perfil `DEFAULT` da máquina aponta para outro workspace e não deve ser usado aqui.

Todos os objetos do projeto (schemas, tabelas, volumes) ficam no catálogo **`lh_retail_analytics`** do Unity Catalog.

```bash
# Criar o perfil (uma única vez)
databricks auth login --host <url-do-workspace> --profile pessoal

# Usar o perfil em todos os comandos
databricks current-user me -p pessoal
```

Para não precisar repetir o `-p` na sessão do terminal:

```bash
export DATABRICKS_CONFIG_PROFILE=pessoal          # bash
$env:DATABRICKS_CONFIG_PROFILE = "pessoal"        # PowerShell
```

### Obter os dados

```bash
git clone https://github.com/ryanariefe/RYStore-Retail-Dataset.git
```

---

## Skills

As skills do projeto ficam na pasta [`skills/`](skills/), uma pasta por skill. Cada uma tem um `SKILL.md` com os passos, o que lê, o que escreve e o que nunca faz, e uma pasta `references/` com exemplos e modelos (quando houver).

| Skill | Para que serve |
|---|---|
| `profile` | Perfilar uma nova fonte ou tabela antes de construir em cima dela |
| `contract` | Contrato de dados com o sistema de origem |
| `metadata` | Tabelas e colunas de uma fonte, a partir dos arquivos e documentos |
| `incident` | Falha de job: causa raiz, opções, rascunhos de e-mail e registro |
| `quality` | Checagens que falharam ou alertaram e se a tabela pode ser usada |
| `reconcile` | Dois números que deveriam bater e onde divergem |
| `impact` | O que depende de uma tabela, coluna ou função e o que quebra |
| `toolkit` | Site de documentação do projeto, gerado a partir do repositório |
| `data-product` | Lado do consumidor de uma tabela: guia e contrato |
| `docs` | Runbook e guias, alinhados ao código |
| `pr-review` | Revisão de uma mudança contra os padrões |
| `big-review` | Revisão da plataforma inteira a partir dos logs e do repositório |
| `cost-review` | Para onde vai o custo de computação e armazenamento |
| `test-data` | Dados de teste com casos de borda e resultado esperado |
| `knowledge-refresh` | Conhecimento do projeto comparado com o código e os dados |
| `migration` | Inventário e plano em ondas de um ambiente legado |

---

## Estrutura do repositório

```
Retail_Analytics/
├── .env.example      # modelo das variáveis de ambiente (copiar para .env)
├── .python-version   # versão do Python usada pelo uv (3.12)
├── pyproject.toml    # metadados e dependências do projeto
├── main.py           # ponto de entrada
├── CLAUDE.md         # instruções do projeto para o Claude Code
├── skills/           # skills do projeto (uma pasta por skill)
│   └── <nome>/
│       ├── SKILL.md      # passos, entradas, saídas e limites da skill
│       └── references/   # exemplos e modelos usados pela skill
├── knowledge/        # conhecimento do projeto, uma página por assunto
│   ├── architecture/     # plataforma, ambientes e camadas
│   ├── business/         # glossário e regras de negócio
│   ├── decisions/        # decisões tomadas e em aberto
│   ├── incidents/        # registro de incidentes
│   └── sources/          # uma página por fonte de dados
├── reports/          # relatórios gerados (ex.: perfil de dados da fonte)
├── retail_analytics/ # bundle do Databricks com o código do pipeline
│   ├── databricks.yml    # targets dev e prod, catálogo lh_retail_analytics
│   ├── resources/        # jobs e pipelines
│   ├── src/              # código Python
│   └── tests/            # testes e fixtures
├── llm/              # prompts de execução, em ordem (ver llm/README.md)
├── .claude/skills/   # skills da Databricks (databricks aitools install --skills-only)
├── RYStore-Retail-Dataset/  # arquivos da fonte RYStore
└── README.md
```

Tudo o que o projeto aprende (fatos das fontes, regras de negócio, decisões, incidentes) fica em [`knowledge/`](knowledge/README.md).

<details>
<summary>Como este projeto foi criado</summary>

```bash
# 1. Cria o projeto Python com a versão desejada
uv init retail-analytics --python 3.12
cd retail-analytics

# 2. Inicializa o Git e faz o primeiro commit
git init
git add .
git commit -m "Initial commit"

# 3. Cria o repositório público no GitHub, associa o remoto e faz o push
gh repo create Retail_Analytics --public --source=. --remote=origin --push
```

</details>
