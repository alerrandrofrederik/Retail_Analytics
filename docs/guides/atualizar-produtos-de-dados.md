# Guia: atualizar a página de produtos de dados

A página [`docs/data-products/index.html`](../data-products/index.html) é gerada a partir das pastas de produto. Não a edite à mão.

1. Edite o `README.md` do produto (uma seção `## ` por aba: Visão geral, Guia, Modelo de dados, Métricas, Consultas iniciais, Qualidade, Versões, Pontos em aberto) ou o contrato `*.odcs.yaml`.
2. Se mudou o contrato, valide-o contra o JSON Schema do ODCS v3.1.0, como foi feito em 2026-10-30.
3. Gere a página, na raiz do repositório:
   ```bash
   uv run --no-project --with markdown --with pyyaml python docs/data-products/build_index.py
   ```
4. Um produto novo é uma pasta nova em `docs/data-products/<produto>/`, com `README.md` e `<produto>.odcs.yaml`. A skill `data-product` ([`llm/prompt_14.md`](../../llm/prompt_14.md)) faz o plano e o conteúdo.
