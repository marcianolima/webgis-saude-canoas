# WebGIS Saúde Canoas — coleta CNES por arquivo diário (v1.3)

## Diagnóstico confirmado no GitHub

- A execução **38992904954** terminou com sucesso, mas o **CNES continuou sem estabelecimentos**.
- O endpoint `/assistencia-a-saude/cnes-estabelecimentos?co_ibge=430460&nu_comp=...` retornou **uma linha por competência**. Essa rota é inadequada para extrair o inventário municipal completo.
- `public/data/establishments.geojson` permanece como coleção vazia; os dados de leitos atuais não atingiram o limiar de validação e devem permanecer indisponíveis.

## O que mudou nesta atualização

1. `scripts/update_data.py` passa a baixar o **CSV diário nacional oficial do CNES**, disponível no catálogo [Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude), no job do GitHub Actions. Não é necessário backend próprio.
2. O arquivo ZIP nacional é processado **localmente no runner**, com leitura gradual das linhas; nenhum arquivo original de âmbito nacional é gravado no repositório.
3. Seleciona registros com `CO_MUNICIPIO_GESTOR=430460` e `CO_MOTIVO_DESAB` vazio, deduplica por `CO_CNES` e gera apenas os agregados de Canoas.
4. Classifica estabelecimentos usando `TP_UNIDADE` e nomes de tipo, normaliza coordenadas WGS84 e descarta pontos sem localização plausível. Mantém o total de estabelecimentos mesmo que alguns não tenham coordenadas.
5. Falha de download, CSV inesperado ou cobertura insuficiente: **não apaga dados anteriores nem inventa quantidades**. Na aba *Actions*, aparecem avisos se CNES ou leitos não tiverem resultado validado.
6. O frontend e as configurações de mapa não são alterados.

## Como enviar pelo computador

1. Extraia este ZIP **sobre a raiz do repositório**, preservando `.git`, `src/` e `public/data/`.
2. Confirme a presença destes arquivos:
   - `scripts/update_data.py`
   - `tests/test_pipeline.py`
   - `.github/workflows/update-data.yml`
3. Execute, se tiver Python 3.12: `python -m unittest discover -s tests -v`.
4. Commit e push na branch `main`.
5. O push executará a coleta inicial porque o CNES ainda tem status `error`. No GitHub, verifique `Actions > Verificar, atualizar dados e publicar WebGIS Saúde`.
6. Se não houver coleta, use **Run workflow**, com a branch `main`.

### O que deve aparecer no log, se funcionar

```
CNES: ZIP nacional baixado, ... MiB
CNES CSV: codificação detectada ...
CNES CSV: ... registros nacionais; ... em Canoas; ... desabilitados; ... ativos únicos
Atualização: ... fonte(s) concluída(s)
```

Confira os arquivos `public/data/summary.json` (`sourceInfo.cnes.status = ok`, `facilities.total`, `facilities.withCoordinates`) e `public/data/establishments.geojson` (`features` não vazio). Atualize o site com Ctrl+F5.

**Atenção à escala:** o arquivo diário é um retrato, não uma série histórica por competência. Totais de estabelecimentos não equivalem a estabelecimentos do SUS, nem necessariamente a unidades administradas pelo município.

**Fonte principal do ZIP:**
`https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_csv.zip`

## Estado de verificação

- 25 testes Python passaram, inclusive processamento de ZIP/CSV sintético e teste ponta a ponta com respostas simuladas.
- A consulta externa ao ZIP oficial **não foi executada aqui**, por restrição de rede. A primeira Action com este patch confirmará a estrutura efetiva do arquivo, conexão S3, status territorial e números do mapa.
- **Leitos:** a API de leitos continua retornando amostra insuficiente para uma contagem municipal. Mantemos os quantitativos indisponíveis até integrar fonte completa por competência, sem reaproveitar o número inválido de 21.
- **Dengue/SIA/SIH:** continuam dependendo de coleta manual/agendada e validação semântica; não devem ser apresentados como zeros enquanto vazios.
