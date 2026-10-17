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
| Chikungunya | Sinan/Febre de Chikungunya | Notificações de residentes, arquivo anual completo; não casos confirmados | Validado, 2025–2026 |
| Zika | Sinan/Vírus Zika | Notificações de residentes, arquivo anual completo; não casos confirmados | Validado, 2025–2026 |
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

## Resultados confirmados da primeira carga v1.0

| Série por residência | 2024 | 2025 | 2026 |
|---|---:|---:|---:|
| Dengue (notificações) | — | 1.037 | 32 |
| Chikungunya (notificações) | — | 6 | 4 |
| Zika (notificações) | — | 3 | 0 |
| SINASC (nascidos vivos) | 3.435 | 3.698 | — |
| SIM (óbitos não fetais) | 3.136 | 1.771 | — |

**Fonte:** arquivos anuais do Ministério da Saúde extraídos em 17/10/2026. Os anos recentes são sujeitos a revisão; particularmente, 2025 no SIM/SINASC e 2026 nas arboviroses têm caráter preliminar. Não comparar notificações com casos confirmados.

Rede CNES: 969 estabelecimentos ativos, 962 com posição geográfica, 35 UBS classificadas e 6 estabelecimentos hospitalares (incluindo hospital-dia). Leitos: 668 existentes, 539 SUS, competência 08/2026.

## Seleção individual e análise cruzada — v1.1

A aplicação oferece um **explorador contextual de estabelecimentos** nas abas Visão geral, Mapa, Estabelecimentos e Indicadores. Ao selecionar o CNES pela busca, pelo marcador, pela lista ou pelo gráfico de comparação de capacidade, a seleção permanece ativa ao trocar de aba e pode ser compartilhada pelo parâmetro `?cnes=NNNNNNN`.

O arquivo `public/data/facilities.json` é gerado pelo coletor diário e inclui todos os **969 estabelecimentos ativos** do município, inclusive os 7 sem coordenadas publicadas. Os atributos são públicos e cadastrais: CNES, nome, tipologia, bairro, endereço, telefone, gestão quando preenchida e vínculo SUS quando declarado.

A base de leitos possui **capacidade individual por CNES** na competência 08/2026: leitos existentes, leitos SUS e respectivos subconjuntos de UTI. A visualização evita a soma duplicada das UTIs. Registros sem correspondência em leitos recebem **valor indisponível**, nunca zero presumido. O gráfico comparativo é clicável e seleciona o estabelecimento da barra escolhida.

Quando há seleção, o painel geral troca os cartões para dados da unidade e passa a calcular os gráficos territoriais com o recorte do seu bairro e da sua categoria. Gráficos de dengue, nascimentos, mortalidade e população permanecem **explicitamente municipais**, pois os microdados foram agregados por residência e não identificam atendimento por CNES.

Não são fornecidos prontuários, nome de pacientes, CPF/CNS, atendimentos individuais nem inferência de ocupação de leitos. Alguns campos cadastrais podem vir em branco na fonte e são exibidos como não informados.

Teste técnico: `python -m unittest discover -s tests -v` e `npm run build`; o workflow executa ambos os procedimentos e publica o site.

## Dados oficiais MGDI/DATASUS — assistência, financiamento e rastreamento

A partir da revisão de 17/10/2026, a aplicação oferece **uma seção de Assistência e financiamento** com dados municipais validados de **eMulti custeadas e homologadas, repasses federais para eMulti, exames citopatológicos e mamografias de rastreamento**. O processamento é feito a partir dos arquivos CSV ZIP oficiais do Ministério da Saúde disponíveis no catálogo de dados abertos. Cada indicador apresenta sua própria unidade e competência; não há soma de competências acumuladas.

Os indicadores de exames são apresentados com referência predominantemente **anual** nos recursos consultados (e o ano mais recente pode estar incompleto), não devendo ser confundidos com séries mensais de equipes e repasses. Arquivos individuais não são publicados; o agregado por Canoas está em `public/data/sus.json`.

O arquivo oficial da **razão de consultas APS por 100 habitantes** foi localizado, mas não processado integralmente devido ao tamanho extraído acima do limite seguro da rotina atual; permanece documentado como indisponível. A extração integral de SIH e SIA pelos arquivos mensais DBC ainda depende de uma via de acesso estável — o endereço HTTPS do DATASUS testado apresentou timeout no runner, e a API DEMAS retornou apenas amostras. Portanto, **os cinco indicadores específicos publicados não representam o total de produção hospitalar ou ambulatorial do SUS.**

Recursos utilizados: `emultcust.csv.zip`, `emulthomol.csv.zip`, `emultvlrff.csv.zip`, `ccmec25a64.csv.zip`, `ccmec50a69.csv.zip`, publicados em `https://demas-dados-abertos.s3.amazonaws.com/csv/`. O script `scripts/sus_sources.py` realiza validação de município, período, valor e cobertura antes da publicação.

## Atualização da página inicial municipal (versão 1.2)

A aplicação abre no **Painel Municipal de Saúde**, que agrega IBGE, CNES, leitos, SINAN, SIM, SINASC e indicadores de assistência MGDI em seções distintas e com referências temporais e metodológicas identificadas. A seleção de um estabelecimento não substitui esses valores por informações individuais. A antiga visão geral foi preservada como **Análise territorial**, onde a seleção por CNES é mantida.

O coletor `scripts/sus_sources.py` usa ZIP em streaming, retries progressivos, limites configuráveis (350 MiB compactados, 1.500 MiB descompactados e 12 milhões de linhas), sem armazenar microdados no GitHub. Três indicadores RIPSA adicionais estão previstos: razão de consultas médicas na APS por 100 habitantes, razão de consultas especializadas por habitante e valor médio por AIH. **Só aparecerão como disponíveis se o CSV completo comprovar dados municipais.** A unidade e o denominador de cada indicador são preservados. Problemas persistentes são sinalizados no GitHub Actions e no painel; não são convertidos em zero.

A fonte oficial de cobertura vacinal é publicada no TabNet e em arquivos nacionais PNI por mês, mas exige seleção de vacina/dose/faixa etária e compatibilização de denominadores. Até existir um agregador validado, não haverá um índice municipal único artificial. O acesso aos arquivos mensais DBC de SIH/SIA permanece como integração separada para não confundir os indicadores RIPSA com totais hospitalares ou ambulatoriais.

## Avanço RIPSA — integração de consultas e internações anuais

O arquivo de razão de consultas médicas na APS (`mgdi_ms_4iu.csv.zip`) contém dados por faixa etária. A versão municipal utiliza **somente a categoria `sg_categoria=TC` (Total)**; não soma razões por faixa etária. O mesmo tratamento de total é aplicado às consultas especializadas (`mgdi_ms_0bx.csv.zip`), que também fornecem decomposição por especialidade.

O recurso oficial RIPSA `ripsa019rc.csv.zip`, indicador REC.3.02, apresenta por município e ano o numerador (valor das internações) e o denominador (número de internações). O coletor produz dois indicadores independentes: **internações hospitalares SUS agregadas anuais** (denominador) e **valor médio pago por AIH** (numerador ÷ denominador × multiplicador). Somente dados do município 430460 e anos únicos são aceitos. Não são pacientes distintos, internações por residência, produção discriminada por CNES nem substitutos integrais dos arquivos DBC mensais SIH/SUS.

Fontes: https://dadosabertos.saude.gov.br/dataset/ripsa-recursos-dimensao-3-recursos-financeiros-assistencia-a-saude/resource/ripsa019rc_csv e https://dadosabertos.saude.gov.br/dataset/ripsa-cobertura-dimensao-1-consultas-medicas-e-odontologicas/resource/mgdi_ms_4iu_csv.
