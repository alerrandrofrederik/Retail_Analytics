Use a skill `contract` para escrever o contrato de dados entre a plataforma e a fonte RYStore.

Entradas: o perfil (reports/profile/rystore_profile.html), a metadata do prompt_02, knowledge/sources/rystore.md, knowledge/business/glossary.md e knowledge/decisions/decision-log.md.

O contrato traz só fatos e acordos: formato de entrega (um delimitador, uma codificação, um formato de data, um separador decimal, um token de nulo), o esquema com tipos e chaves, as regras de qualidade com o limite de cada uma, a entrega (frequência, carga completa ou incremental, como chega uma exclusão), o dono e o processo de mudança. Cada achado do perfil marcado para o contrato vira uma regra ou um ponto em aberto.

Os pontos em aberto (fuso de order_datetime, Cancelled/Refunded, signup_date, employees completo, vendas de madrugada, hire_date) viram uma lista de perguntas para o dono da fonte, sem resposta inventada.

Pré-requisito: prompt_02 concluído.

Saída: o contrato da fonte e a lista de pontos em aberto, no lugar que você propuser antes de criar; decision-log atualizado.
