# WebGIS Saúde Canoas — V1.0

Aplicação pública territorial sobre Canoas/RS, código IBGE 4304606.

**Acesso:** https://marcianolima.github.io/webgis-saude-canoas/  
**GitHub Actions:** https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/update-data.yml

## O que a versão 1.0 entrega

1. Visão geral de estabelecimentos, população e leitos, com gráficos por tipologia e bairro.
2. Mapa MapLibre com fallback Leaflet, agrupamento, pesquisa, filtros por categoria e disponibilidade de leitos.
3. Rede assistencial com catálogo CNES, busca por bairro e exportação CSV dos pontos filtrados.
4. Nova seção de indicadores com séries anuais de dengue, chikungunya, Zika, nascidos vivos (SINASC) e óbitos (SIM), sujeitas à disponibilidade e validação do arquivo oficial.
5. Transparência sobre fonte, competência, metodologia, situação da coleta e períodos preliminares.

Tecnologias: TypeScript, Vite, Tailwind CSS, MapLibre, Leaflet, ECharts e Python 3.12. Hospedagem no GitHub Pages, sem servidor próprio.

## Fontes e critérios

| Indicador | Origem | Recorte/método | Situação |
|---|---|---|---|
| População | IBGE SIDRA/Cidades | Estimativas anuais, IBGE 4304606 | Validado |
| Estabelecimentos | Cadastro Nacional de Estabelecimentos de Saúde (CNES) | CSV nacional, ativos em Canoas, CNES únicos; inclui setor privado | Validado |
| Leitos existentes/SUS | Hospitais e Leitos, Ministério da Saúde | Uma competência e CNES único; não somar novamente campos de UTI | Validado |
| Dengue | Sinan/Dengue | Registros notificados de residentes (ID_MN_RESI); não equivale a casos confirmados | Validado |
| Nascidos vivos | SINASC | Residência materna CODMUNRES; 2025 preliminar | Validado |
| Óbitos não fetais | SIM | Residência CODMUNRES e TIPOBITO=2; 2025 preliminar | Validado |
| Chikungunya | Sinan/Febre de Chikungunya | Notificações por residência; confirmar esquema e cobertura | Validação em andamento |
| Zika | Sinan/Vírus Zika | Notificações por residência; confirmar esquema e cobertura | Validação em andamento |
| SIA | DATASUS e DEMAS | Produção ambulatorial por competência; não equivale a pacientes únicos | Cobertura insuficiente na API testada, sem total publicado |
| SIH | DATASUS e DEMAS | Produção hospitalar por competência, local de internação ou residência | Cobertura insuficiente na API testada, sem total publicado |
| PNI/RNDS | OPENDATASUS | Doses/cobertura requerem denominador e coortes verificadas | Pendente |
| e-SUS APS/PEC | SISAB e rede municipal | Extração de dados clínicos locais depende de acesso autorizado e LGPD | Pendente |

Fontes oficiais:
- https://www.ibge.gov.br/cidades-e-estados/rs/canoas.html
- https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude
- https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos
- https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue
- https://dadosabertos.saude.gov.br/dataset/arboviroses-febre-de-chikungunya
- https://dadosabertos.saude.gov.br/dataset/arboviroses-zika-virus
- https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc
- https://dadosabertos.saude.gov.br/dataset/sim
- https://datasus.saude.gov.br/assistencia-a-saude/
- https://apidadosabertos.saude.gov.br/static/swagger.json

**Regras de qualidade:** só publicar totais com cobertura comprovada; não substituir ausências por zero; não usar notificações como casos confirmados; não combinar períodos diferentes ou dados de residência e ocorrência. Referência da fonte difere da data de coleta.

## Privacidade e processamento

As bases nacionais podem conter microdados sensíveis. O processamento acontece somente no runner temporário do GitHub Actions. Os arquivos individuais não são salvos em public/, não são enviados como artefatos e nunca são persistidos no repositório. Os visitantes recebem apenas agregados municipais e campos cadastrais públicos do CNES.

Arquivos publicados:
- public/data/summary.json: população, CNES, leitos e fontes;
- public/data/establishments.geojson: pontos públicos de estabelecimentos;
- public/data/indicators.json: séries anuais validadas e metadados.

## Atualização e deploy

O workflow verifica testes, atualiza snapshots e publica a pasta dist/ no GitHub Pages. Executa diariamente às 08:17 UTC (05:17 Brasília). Bases nacionais volumosas têm cache temporal de 7 dias quando preliminares e 30 dias nos arquivos históricos. É possível solicitar reprocessamento manual pela aba Actions.

Para desenvolver localmente, execute npm install, python -m unittest discover -s tests -v e npm run build. Node.js 22+ e Python 3.12+.

## Homologação UX

A aplicação foi construída para leitura em desktop e dispositivos móveis, com informação progressiva, legendas, tabelas de apoio e explicações metodológicas. A revisão visual detalhada em aparelhos físicos e as preferências de layout do usuário são parte da homologação posterior à entrega técnica.

A versão 1.0 é um painel exploratório público; não é produto oficial da SMS e não substitui os sistemas municipais ou nacionais de saúde.
