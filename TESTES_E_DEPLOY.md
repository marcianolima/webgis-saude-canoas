# Testes, correções e publicação — WebGIS Saúde Canoas

Revisão: 16/10/2026. Repositório de destino: https://github.com/marcianolima/webgis-saude-canoas

## 1. Procedimento de atualização no computador

**Recomendado: GitHub Desktop.** Clone o repositório, extraia o ZIP em outra pasta e
copie **todos** os arquivos extraídos para a pasta clonada, inclusive `.github` e
`.gitignore`. Preserve a pasta `.git` que já existe no clone. No GitHub Desktop,
revise as alterações, faça `Commit to main` e depois `Push origin`.

**Alternativa pelo terminal Git Bash / Linux / macOS:**

```bash
git clone https://github.com/marcianolima/webgis-saude-canoas.git webgis-saude-canoas-repo
# copie o conteúdo deste ZIP (incluindo .github) para a pasta clonada,
# substituindo os arquivos de mesmo nome e sem excluir .git
cd webgis-saude-canoas-repo
python -m unittest discover -s tests -v
npm install
npm run build
git add -A
git commit -m "fix: corrigir dados, frontend e deploy"
git push origin main
```

No Windows PowerShell, depois de extrair o ZIP e clonar o repositório na mesma pasta:

```powershell
# Execute dentro da pasta em que estão os dois diretórios:
#  - webgis-saude-canoas          (extraído deste ZIP)
#  - webgis-saude-canoas-repo     (clonado com git)
Get-ChildItem -Force .\webgis-saude-canoas | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination .\webgis-saude-canoas-repo -Force -Recurse
}
Set-Location .\webgis-saude-canoas-repo
python -m unittest discover -s tests -v
npm install
npm run build
git add -A
git commit -m "fix: corrigir dados, frontend e deploy"
git push origin main
```

Caso `git commit` informe que não há alterações, não é um erro.

## 2. Configuração do GitHub Pages

1. No repositório, confira se existe **`.github/workflows/update-data.yml`**.
   A pasta `.github` é oculta em alguns gerenciadores de arquivos.
2. **Settings → Pages → Build and deployment → Source → GitHub Actions**.
3. **Settings → Actions → General → Workflow permissions → Read and write permissions**.
4. **Actions → Verificar, atualizar dados e publicar WebGIS Saúde → Run workflow**.
5. Aguarde os jobs `verify`, `update` e `deploy`. Inspecione os erros caso ocorram.
6. URL esperada após o sucesso: https://marcianolima.github.io/webgis-saude-canoas/

## 3. Resultado dos testes locais

| Verificação | Resultado |
|---|---|
| Estrutura JSON e GeoJSON inicial | Aprovada |
| Testes Python (incluindo integração com respostas simuladas) | **16 aprovados** |
| Sintaxe dos arquivos TypeScript | Aprovada |
| Checagem TypeScript `strict` com declarações locais temporárias para dependências externas | Aprovada; não substitui checagem com bibliotecas npm reais |
| Sintaxe e estrutura do YAML GitHub Actions | Aprovada |
| Referências de paginação/competência conferidas na documentação DEMAS | Conferidas |
| `npm install` com dependências reais | **Bloqueado — ambiente sem resolução DNS para npm** |
| `npm run build` real | **Pendente de instalação npm** |
| Coleta real IBGE/CNES/SIA/SIH/dengue | **Pendente de execução online** |
| Teste visual responsivo/WebGL no browser com bundle | **Pendente de build** |
| Publicação remota na conta | **Bloqueada — integração GitHub retorna HTTP 403 em escrita** |

**IMPORTANTE:** snapshots sintéticos usados nos testes nunca foram incorporados
em `public/data/`. O pacote conserva o JSON original, com indicadores não
integrados explicitamente marcados como indisponíveis.

## 4. Diagnóstico após o primeiro workflow

- `verify` vermelho: identificar o teste falho nos logs; não forçar deploy.
- `update` vermelho: checar endpoints, DNS e limites da API. Como a coleta é
  segmentada, alguns indicadores podem atualizar mesmo se outros falharem.
- `deploy` vermelho em `npm install`: conferir acesso ao registro npm.
- `deploy` vermelho em `npm run build`: copiar o log TypeScript/Vite; corrigir e comitar.
- `deploy` vermelho em `deploy-pages`: conferir **Settings → Pages** e permissões
  de Actions; conferir restrições de ambientes do repositório.
- Site abre, mas mapa vazio: consulte `public/data/establishments.geojson`
  e `public/data/summary.json` no branch principal; veja `sourceInfo.cnes.status`.
- Mapa sem base: inspecione no navegador se os tiles da CARTO e o WebGL
  estão disponíveis (rede e aceleração gráfica).
