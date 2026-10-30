# Pontos em aberto: contrato RYStore

Pauta do contrato [`rystore.odcs.yaml`](rystore.odcs.yaml) da fonte RYStore, com as respostas. Os 19 pontos foram respondidos em 2026-10-30 e o contrato passou da versão 0.1.0 (`draft`) para a 1.0.0 (`active`). Os números estão no [perfil da fonte](../reports/profile/rystore_profile.html).

Origem das respostas:
- **EDD:** o engenheiro de dados respondeu na conversa (ele também é o dono da fonte neste projeto).
- **Delegada:** o engenheiro pediu que o Claude decidisse e seguisse. Valem até alguém revisar.

## Responsáveis e entrega

| # | Pergunta | Resposta | Origem |
|---|---|---|---|
| 1 | Dono da fonte e canal de suporte | O engenheiro de dados do projeto responde pela fonte; o suporte é por issues do repositório no GitHub | EDD |
| 2 | Storage ou PostgreSQL? | Supabase Storage: um CSV por tabela, no bucket `rystore`, lido pela API S3 | EDD |
| 3 | Frequência e horário | Uma entrega por dia, disponível até 06:00 UTC | EDD (frequência); delegada (horário) |
| 4 | Completa ou incremental? | `orders` e `order_items` são incrementais: um arquivo por dia, com os pedidos do dia, e um pedido antigo que muda (devolução) volta inteiro no arquivo do dia da mudança, valendo a última entrega. As outras 7 tabelas, `inventory` inclusive, chegam completas todo dia. `inventory` é uma foto do estoque, então fica completa (desvio da opção escolhida, que a listava como incremental) | EDD; detalhe delegado |
| 5 | Como chega uma exclusão? | Nas tabelas completas, a linha que some da foto foi excluída. Em `orders`/`order_items` nada é excluído: muda o status | EDD |
| 6 | Aviso de mudança | 7 dias antes, com nova versão do contrato | Delegada |

## Semântica dos dados

| # | Pergunta | Resposta | Origem |
|---|---|---|---|
| 7 | Fuso de `order_datetime` | Europe/London, hora local sem offset. Na hora que não existe, avança 1h; na hora repetida, vale a primeira (BST, +01:00) | EDD |
| 8 | Cancelled e Refunded na receita | Receita conta só `Completed`. `Cancelled` e `Refunded` ficam com o status, fora da receita | EDD |
| 9 | `signup_date` | Adesão ao programa de fidelidade. Pedido anterior é válido, e cadastro depois do período também | Delegada |
| 10 | `employees` completo? | É uma amostra. `staff_count` é o quadro oficial e não se compara com `employees` | EDD |
| 11 | `hire_date` antes da abertura da loja | Transferência: admissão na empresa. É válido | EDD |
| 12 | Vendas na loja de madrugada | São reais e válidas | EDD |
| 13 | `aisle_location` | Texto livre, corredor ou seção; os dois são válidos | Delegada |
| 14 | `discount_value` | Percentual quando `discount_type` = `Percentage`; GBP quando `Fixed` | Delegada (confirmado nos dados) |
| 15 | Listas de valores | Fechadas com os valores do perfil; um valor novo gera alerta (`warning`) e é anunciado como mudança de contrato | Delegada |

## Formato e documentação

| # | Pergunta | Resposta | Origem |
|---|---|---|---|
| 16 | Descrições reais das colunas | Por ora ficam os textos genéricos do dicionário; descrições melhores entram numa versão futura do contrato, vindas do glossário | Delegada |
| 17 | Inteiros como decimal | As colunas inteiras chegam sem `.0` (conferido pelo script da metadata). Decimais podem ter número variável de casas (`3.0`, `18.5`) | Delegada (confirmado nos dados) |
| 18 | Total com diferença de 0,01 | Aceito: tolerância de 0,01 por arredondamento | Delegada |
| 19 | Dados pessoais | Tratados como reais (`restricted`), mascarados fora da bronze, embora a fonte diga que são fictícios | Delegada |
