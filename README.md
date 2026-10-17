# WebGIS Saúde Canoas

**Dashboard territorial de saúde pública de Canoas/RS — código IBGE 4304606.** Aplicação estática, responsiva, com mapas e gráficos interativos, GitHub Pages e atualização programada via GitHub Actions.

> **Versão inicial / experimental, não oficial.** Não substitui os dados primários do Ministério da Saúde ou da Secretaria Municipal de Saúde. Um campo sem coleta válida aparece como **— / indisponível**, nunca como `0` inventado. Os arquivos iniciais contêm apenas valores do IBGE conferidos na fonte e um GeoJSON vazio; as primeiras consultas reais ao CNES e às demais APIs serão feitas **pelo GitHub Actions com acesso à internet**.

## O que já está implementado

- Painel mobile-first com indicadores do IBGE, CNES e leitos, gráficos ECharts com séries anuais e classificação por tipo, estados vazios informativos.
- Mapa MapLibre GL JS, base CARTO/OSM, clusters com contador, pop-ups enriquecidos e expansão de agrupamentos.
- Filtros por tipo (UBS, hospital, urgência, clínica, outros e unidades com leitos confirmados), nome, bairro ou CNES; lista de estabelecimentos e exportação CSV dos pontos filtrados.
- Tema claro/escuro, acessibilidade básica, rotas de navegação sem recarregar página e tela de metodologia/proveniência.
- Coleta agendada sem servidor próprio, armazenamento leve em `public/data/` e deploy na mesma Action.

**Tecnologias:** Vite 6, TypeScript, Tailwind CSS 3, ECharts 5, MapLibre 4, Lucide e Python 3.12 (biblioteca padrão). Os navegadores acessam somente os arquivos estáticos e a base cartográfica; os servidores de dados públicos são consultados **no workflow**, não no celular do visitante.

## Publicar usando somente o celular (Android)

O aplicativo GitHub no celular é excelente para navegar e editar arquivos individuais, **mas não é um método adequado para importar a estrutura completa de um ZIP**. A alternativa mais segura é usar **Termux + GitHub CLI**, após extrair o pacote baixado. O diretório raiz deve conter `package.json`, `index.html`, `src/`, `public/`, `scripts/`, `tests/` e `.github/` — **sem uma pasta externa extra**.

### Método A — Termux (recomendado)

1. Instale o Termux por uma fonte oficial do projeto, abra e conceda acesso aos arquivos compartilhados.
2. Baixe o ZIP desta conversa para a pasta `Downloads` e extraia os arquivos usando o gerenciador do Android, ou use os comandos abaixo.
3. Execute:

```bash
pkg update -y
pkg install -y git gh unzip
termux-setup-storage
cd ~/storage/downloads
unzip -o webgis-saude-canoas.zip
cd webgis-saude-canoas
gh auth login
# Abra o link de autenticação informado pelo gh no navegador.
git init -b main
git add .
git -c user.name='WebGIS Canoas' -c user.email='webgis@users.noreply.github.com' commit -m 'feat: iniciar WebGIS Saúde Canoas'
gh repo create webgis-saude-canoas --public --source=. --remote=origin --push
```

Se já tiver criado o repositório pelo aplicativo, em vez de `gh repo create ...`, faça `git remote add origin https://github.com/SEU_USUARIO/webgis-saude-canoas.git` e `git push -u origin main`. Se precisar, configure `git config user.name` e `git config user.email` com suas credenciais de autoria **antes do commit**. A autenticação `gh auth login` não exige colocar tokens no código do projeto. Não inclua senhas ou dados pessoais no GitHub.

### Método B — navegador em modo desktop

No Chrome/Firefox do smartphone, entre no repositório no `github.com` → **Add file → Upload files**, envie o **conteúdo extraído**. Dependendo do navegador, a seleção de diretórios inteiros pode não funcionar; nesse caso, use o Termux. **Não envie apenas o ZIP**: GitHub Pages não executa um arquivo compactado.

### Habilitar a publicação

1. Abra **Settings → Pages → Build and deployment → Source → GitHub Actions**.
2. Abra **Settings → Actions → General → Workflow permissions → Read and write permissions** para permitir commits dos JSONs. Em contas/organizações que bloqueiam esta opção, ajuste a política com o administrador.
3. Abra **Actions → Dados e publicação WebGIS Saúde → Run workflow** para forçar a primeira atualização. Examine os logs da etapa `Coletar snapshots oficiais` e os arquivos `public/data/`.
4. O mesmo workflow constrói o frontend (`npm run build`) e publica em **`https://SEU_USUARIO.github.io/webgis-saude-canoas/`**. O endereço também aparece no resultado do job `deploy`. O primeiro `push` da `main` já faz uma publicação inicial.

A Action executa às **segundas e quintas, 08:17 UTC (05:17 de Brasília, quando UTC−3)**, além dos disparos manuais e commits na `main`. Atualizações fazem commit na mesma branch antes do deploy. A publicação **não exige PAT ou segredo adicional** quando o GitHub Pages e o `GITHUB_TOKEN` estão habilitados. Como commits feitos com `GITHUB_TOKEN` geralmente não disparam outros workflows de `push`, tudo está reunido em **um único workflow**.

## Fontes e dados efetivamente tratados

As URLs e parâmetros abaixo foram estudados em **16/10/2026**; a execução dos endpoints de dados em produção depende da Action. Não afirmar disponibilidade de um indicador até o arquivo atualizado conter o valor e o status `ok`.

| Fonte | API ou referência | Indicadores planejados/implementados | Situação no ZIP |
|---|---|---|---|
| IBGE Cidades | https://www.ibge.gov.br/cidades-e-estados/rs/canoas.html | Estimativa 2026 (**359.845**), Censo 2022 (**347.657**), área **130,774 km²** e densidade Censo 2022 **2.658,15 hab./km²** | **Valor inicial verificado** |
| IBGE SIDRA | `https://apisidra.ibge.gov.br/values/t/6579/n6/4304606/v/9324/p/all?formato=json` | Série anual de população; última estimativa se disponível e validada | Coletor implementado, ainda não executado online |
| CNES — estabelecimentos | `https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?codigo_municipio=430460&status=1&limit=20&offset=0` | Unidades, coordenadas, tipo, bairro, telefone, contagem e agrupamentos | Coletor implementado, aguardando execução |
| CNES — leitos | `https://apidadosabertos.saude.gov.br/assistencia-a-saude/cnes-leitos?co_ibge=430460` | Leitos existentes e SUS, conforme campos e competência retornados | Adaptador experimental; somente após validação |
| DEMAS dengue | `https://apidadosabertos.saude.gov.br/arboviroses/dengue?id_municip=430460&nu_ano=2025` | Número de registros de notificação no município notificante, por ano | Adaptador experimental; somente após validação |
| SIA produção ambulatorial | `https://apidadosabertos.saude.gov.br/assistencia-a-saude/sia-procedimentos-ambulatoriais?co_ibge=430460&nu_ano=2025` | Quantidade de procedimentos **se a coluna estiver presente** | Adaptador experimental; somente após validação |
| SIH produção hospitalar | `https://apidadosabertos.saude.gov.br/assistencia-a-saude/sih-procedimentos-hospitalares?co_ibge=430460&nu_ano=2025` | Produção hospitalar/AIHs **se houver coluna identificável** | Adaptador experimental; somente após validação |

**Documentação oficial da API:** https://apidadosabertos.saude.gov.br/static/swagger.json  
**Catálogo:** https://dadosabertos.saude.gov.br/  
**DATASUS:** https://datasus.saude.gov.br/  
**SES/RS (referência de comparação):** http://bipublico.saude.rs.gov.br/  
**GeoCanoas:** https://geo.canoas.rs.gov.br/  
**Relatórios municipais:** https://www.canoas.rs.gov.br/

**Não integrados nesta primeira versão:** SIM (mortalidade), SINASC (nascidos vivos), SINAN por agravo além da API de dengue, SIOPS (financiamento), cobertura vacinal, causas detalhadas por CID-10, pirâmide etária, bairros GeoCanoas e limites oficiais. Foram deliberadamente deixados fora da carga automática porque não foi possível validar um fluxo leve e reprodutível para eles. O layout e a estrutura de arquivos suportam extensões futuras.

## Interpretação epidemiológica e limitações

- **IBGE:** 4304606 é o código de **sete dígitos**. Algumas APIs federais requerem **430460**, com seis dígitos. O script tenta validar o município em cada registro CNES.
- **CNES:** cadastro de estabelecimentos não equivale necessariamente a oferta assistencial SUS. Os dados podem conter unidades privadas. O mapa só mostra coordenadas públicas plausíveis para Canoas; a contagem CNES inclui registros sem coordenadas.
- **Classificação UBS/hospital:** derivação aproximada pelo texto do tipo CNES, não indicador de cobertura da Atenção Primária.
- **CNES leitos:** somatórios por competência devem distinguir total existente e leitos SUS; **não** deduzir leitos pelo nome hospital.
- **Dengue:** registros do município **notificante** não são taxa de incidência entre residentes nem necessariamente casos confirmados. Não calcular incidência com esses valores sem metodologia.
- **SIA e SIH:** produção de procedimentos/AIHs não é contagem de pacientes únicos, nem necessariamente de internações de moradores de Canoas. Não rotular esses números como internações únicas.
- **Ano de referência:** o dashboard identifica competência ou ano quando disponível. Não se deve aplicar ano de notificações aos estabelecimentos CNES (fotografia de competência diferente).
- **Segurança:** o repositório contém somente agregados e informações públicas de estabelecimentos. Nunca publique dados individuais de pacientes, CPF, CNS ou endereços residenciais.
- **Resiliência:** falhas de fonte preservam os números anteriores e indicam status/nota de coleta. O Python não publica dados de páginas parcialmente carregadas de um mesmo indicador.
- **Georreferenciamento:** coordenadas inválidas/ausentes não são geocodificadas por aproximação.

## Estrutura

```text
webgis-saude-canoas/
├── .github/workflows/update-data.yml  # atualização + build + Pages
├── public/
│   ├── assets/favicon.svg
│   └── data/
│       ├── summary.json               # indicadores agregados e proveniência
│       └── establishments.geojson      # pontos públicos georreferenciados
├── scripts/update_data.py             # coletor Python; sem pandas
├── src/
│   ├── main.ts                         # páginas, filtros, mapas, gráficos
│   ├── style.css                       # Tailwind e componentes
│   └── lib/                            # tipos, leitura, utilitários
├── tests/test_data.py
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

## Executar localmente e testar

Requisitos: Node.js 22+, npm e Python 3.12+. Com acesso às dependências do npm:

```bash
npm install
npm run dev
npm run build
python -m unittest discover -s tests -v
python scripts/update_data.py
```

Os assets são copiados de `public/` para `dist/`. O `base: './'` do Vite permite hospedagem sob o nome do repositório. Não abra `index.html` diretamente com `file://` sem passar pelo Vite/build. Para economizar chamadas nos conjuntos mais extensos, o coletor aceita `SKIP_HEAVY=true` (pula SIA/SIH/dengue), `DATA_YEARS=2025,2026` e `MAX_PAGES_PER_SERIES=160`. Se o volume exceder o limite configurado, o indicador **não será publicado parcialmente**.

### Integridade e qualidade

`python -m unittest discover -s tests -v` verifica contrato JSON/GeoJSON, município, coordenadas, classificação e campos ausentes. O build executa `tsc --noEmit`, além da compilação Vite. Para validação real de mapa e responsividade em celulares, testar também no navegador após o primeiro deploy, pois tiles e APIs exigem acesso à rede externa. Verifique erros no console caso haja restrições de WebGL ou de acesso aos servidores de mapas.

## Logo institucional GeoCanoas

O portal GeoCanoas referencia `assets/img/profile/GEOCANOAS_Vetorizado2.webp`. O cabeçalho tenta carregar primeiro `public/assets/geocanoas-oficial.webp` e depois a URL do próprio portal `https://geo.canoas.rs.gov.br/assets/img/profile/GEOCANOAS_Vetorizado2.webp`. O coletor tenta copiar **os bytes originais** do site institucional para o repositório durante as atualizações. **No ZIP não há logotipo local**, pois o arquivo original não pôde ser obtido/validado nesta execução. Se a imagem remota não estiver pública ou bloquear hotlink, solicite o arquivo à equipe GeoCanoas e adicione o original a `public/assets/geocanoas-oficial.webp`. Não foi criada logo falsificada.

## Roadmap da versão ampliada

Adaptadores oficiais SIM/SINASC e SIH por município de residência (sem microdados expostos); incidência e mortalidade ajustadas por população/idade; séries longas, cobertura vacinal/APS com definição correta; SIOPS, RAG e PMS com data de referência; territorialização por bairros GeoCanoas, limite municipal e coropletas normalizadas; comparação regional com indicadores padronizados; auditoria CI, snapshots versionados, alertas de falha e testes E2E Playwright em múltiplos breakpoints.

### Licenciamento

Código sob licença MIT (`LICENSE`). Fontes de dados e logomarcas continuam sob os respectivos termos de uso; confira a licença e as atribuições de cada fornecedor.
