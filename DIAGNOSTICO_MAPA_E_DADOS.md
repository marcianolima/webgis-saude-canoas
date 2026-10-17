# Diagnóstico: indicadores vazios e mapa (17/10/2026)

## O que foi observado no GitHub

- O snapshot publicado no repositório (`public/data/summary.json`) estava com `facilities.total: null`, CNES `status: not_loaded`, e séries dengue, SIH e SIA vazias.
- `public/data/establishments.geojson` continha **zero** feições. Não há como mostrar pontos CNES até ocorrer uma coleta oficial válida.
- No workflow antigo, `update` usava `if: github.event_name != 'push'`. Logo, os uploads do usuário publicavam a aplicação, mas **não executavam a coleta de dados**. Ela só rodaria manualmente ou por cron.
- O mapa original usava MapLibre com tiles CARTO e um serviço de glyphs/fontes externo; sem WebGL ou com falha nesses serviços poderia aparecer vazio. **Não foi possível inspecionar o console do navegador do usuário nem validar o acesso às URLs de tiles pelo ambiente de testes**, portanto a falha exata do mapa-base ainda não está confirmada.

## Ajustes desta atualização

1. Em um `push`, **se o CNES ainda não estiver disponível**, executa-se uma coleta inicial para popular o mapa. Em `push` com CNES existente, não há novas chamadas à API. `workflow_dispatch` e `schedule` executam coleta completa.
2. O job não derruba o site se uma API externa falhar; preserva snapshots válidos anteriores, gera relatório por fonte e continua a publicação. Erros ficam registrados no log e na página *Sobre os dados*.
3. MapLibre permanece como primeira opção. Adiciona-se tratamento de erros e um fallback para **Leaflet**, com tiles OSM em caso de erro de WebGL, raster ou glyphs. O mapa exibe aviso de contingência se as duas alternativas falharem. A biblioteca alternativa é carregada somente quando necessária.
4. São exibidos avisos explícitos quando a camada CNES ainda não tiver sido carregada. Indicadores indisponíveis continuam exibidos como `—`, não `0` fictício.
5. Séries anuais preservam os anos válidos se um outro ano falhar, marcando o indicador como `partial` quando apropriado.

## Instalação no repositório existente

### Atualização mínima (recomendada)

Extraia o arquivo `webgis-saude-canoas-patch.zip` na pasta raiz do clone local, substituindo os arquivos com mesmo nome. No GitHub Desktop, verifique se aparecem os arquivos abaixo. Depois faça `Commit to main` e `Push origin`:

- `.github/workflows/update-data.yml`
- `scripts/update_data.py`
- `src/main.ts`
- `src/lib/leafletFallback.ts` (arquivo novo)
- `tests/test_pipeline.py`

**Não exclua a pasta `.git` e não substitua seus JSONs oficiais já coletados.** O patch não contém dados `public/data/`.

### Atualização completa

Caso prefira atualizar tudo, use `webgis-saude-canoas-ajustado.zip`, mas **não copie os arquivos de `public/data/` sobre dados de produção já atualizados**. Preserve a pasta `.git` do clone. O pacote completo contém amostras iniciais sem os registros CNES.

## Executar e verificar

1. No GitHub, abra **Actions → Verificar, atualizar dados e publicar WebGIS Saúde → Run workflow → main → Run workflow**. [Abrir workflow](https://github.com/marcianolima/webgis-saude-canoas/actions/workflows/update-data.yml).
2. Aguarde os jobs `verify`, `update` e `deploy`. No job `update`, abra a etapa `Atualizar dados públicos de saúde` e analise erros/avisos.
3. Veja a seção **Summary** do workflow: cada fonte terá `status`, `records` e `reference`.
4. Confira se `public/data/summary.json` passou a ter `sourceInfo.cnes.status = "ok"` e `facilities.total` numérico; se sim, `public/data/establishments.geojson` deve conter uma coleção de pontos.
5. No site [GitHub Pages](https://marcianolima.github.io/webgis-saude-canoas/), atualize forçando recarga (Ctrl+F5) e confira mapa-base, clusters e pop-up.
6. Se `update` apresentar alerta, copie **somente as linhas de erro e de aviso** (sem credenciais) para diagnóstico. Se o mapa-base continuar branco, abra F12 → Console / Network e envie os erros de `maplibre`, `cartocdn`, `openstreetmap` ou `glyph` e uma captura da área do mapa.

## Limitações da validação

- Os testes Python passaram (17), e foi feita verificação estática TypeScript com módulos externos simulados.
- O ambiente não obteve conexão ao registry npm nem às URLs de tiles e às APIs DEMAS: o build real, a integração em rede e o teste visual precisam ocorrer no GitHub Actions/navegador.
- Fontes oficiais podem continuar retornando dados parciais ou erros de API. Nunca publicar quantidades inferidas a partir de ausência de resposta.
