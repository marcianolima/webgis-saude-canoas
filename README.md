# WebGIS Saúde Canoas — versão 1.5.0 (fechamento técnico do ciclo v1)

[![Atualização e deploy](https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/update-data.yml/badge.svg)](https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/update-data.yml)
[![Homologação de interface](https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/ux-smoke.yml/badge.svg)](https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/ux-smoke.yml)

**[Abrir WebGIS Saúde Canoas](https://marcianolima.github.io/webgis-saude-canoas/)** · [Código-fonte](https://github.com/marcianolima/webgis-saude-canoas) · [Metodologia e fontes](./FONTES_BNAFAR_SIAPS.md)

Aplicação territorial pública de indicadores e estabelecimentos de saúde de **Canoas, Rio Grande do Sul** (IBGE **4304606**). Projeto demonstrativo de dados abertos, **não é sistema oficial da Secretaria Municipal de Saúde** nem substitui CNES, DATASUS, e-SUS APS/PEC, SIAPS ou outros sistemas do SUS.

## Funcionalidades

O aplicativo é responsivo, com menu agrupado em desktop e drawer no celular, destaque/alinhamento da página ativa à esquerda, navegação por teclado, tema claro/escuro persistente, atalhos contextuais e indicação de carregamento e ausência de informação.

| Página | Conteúdo |
| --- | --- |
| **Panorama municipal** | Indicadores de população, rede, leitos e sínteses municipais com referência temporal |
| **Rede e território** | Gráficos de estabelecimentos por tipologia e bairro, análise contextual por CNES |
| **Mapa** | Pontos CNES em MapLibre, agrupamento e seleção, com alternativa Leaflet em caso de indisponibilidade |
| **Estabelecimentos** | Catálogo completo, busca/filtros, ficha por CNES, exportação CSV e vínculos de leitos quando existentes |
| **Vigilância** | Séries anuais de dengue, chikungunya e Zika; distinguir notificações de casos confirmados |
| **Nascimentos e óbitos** | SINASC e SIM por residência, com alertas de dados preliminares |
| **Atenção Primária** | Indicadores validados de assistência MGDI/RIPSA |
| **Farmácia e SIAPS** | Monitoramento e links BNAFAR/Qualifar e SIAPS; sem inventar indicadores municipais |
| **APS · histórico** | Indicadores do SISAB/Previne Brasil, identificados como série histórica encerrada |
| **Prevenção e exames** | Exames e rastreamento com unidades/competências próprias |
| **Financiamento e RIPSA** | eMulti, repasses e séries de produção/financiamento com critérios explícitos |
| **Produção SIH/SIA** | AIH/RD e produção aprovada PA por competência e CNES; meses incompletos claramente assinalados |
| **Fontes e metodologia** | Catálogo pesquisável, filtros por status, exportação CSV, origem, período e limitações |

Ao selecionar um estabelecimento, a aplicação mantém o CNES entre seções pertinentes. O vínculo pode ser compartilhado por `?cnes=NNNNNNN`. Estatísticas calculadas para a população residente **não** são atribuídas artificialmente ao estabelecimento.

## Situação dos dados: referência auditada de 27/10/2026

A publicação automática mais recente inspecionada na auditoria de fechamento foi em **27/10/2026**; o retrato diário do CNES corresponde àquela captura. Os números são **snapshots**, não valores permanentes:

| Conjunto | Recorte publicado | Situação |
| --- | --- | --- |
| CNES, estabelecimentos ativos de todos os tipos | **971** unidades, **964** com coordenadas; **35** UBS e **6** hospitalares pela classificação CNES | Validado em 27/10/2026 |
| CNES, leitos existentes e vinculados ao SUS | **668** existentes, dos quais **539** SUS | Competência **09/2026** |
| IBGE, população estimada | **359.845** habitantes | Referência **2026** |
| SINAN arboviroses | Séries municipais por residência, sujeitas à atualização de cada arquivo | Dados preliminares nos anos recentes |
| SIM / SINASC | Séries anuais por residência | Alguns períodos preliminares |
| SIH, AIH reduzida (RD) | **15/21** competências solicitadas, de 01/2025 a 09/2026 | **Parcial**; não somar meses faltantes como zero |
| SIA, produção aprovada (PA) | **12/21** competências solicitadas, de 01/2025 a 09/2026 | **Parcial**; PA não cobre todos os instrumentos SIA |
| SISAB/Previne Brasil | Série histórica até 2024 | Não equivale a SIAPS atual |
| BNAFAR / Qualifar / SIAPS atual | Catálogo e links de consulta oficiais | Sem série municipal homologada |
| PIAPS-RS, SRAG/Sivep-Gripe, PNI 2026, SISAGUA | Novas fontes documentadas e visíveis em **Fontes e metodologia** | **Catalogadas; sem integração estatística municipal** |

**Atenção:** 971 estabelecimentos CNES **não** significa 971 unidades públicas ou 971 unidades municipais. Os leitos existentes não representam ocupação nem disponibilidade em tempo real. Doses não equivalem a cobertura vacinal; notificações não equivalem a incidência ou casos confirmados. Dados de bairros são declarados no cadastro CNES, sem equivalência automática com limites oficiais dos bairros do GeoCanoas.

A aba **Fontes e metodologia** e os arquivos JSON descrevem os estados de cada coletor. Valores ausentes, competências incompletas e integrações sem cobertura validada não são preenchidos com zero.

## Dados, processamento e privacidade

Os arquivos publicáveis são **agregados municipais e atributos cadastrais públicos de estabelecimentos**, sem prontuários, CPF, CNS ou dados identificáveis de pacientes. Microdados nacionais eventualmente necessários são processados em runner temporário e não commitados em `public/`.

| Arquivo | Conteúdo |
| --- | --- |
| `public/data/summary.json` | População, rede CNES, leitos, proveniência |
| `public/data/establishments.geojson` | Pontos públicos CNES válidos |
| `public/data/facilities.json` | Inventário público por CNES, inclusive sem coordenadas |
| `public/data/indicators.json` | Vigilância e estatísticas vitais agregadas |
| `public/data/sus.json` | Indicadores MGDI/RIPSA e assistência |
| `public/data/production.json` | Produção SIH/SIA por competências e CNES com limiares de privacidade |
| `public/data/aps.json` | Indicadores históricos SISAB |
| `public/data/farmacia_siaps.json` | Referências BNAFAR/Qualifar/SIAPS, sem números não validados |
| `public/data/extra_sources.json` | Catálogo PIAPS, SRAG, PNI e SISAGUA — sem números não validados |

Fontes oficiais principais: [CNES](https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude), [Hospitais e leitos](https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos), [IBGE](https://www.ibge.gov.br/cidades-e-estados/rs/canoas.html), [DATASUS](https://datasus.saude.gov.br/assistencia-a-saude/), [SINASC](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc), [SIM](https://dadosabertos.saude.gov.br/dataset/sim), [SISAB histórico](https://dadosabertos.saude.gov.br/dataset/indicadores_desempenho_sisab), [BNAFAR](https://bnafar.github.io/statusenvio/), [SIAPS](https://siaps.saude.gov.br/publico), [PIAPS-RS](https://atencaoprimaria.rs.gov.br/painel-piaps), [SRAG/Sivep-Gripe](https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026), [PNI 2026](https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2026) e [SISAGUA](https://dadosabertos.saude.gov.br/dataset/sisagua-vigilancia-parametros-basicos).

## Tecnologias e execução

- **Frontend:** TypeScript, Vite, Tailwind CSS, ECharts, MapLibre GL JS, alternativa Leaflet, ícones Lucide. Aplicação estática no GitHub Pages.
- **ETL:** Python 3.12 e PySUS para fluxos de produção, com limites de download, validação de competência e testes de contrato.
- **CI/CD:** GitHub Actions; o workflow [update-data.yml](./.github/workflows/update-data.yml) verifica, atualiza quando necessário e publica. A coleta diária é agendada para **08:17 UTC (05:17, horário de Brasília)**. Publicações têm latência própria de cada origem e podem falhar isoladamente, preservando snapshots anteriores.
- **UX:** [ux-smoke.yml](./.github/workflows/ux-smoke.yml) compila e usa Chromium headless/Playwright para smoke tests mobile **360, 390 e 768 px** e desktop **1280 px**, incluindo menu, foco, tema, overflow e capturas.

```bash
npm install
python -m unittest discover -s tests -v
npm run build
npm run dev
```

Pré-requisitos: Node.js 22+, npm e Python 3.12+. Para homologação de navegador, instalar Playwright e Chromium conforme [workflow de smoke](./.github/workflows/ux-smoke.yml); o comando é `node scripts/smoke-mobile.cjs` com o projeto compilado.

## Qualidade, limites e critérios de aceite

Testes automatizados **não equivalem** a homologação epidemiológica, revisão profissional da Secretaria de Saúde ou teste com usuários reais. A publicação é considerada tecnicamente apta somente quando **verify**, build/deploy e smoke de UX terminarem com sucesso no GitHub Actions. A situação de cada execução pode ser acompanhada nos badges acima.

Pendências decorrentes de dependências externas: série municipal atual SIAPS e BNAFAR, cobertura completa SIH/SIA, homologação de doses PNI e SRAG, territórios/bairros oficiais por geoprocessamento e comparação validada de indicadores. Foram documentadas sem resultados simulados. Para ampliar dados, é indispensável verificar dicionários, município por residência/ocorrência, competências, completude, supressão estatística, licenciamento e LGPD.

## Governança e atualização

O código é aberto, mas **os indicadores pertencem às suas fontes**, e nenhuma interpretação deve omitir fonte, competência, universo, denominador ou cobertura. Mudanças de regras nacionais ou revisões retrospectivas podem modificar os números ao longo do tempo. Para identificar a competência de cada bloco, utilize **Fontes e metodologia** no próprio painel.

**Licença:** consulte [LICENSE](./LICENSE). **Escopo do projeto:** exploratório, informativo e de transparência pública.
