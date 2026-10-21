# Integração BNAFAR e SIAPS — WebGIS Saúde Canoas

## Situação atual (21/10/2026)

- **Página nova: Farmácia e SIAPS**, dentro do grupo *Saúde e atendimento*, com identidade mobile-first, acesso às publicações e avisos metodológicos.
- **Catálogo de fontes**, `public/data/farmacia_siaps.json`, integrado à tela *Fontes e metodologia*.
- **Monitor de publicações Qualifar-SUS**, `scripts/farmacia_siaps.py`, executado pelo GitHub Actions e capaz de descobrir a planilha XLSX mais recente publicada em `https://bnafar.github.io/statusenvio/`.
- **Sem números fabricados:** indicadores municipais permanecem indisponíveis até que a extração de Canoas seja validada. `partial` significa publicação encontrada, mas **não** cobertura municipal confirmada.

## Fontes e limitações

### 1. BNAFAR — status mensal de envio

- Catálogo: https://bnafar.github.io/statusenvio/
- Painel municipal: https://lookerstudio.google.com/reporting/9f4ae971-614c-4d68-98e2-9aef9df915d2
- Publicação: mensal; apresentação via Looker Studio.
- Interpretação: *situação de envio de dados*, **não** quantidade de medicamentos em estoque, atendimentos ou dispensações.
- Pendente: obter CSV municipal oficial ou endpoint público estável e conferir chave IBGE 4304606, competências e semântica de cada status antes de incorporar ao gráfico.

### 2. Qualifar-SUS — monitoramento de envios

- Repositório público: https://github.com/bnafar/statusenvio
- Planilhas: `arquivos/qualifarsus/ciclo_0N_AAAA/*.xlsx`
- Monitoramento: publicação semanal, em ciclos de aproximadamente três meses, com histórico de versões.
- Coleta automatizada implementada: descobre a URL e a data da planilha mais recente, rejeita hosts/URLs fora do padrão e preserva o último registro quando a fonte estiver indisponível.
- Pendente: revisar o dicionário de campos e extrair somente o registro municipal de Canoas com validação do status. Não pressupor que o município conste da planilha nem inferir regularidade caso não conste.

### 3. SIAPS — Atenção Primária atual

- Consulta pública: https://siaps.saude.gov.br/publico
- Manual: https://sisaps.saude.gov.br/sistemas/siaps/docs/manual/utilizando-sistema/
- Relatórios públicos: https://relatorioaps.saude.gov.br/
- Informação: cofinanciamento APS, componente de qualidade das equipes, acompanhamento territorial e práticas assistenciais.
- Exportações disponibilizadas pela interface: CSV/XLSX, sujeitas aos filtros do relatório e às competências.
- Pendente: coletar uma exportação oficial pública de Canoas e validar cabeçalho, INE/CNES, tipo de equipe, numerador, denominador, período, unidade e eventual supressão estatística. A consulta web não constitui uma API pública documentada; não automatizar endpoints privados nem autenticação de gestor.
- Atenção: o histórico `aps.json` (Previne Brasil) termina em 2024 e **não** deve ser emendado à série SIAPS sem série e metodologia compatíveis.

## Critérios para incorporar séries

1. Obter tabela municipal pública com filtro e código IBGE 4304606; não carregar dados de pessoas ou registros de pacientes.
2. Identificar competência e definição técnica verificáveis; usar `null` para lacunas, nunca 0 por falta de resultado.
3. Validar desduplicação municipal, universo, agregação, unidades, numerador e denominador.
4. Documentar URL do recurso, carimbo de coleta, referência e status `ok` após homologação.
5. Publicar `series[id]=[{period, value}, ...]` apenas para indicadores homologados, preservando os períodos anteriores quando a fonte falhar.
6. Não reproduzir dados pessoais, credenciais ou tabelas clínicas identificáveis no GitHub Pages.

## Execução

```bash
python scripts/farmacia_siaps.py
python -m unittest tests/test_farmacia_siaps.py
npm run build
```

O script não necessita de bibliotecas Python adicionais e não modifica o arquivo quando a versão da planilha permanece igual. No `update-data.yml`, ele executa com falha tolerada, sem interromper o site quando o catálogo externo estiver indisponível.
