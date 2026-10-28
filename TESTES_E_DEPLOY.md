# Verificação, testes e publicação — WebGIS Saúde Canoas

**Revisão:** 28/10/2026 · **Versão:** 1.5.0

O material anterior de 16/10/2026 documentava restrições de ambiente anteriores à implantação. Hoje o repositório tem acesso de escrita, pipeline de atualização e deploy funcional no GitHub Pages. Para informações gerais, consulte o [README principal](./README.md).

## CI e publicação

1. O workflow [Verificar, atualizar dados e publicar](./.github/workflows/update-data.yml) roda testes Python, processa snapshots quando necessário e compila/publica o frontend na branch `main`. Em `pull_request`, somente a verificação roda; coleta e publicação ficam desligadas.
2. O workflow [Homologação automatizada de UX](./.github/workflows/ux-smoke.yml) compila a aplicação e testa navegação em Chromium headless. Executa em pushes relevantes e pull requests; gera capturas disponíveis nos artefatos da execução.
3. O Pages está configurado para a URL [https://marcianolima.github.io/webgis-saude-canoas/](https://marcianolima.github.io/webgis-saude-canoas/). A execução da Action de publicação deve apresentar a etapa de deploy aprovada. Não interpretar apenas o sucesso da coleta como confirmação de todas as séries: cada fonte possui status individual.

### Testes executados no fechamento de 28/10/2026

- Suite Python: **79 testes aprovados** no workflow do pull request de fechamento, após correção de um teste estrutural que não reconhecia aspas na rota `farmacia-siaps`.
- Homologação Chromium: **13 páginas em cada largura de 360, 390 e 768 px**, e verificação desktop em **1280 px**. Inclui abertura e fechamento do menu, página ativa à esquerda, Escape, foco no drawer, `inert` no conteúdo de fundo, overflow horizontal e persistência do tema.
- A PR [#2](https://github.com/marcianolima/webgis-saude-canoas/pull/2) foi incorporada em `main` após pipelines de pull request aprovados. O workflow de publicação do merge [40626858933](https://github.com/marcianolima/webgis-saude-canoas/actions/runs/40626858933) e o de UX [40626858932](https://github.com/marcianolima/webgis-saude-canoas/actions/runs/40626858932) terminaram com sucesso.

## Como reproduzir localmente

```bash
npm install
python -m unittest discover -s tests -v
npm run build
npm run preview
```

Para executar o smoke test com Playwright/Chromium:

```bash
npm install --no-save playwright@1.56.1
npx playwright install chromium
node scripts/smoke-mobile.cjs
```

Aplique as dependências de sistema do Chromium conforme seu ambiente. O smoke inicia e encerra o preview Vite automaticamente. Consulte os logs da Action para diagnóstico de build, downloads ou fontes incompletas.

## Limites da homologação

Testes automatizados **não substituem** inspeção com leitores de tela, usuários reais e dispositivos físicos; não homologam a semântica epidemiológica das origens. O catálogo SIAPS/BNAFAR e as quatro novas fontes oficiais não possuem séries municipais validadas. SIH e SIA possuem competências faltantes; a aplicação não as interpreta como zero. A comparação territorial por bairros cadastrados no CNES também não equivale à validação contra limites oficiais.
