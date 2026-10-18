#!/usr/bin/env python3
"""Indicadores públicos MGDI/DATASUS com chave municipal e competência explícitas.

Processa arquivos CSV nacionais em um diretório temporário; somente dados
agregados de Canoas são persistidos. Não estima SIA/SIH com amostras de API.
"""
import csv, io, json, logging, os, re, tempfile, zipfile, time, unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError, HTTPError

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
 'consultas_aps_razao':{
   'file':'mgdi_ms_4iu','label':'Razão de consultas médicas na APS','unit':'por 100 hab.','kind':'rate','cadence':'annual','category':'TC',
   'url':'https://dadosabertos.saude.gov.br/dataset/ripsa-cobertura-dimensao-1-consultas-medicas-e-odontologicas/resource/mgdi_ms_4iu_csv',
   'method':'Razão anual de consultas médicas do SUS em estabelecimentos de Atenção Primária por 100 habitantes. Não é contagem total de consultas e não mede consultas individuais.'
 },
 'consultas_especializadas_razao':{
   'file':'mgdi_ms_0bx','label':'Razão de consultas médicas especializadas','unit':'por 100 hab.','kind':'rate','cadence':'annual','category':'TC',
   'url':'https://dadosabertos.saude.gov.br/dataset/ripsa-cobertura-dimensao-1-consultas-medicas-e-odontologicas/resource/mgdi_ms_0bx_csv',
   'method':'Razão de consultas médicas na atenção especializada do SUS por 100 habitantes, segundo metodologia RIPSA. Não é total da produção SIA/SUS.'
 },
 'sih_internacoes_anuais':{
   'file':'ripsa019rc','label':'Internações hospitalares SUS (AIHs)','unit':'internações','kind':'count','cadence':'annual','parser':'ripsa_aih',
   'url':'https://dadosabertos.saude.gov.br/dataset/ripsa-recursos-dimensao-3-recursos-financeiros-assistencia-a-saude/resource/ripsa019rc_csv',
   'method':'Denominador anual do indicador RIPSA REC.3.02: número de internações hospitalares SUS no município de ocorrência. Contagem de internações autorizadas, não pacientes distintos nem origem residencial.'
 },
 'valor_medio_aih':{
   'file':'ripsa019rc','label':'Valor médio por internação (AIH)','unit':'R$/AIH','kind':'currency','cadence':'annual','parser':'ripsa_aih',
   'url':'https://dadosabertos.saude.gov.br/dataset/ripsa-recursos-dimensao-3-recursos-financeiros-assistencia-a-saude/resource/ripsa019rc_csv',
   'method':'Razão entre valores pagos pelo Ministério da Saúde e internações hospitalares SUS autorizadas. Indicador financeiro médio; não é total de internações SIH nem custo clínico real.'
 },
 'mamografias':{
   'file':'ccmec50a69','label':'Mamografias de rastreamento (50–69 anos)','unit':'exames','kind':'count','cadence':'annual',
   'url':'https://dadosabertos.saude.gov.br/dataset/mgdi-prevencao-do-cancer-de-colo-e-mama/resource/ccmec50a69_csv',
   'method':'Mamografias bilaterais para rastreamento em mulheres de 50 a 69 anos; município de realização do exame, não residência da paciente.'
 },
}
UNVALIDATED={
 'sih':{'label':'SIH/SUS — detalhamento de internações','status':'partial','note':'Produção mensal de AIHs RD por município e CNES já disponível no módulo Produção SIH/SIA, com cobertura parcial. A desagregação por procedimento e diagnóstico ainda não foi integrada. O total anual RIPSA utiliza outra metodologia e não deve ser somado às competências RD.','url':'https://datasus.saude.gov.br/assistencia-a-saude/'},
 'sia':{'label':'SIA/SUS — produção ambulatorial detalhada','status':'partial','note':'Produção PA mensal aprovada por município e CNES disponível com competências não processadas identificadas; ainda não há detalhamento por procedimento e não está comprovada a abrangência integral dos demais instrumentos SIA. São procedimentos, não pacientes únicos.','url':'https://datasus.saude.gov.br/assistencia-a-saude/'},
 'pni':{'label':'Cobertura vacinal PNI/RNDS','status':'not_loaded','note':'Arquivos nacionais mensais oficiais identificados (setembro/2026: cerca de 1,79 GB ZIP), mas o catálogo estadual PySUS consultado não apresentou arquivos RS/2025–2026. Não calcular cobertura sem imunizante, dose, faixa etária e denominador validados.','url':'https://dadosabertos.saude.gov.br/dataset/doses-aplicadas-pelo-programa-de-nacional-de-imunizacoes-pni-2026'}
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
        # Streaming em disco, tentativas com backoff e limites ajustáveis: não carrega ZIP completo na RAM.
        # Em arquivos de vários anos, 150 MB extraídos era insuficiente, mesmo com origem oficial.
        max_zip_mb=int(os.getenv('MGDI_MAX_ZIP_MB','350'))
        last=None
        for attempt in range(3):
            try:
                with urlopen(Request(path,headers={'User-Agent':'WebGIS-Saude-Canoas/1.3','Accept-Encoding':'identity'}),timeout=240) as response,target.open('wb') as stream:
                    size=0
                    while True:
                        chunk=response.read(1024*1024)
                        if not chunk:break
                        size+=len(chunk)
                        if size>max_zip_mb*1024*1024:raise ValueError('ZIP MGDI excede limite configurado')
                        stream.write(chunk)
                last=None
                break
            except (URLError,TimeoutError,ConnectionError) as exc:
                last=exc
                if attempt<2:time.sleep(2**attempt*3)
        if last is not None:raise last
        if not zipfile.is_zipfile(target):raise ValueError('Recurso MGDI não é ZIP')
        with zipfile.ZipFile(target) as archive:
            items=[m for m in archive.infolist() if m.filename.lower().endswith('.csv')]
            if len(items)!=1:raise ValueError('MGDI: arquivo CSV não único')
            limit_mb=int(os.getenv('MGDI_MAX_CSV_MB','1500'))
            if items[0].file_size>limit_mb*1024*1024:raise ValueError('MGDI: arquivo CSV acima do limite de '+str(limit_mb)+' MiB')
            LOG.info('MGDI %s: ZIP validado, CSV de %.1f MiB; leitura incremental em andamento',
                     config['file'],items[0].file_size/1024/1024)
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

def extract(rows,columns,kind,category=None):
    required={'co_ibge','co_anomes','vl_indicador_calculado_mun'}
    if not required.issubset(columns):
        raise ValueError('MGDI sem colunas municipais/temporais: '+str(sorted(required-set(columns))))
    result={}
    municipalities=set(); scanned=0; cityrows=0; nonempty=0
    for row in rows:
        scanned+=1
        if scanned>12_000_000:raise ValueError('MGDI: limite de 12 milhões de registros excedido')
        mun=str(row.get('co_ibge') or '').strip()
        if mun:municipalities.add(mun)
        if mun!='430460':continue
        if category is not None:
            if 'sg_categoria' not in columns:raise ValueError('MGDI: filtro de categoria solicitado sem coluna sg_categoria')
            if str(row.get('sg_categoria') or '').strip().upper()!=category:continue
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

def extract_ripsa_aih(rows,columns,kind):
    """Processa a base oficial RIPSA REC.3.02: anual, município de ocorrência.
    
    Publica numerador/denominador sem somar subgrupos, nunca microdados.
    """
    def unaccent(value):
        return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '')) if not unicodedata.combining(c)).lower()
    keys={unaccent(k):k for k in columns}
    required=('indicador','municipio','ano','denominador - numero de internacoes hospitalares','numerador - valor de internacoes hospitalares','multiplicador')
    absent=[k for k in required if k not in keys]
    if absent:raise ValueError('RIPSA AIH: colunas essenciais ausentes: '+str(absent))
    city={};all_regions=set();count=0;city_count=0
    for row in rows:
        count+=1
        if count>2_000_000:raise ValueError('RIPSA: quantidade de linhas inesperada')
        municipal=str(row.get(keys['municipio']) or '').strip()
        if municipal:all_regions.add(municipal)
        if municipal not in ('430460','4304606'):continue
        if str(row.get(keys['indicador']) or '').strip().upper()!='REC.3.02':continue
        city_count+=1
        year=str(row.get(keys['ano']) or '').strip()
        if not re.fullmatch(r'(?:19|20)\d{2}',year):raise ValueError('RIPSA: ano municipal inválido')
        total=decimal_value(row.get(keys['denominador - numero de internacoes hospitalares']))
        amount=decimal_value(row.get(keys['numerador - valor de internacoes hospitalares']))
        multiplier=decimal_value(row.get(keys['multiplicador']))
        if total is None or amount is None or multiplier is None:
            raise ValueError('RIPSA: numerador, denominador ou multiplicador ausente')
        if total<=0 or total!=total.to_integral_value() or amount<0 or multiplier<=0:
            raise ValueError('RIPSA: hospitalizações, pagamentos ou fator inválidos')
        value=int(total) if kind=='count' else float(round((amount/total)*multiplier,2))
        old=city.get(year)
        if old is not None and old!=value:raise ValueError('RIPSA: valores duplicados divergentes para ano municipal '+year)
        city[year]=value
    if count<500 or len(all_regions)<100:raise ValueError('RIPSA: cobertura nacional insuficiente')
    if not city or len(city)<3:raise ValueError('RIPSA: sem histórico anual municipal suficiente')
    years=sorted(city)
    return {'series':[{'period':y,'value':city[y]} for y in years[-24:]],
      'totalPeriods':len(years),'earliest':years[0],'latest':years[-1],
      'lastValue':city[years[-1]],'scanned':count,'municipalRecords':city_count,
      'valuedMunicipalRecords':len(city)}

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
                parsed=(extract_ripsa_aih(rows,columns,conf['kind']) if conf.get('parser')=='ripsa_aih'
                        else extract(rows,columns,conf['kind'],category=conf.get('category')))
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
