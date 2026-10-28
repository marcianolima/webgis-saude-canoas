# WebGIS Saúde Canoas — leitura inicial (versão 1.5.0)

> **Documento vigente em 28/10/2026.** As anotações antigas sobre CNES vazio, mapa sem feições e impossibilidade de escrever no GitHub foram superadas e não representam a aplicação atual.

Acesse o [painel publicado](https://marcianolima.github.io/webgis-saude-canoas/) e consulte o [README](./README.md) para arquitetura, funcionalidades, referências, indicadores e limitações. A versão 1.5.0 reúne 13 páginas temáticas acessíveis por menu agrupado, com foco no uso em dispositivos móveis.

## Estado verificado

| Tema | Retrato de 27/10/2026 |
| --- | --- |
| CNES | 971 estabelecimentos ativos; 964 com coordenadas publicadas |
| UBS e unidades hospitalares | 35 UBS e 6 unidades classificadas como hospitalares pelo tipo CNES |
| Leitos | 668 existentes e 539 SUS; competência 09/2026 |
| SIH e SIA | Cobertura parcial: respectivamente 15 e 12 meses validados de 21 solicitados |
| BNAFAR e SIAPS atuais | Fontes documentadas; sem indicador municipal homologado no painel |
| PIAPS-RS, SRAG, PNI 2026, SISAGUA | Catalogadas como fontes oficiais adicionais; séries municipais ainda não integradas |

## Para quem desenvolve

```bash
npm install
python -m unittest discover -s tests -v
npm run build
npm run dev
```

Requer Node.js 22+ e Python 3.12+. O CI executa os testes no [workflow de atualização e deploy](./.github/workflows/update-data.yml) e verifica a navegação com Chromium no [workflow de UX](./.github/workflows/ux-smoke.yml). Confira o relatório das execuções na [aba GitHub Actions](https://github.com/marcianolima/webgis-saude-canoas/actions).

**Importante:** a extração de microdados individuais ocorre somente no runner de coleta. Arquivos públicos são agregados e cadastros CNES, sem identificação de pacientes. Informações indisponíveis não equivalem a zero. O painel é demonstrativo, não oficial da SMS, e não substitui os sistemas do SUS.
