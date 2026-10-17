#!/usr/bin/env python3
"""Indicadores públicos MGDI/DATASUS com chave municipal e competência explícitas.

Processa arquivos CSV nacionais em um diretório temporário; somente dados
agregados de Canoas são persistidos. Não estima SIA/SIH com amostras de API.
"""
import csv, io, json, logging, os, re, tempfile, zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'public/data/sus.json'
LOG=logging.getLogger('webgis.sus')
BASE='https://demas-dados-abertos.s3.amazonaws.com/csv/'
CONFIG={
 'emulti_custeadas':{
   'file':'emultcust','label':'Equipes eMulti custeadas','unit':'equipes','kind':'count',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-equipes-multiprofissionais-na-aps-emulti/resource/emultcust_csv',
   'method':'Equipes multiprofissionais da APS aptas e contempladas com incentivo de custeio federal; estoque mensal, não somar competências.'
 },
 'emulti_homologadas':{
   'file':'emulthomol','label':'Equipes eMulti homologadas','unit':'equipes','kind':'count',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-equipes-multiprofissionais-na-aps-emulti/resource/emulthomol_csv',
   'method':'Equipes homologadas no CNES/INE para fins de financiamento. Não indica profissionais individuais nem consultas.'
 },
 'emulti_repasses':{
   'file':'emultvlrff','label':'Repasses federais para eMulti','unit':'R$','kind':'currency',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-equipes-multiprofissionais-na-aps-emulti/resource/emultvlrff_csv',
   'method':'Valor indicado pela fonte para transferências federais eMulti. Não representa toda a despesa municipal em saúde nem produção SIA.'
 },
 'citopatologicos':{
   'file':'ccmec25a64','label':'Exames citopatológicos (25–64 anos)','unit':'exames','kind':'count','cadence':'annual',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama/resource/ccmec25a64_csv',
   'method':'Exames citopatológicos de mulheres de 25 a 64 anos por município de realização, conforme a definição MGDI/DATASUS; não equivale a mulheres únicas.'
 },
 'mamografias':{
   'file':'ccmec50a69','label':'Mamografias de rastreamento (50–69 anos)','unit':'exames','kind':'count','cadence':'annual',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama/resource/ccmec50a69_csv',
   'method':'Mamografias bilaterais para rastreamento em mulheres de 50 a 69 anos; município de realização do exame, não residência da paciente.'
 },
}
UNVALIDATED={
 'consultas_aps_razao':{'label':'Consultas médicas na APS por 100 habitantes','unit':'por 100 hab.','status':'not_loaded',
  'note':'O arquivo municipal oficial excede o limite de segurança da extração integral desta versão. Indicador ainda não validado para Canoas.',
  'url':'https://dadosabertos.saude.gov.br/dataset/ripsa-cobertura-dimensao-1-consultas-medicas-e-odontologicas/resource/mgdi_ms_4iu_csv'},
 'sih':{'label':'Internações hospitalares SIH/SUS','status':'not_loaded','note':'Arquivos DBC mensais oficiais disponíveis, mas a extração completa em nível municipal não está acessível por HTTPS neste runner; API pública devolveu somente amostra. Sem total estimado.','url':'https://datasus.saude.gov.br/assistencia-a-saude/'},
 'sia':{'label':'Produção ambulatorial SIA/SUS','status':'not_loaded','note':'Arquivos mensais DBC não acessíveis por HTTPS neste runner; API pública parcial. Indicadores citopatológicos, mamografias e consultas APS publicados separadamente não representam o total do SIA.','url':'https://datasus.saude.gov.br/assistencia-a-saude/'},
 'pni':{'label':'Cobertura vacinal PNI/RNDS','status':'not_loaded','note':'Sem cálculo de cobertura até validar denominadores, coortes e qualidade da base municipal.','url':'https://opendatasus.saude.gov.br/'}
}
def timestamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def decimal_value(raw):
    raw=str(raw or '').strip()
    if not raw or raw.lower() in ('nan','none','null','-','n/d'):return None
    raw=raw.replace('R$','').replace(' ','').replace('\xa0','')
    if ',' in raw and '.' in raw:
        raw=raw.replace('.','').replace(',','.') if raw.rfind(',')>raw.rfind('.') else raw.replace(',','')
    elif ',' in raw:raw=raw.replace(',','.')
    try:
        value=Decimal(raw)
        return value if value.is_finite() else None
    except InvalidOperation:return None
def period_value(raw):
    raw=str(raw or '').strip()
    if re.fullmatch(r'20\d{2}(?:0[1-9]|1[012])',raw):
        return raw
    if re.fullmatch(r'20\d{2}',raw):return raw
    return None

@contextmanager
def download_records(config):
    """Leitura de CSV ZIP em streaming, sem gravar linhas individuais no repositório."""
    path=BASE+config['file']+'.csv.zip'
    with tempfile.TemporaryDirectory(prefix='webgis-mgdi-') as folder:
        target=Path(folder)/'source.zip'
        with urlopen(Request(path,headers={'User-Agent':'WebGIS-Saude-Canoas/1.2'}),timeout=180) as response,target.open('wb') as stream:
            size=0
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>35*1024*1024:raise ValueError('ZIP MGDI excede 35 MiB')
                stream.write(chunk)
        if not zipfile.is_zipfile(target):raise ValueError('Recurso MGDI não é ZIP')
        with zipfile.ZipFile(target) as archive:
            items=[m for m in archive.infolist() if m.filename.lower().endswith('.csv')]
            if len(items)!=1:raise ValueError('MGDI: arquivo CSV não único')
            if items[0].file_size>150*1024*1024:raise ValueError('MGDI: arquivo extraído muito grande')
            with archive.open(items[0]) as raw:
                preview=raw.peek(16384)[:16384]
                try:preview.decode('utf-8-sig');codec='utf-8-sig'
                except UnicodeDecodeError:codec='cp1252'
                stream=io.TextIOWrapper(raw,encoding=codec,errors='replace',newline='')
                header=stream.readline()
                delim=';' if header.count(';')>header.count(',') else ','
                keys=[x.strip().lower() for x in next(csv.reader([header],delimiter=delim))]
                if len(keys)!=len(set(keys)):raise ValueError('MGDI: colunas duplicadas')
                yield keys,csv.DictReader(stream,fieldnames=keys,delimiter=delim)

def extract(rows,columns,kind):
    required={'co_ibge','co_anomes','vl_indicador_calculado_mun'}
    if not required.issubset(columns):
        raise ValueError('MGDI sem colunas municipais/temporais: '+str(sorted(required-set(columns))))
    result={}
    municipalities=set(); scanned=0; cityrows=0; nonempty=0
    for row in rows:
        scanned+=1
        mun=str(row.get('co_ibge') or '').strip()
        if mun:municipalities.add(mun)
        if mun!='430460':continue
        cityrows+=1
        period=period_value(row.get('co_anomes'))
        if not period:raise ValueError('MGDI: competência inválida em Canoas')
        value=decimal_value(row.get('vl_indicador_calculado_mun'))
        if value is None:continue
        nonempty+=1
        if value<0:raise ValueError('MGDI: valor municipal negativo')
        if kind=='count' and value!=value.to_integral_value():
            raise ValueError('MGDI: contador não inteiro')
        numeric=int(value) if kind=='count' else float(round(value,2))
        if period in result and result[period]!=numeric:
            raise ValueError('MGDI: competências duplicadas com divergência')
        result[period]=numeric
    if scanned<500 or len(municipalities)<20:
        raise ValueError('MGDI: cobertura do arquivo nacional insuficiente')
    if not result:raise ValueError('MGDI: sem valor municipal informado para Canoas')
    periods=sorted(result)
    return {'series':[{'period':p,'value':result[p]} for p in periods[-24:]],
            'totalPeriods':len(periods),'earliest':periods[0],'latest':periods[-1],
            'lastValue':result[periods[-1]],'scanned':scanned,'municipalRecords':cityrows,
            'valuedMunicipalRecords':nonempty}

def read_data():
    try:
        data=json.loads(OUTPUT.read_text('utf8'))
        if isinstance(data.get('sources'),dict) and isinstance(data.get('series'),dict):return data
    except (FileNotFoundError,ValueError,TypeError):pass
    return {'schemaVersion':'1.0','updatedAt':None,'series':{},'sources':{}}
def write_atomic(data):
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    target=OUTPUT.with_suffix('.json.tmp')
    target.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf8')
    os.replace(target,OUTPUT)
def run():
    data=read_data()
    successes=0
    force=os.getenv('MGDI_FORCE','')=='true'
    for name,conf in CONFIG.items():
        existing=data['sources'].get(name,{})
        if not force and existing.get('status')=='ok':
            try:
                cached=datetime.fromisoformat(existing['retrievedAt'])
                if (datetime.now(timezone.utc)-cached).days<7:continue
            except (TypeError,ValueError,KeyError):pass
        try:
            with download_records(conf) as (columns,rows):
                parsed=extract(rows,columns,conf['kind'])
            source={'label':conf['label'],'unit':conf['unit'],'kind':conf['kind'],
                    'cadence':conf.get('cadence','monthly'),'url':conf['url'],
                    'method':conf['method'],'status':'ok','retrievedAt':timestamp(),
                    'reference':parsed['latest'],'start':parsed['earliest'],
                    'totalPeriods':parsed['totalPeriods'],'municipalRecords':parsed['municipalRecords'],
                    'nationalRecords':parsed['scanned']}
            data['series'][name]=parsed['series']
            data['sources'][name]=source
            successes+=1
            LOG.info('MGDI %s: %s competências; %s = %s (%s registros nacionais)',
                     name,parsed['totalPeriods'],parsed['latest'],parsed['lastValue'],parsed['scanned'])
        except Exception as exc:
            previous=data['sources'].get(name,{})
            if previous.get('status')=='ok':
                previous['note']='Última tentativa falhou: '+str(exc)[:150]
                data['sources'][name]=previous
            else:
                data['sources'][name]={'label':conf['label'],'unit':conf['unit'],'url':conf['url'],
                    'status':'error','note':'Falha de validação da fonte: '+str(exc)[:150],
                    'method':conf['method'],'reference':None}
            LOG.warning('MGDI %s não atualizado: %s',name,str(exc)[:150])
    for name,desc in UNVALIDATED.items():data['sources'][name]=desc
    if successes:data['updatedAt']=timestamp()
    write_atomic(data)
    LOG.info('MGDI: %s fontes municipais validadas; %s',successes,OUTPUT)
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    run()
