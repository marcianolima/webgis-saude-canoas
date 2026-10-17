# Correção CNES — WebGIS Saúde Canoas

## Diagnóstico confirmado (GitHub Actions)

- A coleta em `/cnes/estabelecimentos` percorreu 250 páginas de 20 linhas e abortou. O snapshot não foi publicado.
- A coleta de leitos recebeu um único registro, produzindo 21 leitos e 0 SUS, números que **não são total municipal validado**.
- O frontend e o deploy foram compilados e publicados corretamente na última Action.

## Atualização deste patch

- Preferência pela API oficial `/assistencia-a-saude/cnes-estabelecimentos` (até 1000 linhas por página) com `co_ibge=430460` e `nu_comp` (mês de referência), escolhendo a competência recente de estabelecimentos independentemente da competência de leitos.
- Validação explícita de município, competência, identificador CNES, duplicidade e cobertura geográfica.
- Rejeita páginas repetidas. Exibe as chaves do primeiro registro no log para diagnosticar divergências de contrato.
- Revoga automaticamente o agregado anterior de leitos sustentado em apenas um registro; não publica quantidades suspeitas.
- Novos testes de segurança dos dados (22 testes Python aprovados).

## Publicação

Substitua apenas os arquivos `scripts/update_data.py` e `tests/test_pipeline.py` dentro da pasta do repositório. NÃO copie a pasta do ZIP por cima da raiz criando uma subpasta extra. Faça commit e push da branch `main`.

Execute **Actions → Verificar, atualizar dados e publicar WebGIS Saúde → Run workflow → main**. A execução manual coleta também séries pesadas, portanto pode demorar; use os logs `Atualizar dados públicos de saúde`. Verifique o `sourceInfo.cnes.status`, o `facilities.total` e o número de `features` em `public/data/establishments.geojson`.

**Limitação**: não foi possível chamar os endpoints reais deste ambiente. É indispensável validar os logs após a primeira execução. Caso a API ignore `nu_comp` ou devolva schema diferente, o sistema interromperá a publicação dos dados em vez de inventar métricas. Envie os primeiros logs para ajustar o adaptador.
