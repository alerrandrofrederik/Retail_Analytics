Use a skill `metadata` para montar a metadata da fonte RYStore (pasta RYStore-Retail-Dataset).

Entradas: os 9 CSVs, o data_dictionary.csv e o README.md da fonte, o perfil em reports/profile/rystore_profile.html e a página knowledge/sources/rystore.md.

Escreva um script Python que leia cada arquivo com todas as colunas como texto e extraia os fatos técnicos: tabelas, colunas, tipos inferidos, chaves primárias e estrangeiras, nulos permitidos e valores de domínio (status, canal, tier). As descrições vêm dos documentos da fonte, nunca inventadas. O data_dictionary.csv é genérico e tem erros (ex.: discount_type descrito como Integer): quando o documento divergir dos dados, registre a divergência; quando não houver descrição, marque "sem documentação".

Pré-requisito: perfil concluído (prompt_01).

Saída: o arquivo de metadata da fonte e o script que a gerou, em um lugar que você proponha antes de criar (siga a estrutura do repositório), e a página knowledge/sources/rystore.md atualizada com o link. Mostre o plano antes de escrever.
