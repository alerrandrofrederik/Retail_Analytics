# Retail Analytics: Gestão de Vendas e Estoque

Projeto de análise de dados de varejo construído sobre o banco **RYStore**. O objetivo é montar um pipeline que sai dos arquivos CSV originais, passa por um banco PostgreSQL no Supabase e chega a um modelo dimensional pronto para indicadores de vendas, estoque e inteligência de negócio.

> **Fonte dos dados:** [RYStore Retail Dataset](https://github.com/ryanariefe/RYStore-Retail-Dataset)

---

## Sumário

- [Arquitetura do pipeline](#arquitetura-do-pipeline)
- [Modelo de dados](#modelo-de-dados)
- [Análises possíveis](#análises-possíveis)
- [Como executar](#como-executar)
- [Estrutura do repositório](#estrutura-do-repositório)

---

## Arquitetura do pipeline

```
┌──────────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌────────────────┐
│ Arquivos CSV │ ──▶ │ Supabase PostgreSQL  │ ──▶ │     ETL com SQL     │ ──▶ │ Chat Genie One │
│ dados brutos │     │ importação e staging │     │ limpeza, transforma-│     │                │
│              │     │                      │     │ ção e modelagem     │     │                │
└──────────────┘     └──────────────────────┘     └─────────────────────┘     └────────────────┘
```

| Etapa | Responsabilidade |
|---|---|
| **Arquivos CSV** | Dados originais do RYStore |
| **Supabase PostgreSQL** | Importação dos CSVs para tabelas de *staging* |
| **ETL com SQL** | Limpeza, transformação e modelagem dimensional |
| **Chat Genie One** | Consumo e análise dos dados modelados |

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

### Modelo dimensional (PostgreSQL)

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

### Obter os dados

```bash
git clone https://github.com/ryanariefe/RYStore-Retail-Dataset.git
```

---

## Estrutura do repositório

```
Retail_Analytics/
├── .env.example      # modelo das variáveis de ambiente (copiar para .env)
├── .python-version   # versão do Python usada pelo uv (3.12)
├── pyproject.toml    # metadados e dependências do projeto
├── main.py           # ponto de entrada
└── README.md
```

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
