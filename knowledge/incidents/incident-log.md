# Registro de incidentes

As entradas vêm da skill `incident` ([`skills/incident/SKILL.md`](../../skills/incident/SKILL.md)), uma por execução que falhou, da mais recente para a mais antiga.

Formato de cada entrada:

```
## AAAA-MM-DD: <job> — <resumo>

- Erro: a mensagem e onde apareceu
- Causa raiz: o que causou, com a evidência
- Impacto: tabelas e consumidores afetados
- Ação: o que foi feito e o que fica para evitar a repetição
- Status: aberto | resolvido em AAAA-MM-DD
```

## 2026-10-30: rystore_pipeline: a publish falhou em silver.orders (timestampNtz)

- **Erro:** na rodada `966981410696310`, a `publish` falhou duas vezes com `DELTA_FEATURES_REQUIRE_MANUAL_ENABLEMENT` (`timestampNtz`) ao recriar `silver.orders`. Antes disso, a `build_silver` tinha falhado uma vez com um erro de E/S do volume (`Async write failed`) e passado na nova tentativa automática.
- **Causa raiz:**
  - `silver.orders` vinha da versão em PySpark, com o protocolo Delta sem `timestampNtz`, e o `CREATE OR REPLACE` mantém o protocolo.
  - O DuckDB grava o Parquet fora de ordem, o que o volume montado às vezes recusa.
- **Impacto:** no dev, de 17:31 a 17:42 UTC, 17 das 30 tabelas estavam na versão nova e as outras não; a gold ainda não existia. Nenhum consumidor. Mais detalhes no [relatório](../../reports/incident/incident_2026-10-30_rystore_pipeline.html).
- **Ação:**
  - `TBLPROPERTIES delta.feature.timestampNtz` em todo `CREATE` da `publish`, e gravação via arquivo temporário (`silver._copy`), no commit `5ed9235`;
  - depois, a `publish` em duas fases (`b6e5f95`).
- **Status:** resolvido em 2026-10-30 (rodadas `173663739566769` e `498752805931100`).

## 2026-10-30: rystore_pipeline: primeira execução abortada por lentidão

- **Erro:** nenhum erro de código. A rodada `719373279280521` (dev) foi cancelada pelo engenheiro de dados às 17:07:59 UTC, depois de 12 min.
- **Causa raiz:** o desenho em PySpark era pesado demais para 59 mil linhas.
  - A `ingest_bronze` levou cerca de 3 min para subir o serverless e 6,4 min para executar: 737 downloads em série, `%pip` e `createDataFrame` a partir de listas Python.
  - A `build_silver` rodou por cerca de 2 min antes do cancelamento.
- **Impacto:** nenhum consumidor. Ficaram tabelas parciais na bronze e na silver do dev, que a publicação seguinte substitui.
- **Ação:** pipeline refeito em Python puro com DuckDB ([registro de decisões](../decisions/decision-log.md)). Localmente, o pipeline inteiro roda em cerca de 23 s.
- **Status:** resolvido em 2026-10-30.
