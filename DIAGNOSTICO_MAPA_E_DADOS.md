# Diagnóstico do mapa e cobertura — histórico e situação atual

**Atualizado em:** 28/10/2026 · **Versão:** 1.5.0

## Histórico corrigido

Em 17/10/2026 o mapa e o cadastro CNES ainda estavam vazios. Os registros originais deste diagnóstico descreviam aquele estágio do desenvolvimento: o endpoint agregado consultado não entregava o inventário municipal e a coleta inicial não havia sido concluída. Esse problema **foi resolvido** no pipeline posterior usando o CSV nacional oficial do CNES, processado no runner do GitHub Actions, com seleção municipal, deduplicação, classificação por tipologia e validação de coordenadas.

## Estado vigente (snapshot de 27/10/2026)

- `public/data/summary.json`: **971** registros CNES ativos; **964** com coordenadas e **7** sem posição; 35 UBS e 6 tipologias hospitalares.
- `public/data/establishments.geojson`: pontos georreferenciados para exibição no mapa.
- `public/data/facilities.json`: catálogo integral dos estabelecimentos, inclusive os sem coordenadas.
- Leitos: **668 existentes / 539 SUS**, competência **202609**.
- Mapa: **MapLibre** com estilo vetorial público OpenFreeMap sem API key, alternativa **Leaflet** em falha de WebGL ou tiles.

O mapa e o catálogo incluem estabelecimentos privados e públicos. A quantidade CNES não equivale ao número de equipamentos municipais. Bairros informados no CNES apresentam variantes ortográficas e **não estão automaticamente normalizados contra a malha oficial GeoCanoas**. Não calcular cobertura territorial oficial com base exclusivamente nas grafias cadastrais.

## Pontos de atenção ainda vigentes

1. SIH e SIA possuem arquivos e competências não processados: a ferramenta distingue cobertura parcial de ausência de produção.
2. A integração municipal homologada do SIAPS, BNAFAR, SRAG, PIAPS, PNI 2026 e SISAGUA ainda depende de extrações, critérios epidemiológicos e testes de qualidade.
3. A interpretação dos indicadores respeita unidade, recorte territorial, competência, dado preliminar e incertezas. Microdados pessoais não são expostos no frontend.
4. A homologação automatizada foi executada em Chromium para telas móveis e desktop. Testes com pessoas e aparelhos físicos permanecem recomendados.

Consulte o [README](./README.md) para os detalhes e o [catálogo de fontes no aplicativo](https://marcianolima.github.io/webgis-saude-canoas/). As capturas do navegador e os logs são publicados na [aba Actions](https://github.com/marcianolima/webgis-saude-canoas/actions).
