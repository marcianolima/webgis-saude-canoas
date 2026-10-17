#!/usr/bin/env python3
"""WebGIS Saúde Canoas v1.0: extração territorial AGREGADA de SINAN, SIM e SINASC.

Os arquivos nacionais são processados somente no runner temporário. NUNCA salvar
registros individuais em public/, repositório, logs ou artefatos do Actions.
"""
import csv, io, json, logging, os, re, tempfile, zipfile
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/data/indicators.json'
LOG=logging.getLogger('webgis.health')
CITY={'430460','4304606'}
S3='https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br'
CONFIG={
 'dengue':{
   'title':'Notificações de dengue (residentes)','catalog':'https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue',
   'years':{
      2025:S3+'/SINAN/Dengue/csv/DENGBR25.csv.zip',
      2026:S3+'/SINAN/Dengue/csv/DENGBR26.csv.zip'},
   'municipality':'ID_MN_RESI','required':('ID_MN_RESI','NU_ANO','CLASSI_FIN'),
   'method':'Notificações registradas no SINAN de residentes de Canoas, independentemente da classificação final. Não equivalem a casos confirmados.'
 },
 'sinasc':{
   'title':'Nascidos vivos de mães residentes','catalog':'https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc',
   'years':{
      2024:S3+'/SINASC/csv/SINASC_2024_csv.zip',
      2025:S3+'/SINASC/csv/SINASC_2025_csv.zip'},
   'municipality':'CODMUNRES','required':('CODMUNRES','SEXO','PARTO'),
   'method':'Declarações de nascidos vivos no SINASC por município de residência materna. 2025 é preliminar.'
 },
 'sim':{
   'title':'Óbitos não fetais de residentes','catalog':'https://dadosabertos.saude.gov.br/dataset/sim',
   'years':{
      2024:S3+'/SIM/csv/DO24OPEN_csv.zip',
      2025:S3+'/SIM/csv/Mortalidade_Geral_2025_csv.zip'},
   'municipality':'CODMUNRES','required':('CODMUNRES','TIPOBITO','CAUSABAS'),
   'method':'Óbitos não fetais no SIM por município de residência. Exclui óbitos fetais (TIPOBITO=1). 2025 é preliminar.'
 }
}
ADDITIONAL={
 'sia':('Produção ambulatorial (SIA/SUS)','https://apidadosabertos.saude.gov.br/','API testada: resposta limitada a uma linha por consulta; cobertura municipal não comprovada.'),
 'sih':('Produção hospitalar (SIH/SUS)','https://apidadosabertos.saude.gov.br/','API testada: resposta limitada a uma linha por consulta; cobertura municipal não comprovada.'),
 'chikungunya':('Febre de chikungunya','https://dadosabertos.saude.gov.br/dataset/arboviroses-febre-de-chikungunya','Fonte anual identificada; conexão municipal ainda não validada nesta versão.'),
 'zika':('Vírus Zika','https://dadosabertos.saude.gov.br/dataset/arboviroses-zika-virus','Fonte anual identificada; conexão municipal ainda não validada nesta versão.'),
 'pni':('Vacinação (PNI/RNDS)','https://opendatasus.saude.gov.br/','Arquivos mensais volumosos; sem denominador e método municipal validados, nenhuma cobertura é estimada.'),
 'aps':('Atenção Primária (e-SUS APS/PEC)','https://sisab.saude.gov.br/','Dados clínicos locais exigem integração institucional autorizada; não são dados públicos exportáveis automaticamente.')
}

def utcnow():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def municipal(value):
    if value is None:return False
    return re.sub(r'[^0-9]','',str(value).split('.')[0]) in CITY

@contextmanager
def read_zip_csv(url):
    """Itera CSV em modo streaming e retorna linhas durante o contexto."""
    with tempfile.TemporaryDirectory(prefix='webgis-health-') as folder:
        filename=Path(folder)/'source.zip'
        req=Request(url,headers={'User-Agent':'WebGIS-Saude-Canoas/1.0 (dados publicos)'})
        with urlopen(req,timeout=200) as source,filename.open('wb') as dest:
            n=0
            while True:
                block=source.read(1024*1024)
                if not block:break
                n+=len(block)
                if n>150*1024*1024:raise ValueError('ZIP ultrapassa limite de 150 MiB')
                dest.write(block)
        if not zipfile.is_zipfile(filename):raise ValueError('Fonte não é ZIP')
        with zipfile.ZipFile(filename) as archive:
            candidates=[m for m in archive.infolist() if m.filename.lower().endswith('.csv') and not m.is_dir()]
            if len(candidates)!=1:raise ValueError('Número inesperado de tabelas CSV')
            info=candidates[0]
            if info.file_size>1600*1024*1024:raise ValueError('CSV excede limite de segurança')
            with archive.open(info) as raw:
                header_bytes=raw.peek(32768)[:32768]
                try:header_bytes.decode('utf-8-sig');enc='utf-8-sig'
                except UnicodeDecodeError:enc='latin-1'
                stream=io.TextIOWrapper(raw,encoding=enc,errors='replace',newline='')
                head=stream.readline()
                if not head:raise ValueError('CSV vazio')
                sep=';' if head.count(';')>head.count(',') else ','
                fields=[col.strip().lstrip('\ufeff').upper() for col in next(csv.reader([head],delimiter=sep))]
                if len(fields)<5 or len(fields)!=len(set(fields)):raise ValueError('Cabeçalho de CSV inválido')
                rows=csv.DictReader(stream,fieldnames=fields,delimiter=sep)
                yield fields,rows

def aggregate(rows,kind,year,fields):
    spec=CONFIG[kind]
    expected=set(spec['required'])
    if not expected.issubset(fields):raise ValueError('Colunas obrigatórias ausentes: '+str(sorted(expected-set(fields))))
    scanned=0; city_count=0; classes={}; fetal=0
    for r in rows:
        scanned+=1
        if not municipal(r.get(spec['municipality'])):continue
        if kind=='dengue':
            observed=str(r.get('NU_ANO') or '').strip()
            if observed and observed!=str(year):continue
        if kind=='sim' and str(r.get('TIPOBITO') or '').strip()!='2':
            fetal+=1
            continue
        city_count+=1
        if kind=='sinasc':
            sex=str(r.get('SEXO') or '').strip()
            delivery=str(r.get('PARTO') or '').strip()
            if sex in ('1','2'):classes['sexo_'+('masculino' if sex=='1' else 'feminino')]=classes.get('sexo_'+('masculino' if sex=='1' else 'feminino'),0)+1
            if delivery in ('1','2'):classes['parto_'+('vaginal' if delivery=='1' else 'cesarea')]=classes.get('parto_'+('vaginal' if delivery=='1' else 'cesarea'),0)+1
    if scanned<10000:raise ValueError('Extrato nacional inesperadamente pequeno; rejeitado')
    if kind in ('sinasc','sim') and city_count<100:raise ValueError('Cobertura municipal insuficiente no extrato anual')
    if kind=='dengue' and city_count<0:raise ValueError('Indicador inválido')
    return {'year':year,'value':city_count,'scanned':scanned,'breakdown':classes,'residence':True,'provisional':year>=2025 if kind in ('sinasc','sim') else year==datetime.now(timezone.utc).year}

def blank():
    return {'schemaVersion':'1.0','updatedAt':None,'series':{key:[] for key in CONFIG},'sources':{},'definitions':{k:v['method'] for k,v in CONFIG.items()}}
def load():
    if OUT.exists():
        try:
            data=json.loads(OUT.read_text(encoding='utf-8'))
            if isinstance(data.get('series'),dict) and isinstance(data.get('sources'),dict):return data
        except (OSError,ValueError,AttributeError):pass
    return blank()
def check_consistency(kind,entry):
    if entry['year'] not in CONFIG[kind]['years']:raise ValueError('Ano fora do recurso selecionado')
    if entry['value']<0 or entry['value']>entry['scanned']:raise ValueError('Agregado inconsistente')
    if kind=='sinasc' and sum(entry['breakdown'].get('sexo_'+sex,0) for sex in ('masculino','feminino'))>entry['value']:
        raise ValueError('Subtotais de nascidos vivos inconsistentes')
def save_atomic(data):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUT.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temp,OUT)

def run():
    data=load()
    successes=0
    force=os.getenv('HEALTH_FORCE','').lower()=='true'
    for kind,spec in CONFIG.items():
        success_this_source=0
        old={int(r['year']):r for r in data.get('series',{}).get(kind,[]) if isinstance(r,dict) and r.get('year')}
        failures=[]
        for year,url in spec['years'].items():
            if year in old and not force and year<datetime.now(timezone.utc).year:continue
            try:
                with read_zip_csv(url) as (fields,rows):
                    entry=aggregate(rows,kind,year,fields)
                check_consistency(kind,entry)
                old[year]=entry
                successes+=1
                success_this_source+=1
                LOG.info('%s %s: %s registros de residentes em %s linhas nacionais',kind,year,entry['value'],entry['scanned'])
            except Exception as exc:
                failures.append(year)
                LOG.warning('%s %s: fonte não atualizada: %s',kind,year,str(exc)[:160])
        data.setdefault('series',{})[kind]=[old[y] for y in sorted(old)]
        data.setdefault('sources',{})[kind]={
            'label':spec['title'],'url':spec['catalog'],
            'status':'ok' if old and not failures else 'partial' if old else 'error',
            'retrievedAt':utcnow() if success_this_source else data.get('sources',{}).get(kind,{}).get('retrievedAt'),
            'reference':'2024–2026 conforme arquivo anual; município de residência',
            'note':spec['method']+(' Não foi possível atualizar: '+', '.join(map(str,failures)) if failures else ''),
            'yearsAvailable':sorted(old)
        }
    for key,(title,url,note) in ADDITIONAL.items():
        data['sources'][key]={'label':title,'url':url,'status':'not_loaded','retrievedAt':None,'reference':None,'note':note,'yearsAvailable':[]}
    if successes:data['updatedAt']=utcnow()
    save_atomic(data)
    LOG.info('Dados territoriais: %s arquivos anuais processados. Snapshot em %s',successes,OUT)

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    run()
