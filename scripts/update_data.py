#!/usr/bin/env python3
"""Processa dados públicos de Canoas. Sem microdados publicados e sem zeros artificiais.

Fontes verificadas em https://apidadosabertos.saude.gov.br/static/swagger.json
Os JSONs só são modificados após extrações completas e validadas.
"""
import json, os, re, time, logging, math, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'public'/'data'
SUMMARY = DATA/'summary.json'
GEO = DATA/'establishments.geojson'
API = 'https://apidadosabertos.saude.gov.br'
SIDRA = 'https://apisidra.ibge.gov.br/values/t/6579/n6/4304606/v/9324/p/all?formato=json'
IBGE_6='430460'
YEARS = sorted(set(int(x) for x in os.getenv('DATA_YEARS','2025,2026').split(',') if x.strip().isdigit()))
MAX_PAGES = int(os.getenv('MAX_PAGES_PER_SERIES', '160'))
LOG=logging.getLogger('webgis')

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def request_json(url,timeout=50,retries=3):
    for attempt in range(retries):
        try:
            with urlopen(Request(url,headers={'User-Agent':'WebGISSaudeCanoas/1.0 (dados abertos)','Accept':'application/json'}),timeout=timeout) as r:
                if r.status!=200:raise ValueError(f'HTTP {r.status}')
                raw=r.read(30*1024*1024+1)
            if len(raw)>30*1024*1024:raise ValueError('Resposta excede limite por página')
            return json.loads(raw)
        except (HTTPError,URLError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
            if attempt==retries-1:raise
            LOG.warning('Tentativa %s de %s falhou: %s',attempt+1,url.split('?')[0],exc)
            time.sleep(2**attempt)

def parse_number(v):
    if v is None or isinstance(v,bool):return None
    s=str(v).strip().replace(' ','')
    if s in ('','-','...','X','null'):return None
    if '.' in s and ',' in s:s=s.replace('.','').replace(',','.')
    elif ',' in s:s=s.replace(',','.')
    try:
        n=float(s)
        return int(n) if math.isfinite(n) else None
    except ValueError:return None

def coord(v):
    if v is None:return None
    try:
        n=float(str(v).strip().replace(',','.'))
        return n if math.isfinite(n) and abs(n)<=180 else None
    except (ValueError,TypeError):return None

def pick(d,*keys):
    if not isinstance(d,dict):return None
    lowered={k.lower():v for k,v in d.items()}
    for key in keys:
        v=lowered.get(key.lower())
        if v is not None and v!='':return v
    return None

def normalize_type(x):
    v=''.join(c for c in unicodedata.normalize('NFKD',str(x or '').upper()) if not unicodedata.combining(c))
    if any(t in v for t in ('CENTRO DE SAUDE','UNIDADE BASICA','POSTO DE SAUDE','UNIDADE DE SAUDE DA FAMILIA','UBS ')):return 'ubs'
    if 'HOSPITAL' in v or 'MATERNIDADE' in v:return 'hospital'
    if any(t in v for t in ('PRONTO SOCORRO','PRONTO ATENDIMENTO','UPA','URGÊNCIA','URGENCIA','SAMU')):return 'urgencia'
    if any(t in v for t in ('CLINICA','CLÍNICA','POLICLINICA','POLICLÍNICA','CONSULTORIO','CONSULTÓRIO','AMBULATORIO')):return 'clinica'
    return 'outros'

def valid_canoas(r):
    code=pick(r,'codigo_municipio','co_municipio_gestor','co_ibge','municipio_codigo')
    if code is not None:return re.sub(r'\D','',str(code)) in ('430460','4304606')
    city=pick(r,'municipio','nome_municipio','no_municipio')
    return city is None or str(city).strip().upper()=='CANOAS'  # filtro municipal no servidor

def unpack(payload, candidates=()):
    if isinstance(payload,list):return [r for r in payload if isinstance(r,dict)],None
    if not isinstance(payload,dict):raise ValueError('Estrutura de resposta não reconhecida')
    total=parse_number(pick(payload,'total','total_registros','count','totalRecords'))
    for key in (*candidates,'estabelecimentos','dados','data','items','results','registros','resultado','content'):
        a=pick(payload,key)
        if isinstance(a,list):return [r for r in a if isinstance(r,dict)],total
        if isinstance(a,dict):
            try:return unpack(a,candidates)
            except ValueError:pass
    for a in payload.values():
        if isinstance(a,list) and (not a or isinstance(a[0],dict)):
            return [r for r in a if isinstance(r,dict)],total
    raise ValueError('Resposta JSON sem lista identificável: '+str(list(payload)[:8]))

def paginate(endpoint, params, limit, cap, consume, candidates=()):
    read=0
    for page in range(cap):
        rows,total=unpack(request_json(API+endpoint+'?'+urlencode({**params,'limit':limit,'offset':page})),candidates)
        if page==0 and not rows:raise ValueError(endpoint+': nenhum registro para os filtros')
        for row in rows:consume(row)
        read+=len(rows)
        if page%25==0:LOG.info('%s: página %s, registros %s',endpoint,page,read)
        if len(rows)<limit or (total is not None and read>=total):return read
        time.sleep(.1)
    raise ValueError(f'{endpoint}: extrato incompleto (limite {cap} páginas)')

def write_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def mark(s,key,ref,records):
    info=s['sourceInfo'][key]
    info.update(status='ok',retrievedAt=now(),reference=ref,records=records)
    if (info.get('note') or '').startswith('A última tentativa falhou'):
        info['note']=None

def fail(s,key,exc):
    LOG.warning('%s não foi atualizado: %s',key,exc)
    info=s['sourceInfo'][key]
    if info['status']!='ok':info['status']='error'
    info['note']='A última tentativa falhou; snapshots anteriores foram preservados. '+type(exc).__name__

def update_ibge(s):
    obs=request_json(SIDRA)
    if not isinstance(obs,list):raise ValueError('SIDRA com estrutura inesperada')
    rows=[]
    for item in obs[1:]:
        year=parse_number(pick(item,'D3C','D2C','ano'))
        value=parse_number(pick(item,'V'))
        if year and value and 2000<=year<=datetime.now().year and 100000<value<1000000:rows.append({'year':year,'value':value})
    rows=sorted({r['year']:r for r in rows}.values(),key=lambda r:r['year'])
    if not rows:raise ValueError('SIDRA sem série utilizável')
    s['series']['population']=rows
    s['municipality'].update(population=rows[-1]['value'],populationYear=rows[-1]['year'])
    mark(s,'ibge',f'Estimativas SIDRA até {rows[-1]["year"]}',len(rows))

def fetch_cnes():
    out={}
    def consume(r):
        if not valid_canoas(r):raise ValueError('O servidor incluiu município diferente de Canoas')
        code=str(pick(r,'codigo_cnes','co_cnes','cnes') or '').strip()
        if code:out[code]=r
    n=paginate('/cnes/estabelecimentos',{'codigo_municipio':int(IBGE_6),'status':1},20,250,consume)
    if len(out)<20:raise ValueError('CNES retornou menos de 20 estabelecimentos; consulta suspeita')
    return list(out.values()),n

def build_cnes(rows):
    points=[];kinds=Counter();bairros=Counter();ubs=hosp=0
    for r in rows:
        kind=str(pick(r,'descricao_tipo_unidade','tipo_unidade','tipo_estabelecimento','ds_tipo_unidade','estabelecimento_tipo_unidade') or 'Não informado')
        cat=normalize_type(kind)
        kinds[kind]+=1
        ubs+=cat=='ubs';hosp+=cat=='hospital'
        bairro=str(pick(r,'bairro_estabelecimento','bairro','no_bairro') or 'Não informado')
        bairros[bairro]+=1
        lat=coord(pick(r,'latitude_estabelecimento','latitude','nu_latitude','vl_latitude'))
        lng=coord(pick(r,'longitude_estabelecimento','longitude','nu_longitude','vl_longitude'))
        if lat is None or lng is None:continue
        if -51.4<lat<-50.99 and -30.1<lng<-29.73:lat,lng=lng,lat
        if not(-30.1<lat<-29.73 and -51.4<lng<-50.99):continue
        number=str(pick(r,'numero_estabelecimento','numero','nu_endereco') or '')
        street=str(pick(r,'endereco_estabelecimento','logradouro','no_logradouro') or '')
        sus=pick(r,'vinculo_sus','estabelecimento_faz_atendimento_sus','atendimento_sus')
        sus_bool=True if str(sus).lower() in ('1','s','sim','true') else False if str(sus).lower() in ('0','n','nao','não','false') else None
        code=str(pick(r,'codigo_cnes','co_cnes','cnes'))
        points.append({'type':'Feature','id':code,'geometry':{'type':'Point','coordinates':[round(lng,6),round(lat,6)]},'properties':{'cnes':code,'name':str(pick(r,'nome_fantasia','no_fantasia','estabelecimento_nome_fantasia') or 'Estabelecimento CNES'),'type':kind,'category':cat,'address':', '.join(x for x in (street,number) if x),'neighborhood':bairro,'phone':str(pick(r,'numero_telefone_estabelecimento','telefone','nu_telefone') or ''),'hasBeds':None,'sus':sus_bool}})
    stats={'total':len(rows),'withCoordinates':len(points),'ubs':ubs,'hospitals':hosp,'byType':[{'name':k,'value':v} for k,v in kinds.most_common(20)],'byNeighborhood':[{'name':k,'value':v} for k,v in bairros.most_common(40)],'asOf':now()[:10]}
    return {'type':'FeatureCollection','features':points},stats

def latest_bed_competence():
    """Procura a competência mais recente COM registros, evitando varrer anos do CNES.

    A competência é YYYYMM; meses incompletos ou sem publicação são ignorados.
    A busca é limitada a 18 meses e pode ser controlada em BED_COMPETENCE.
    """
    fixed=os.environ.get('BED_COMPETENCE','').strip()
    if fixed:
        if not re.fullmatch(r'20\d{4}',fixed) or not 1<=int(fixed[-2:])<=12:
            raise ValueError('BED_COMPETENCE deve usar AAAAMM')
        return int(fixed)
    current=datetime.now(timezone.utc)
    for delta in range(18):
        total_months=current.year*12+(current.month-1)-delta
        comp=(total_months//12)*100+(total_months%12)+1
        payload=request_json(API+'/assistencia-a-saude/cnes-leitos?'+urlencode(
            {'co_ibge':int(IBGE_6),'nu_comp':comp,'limit':1,'offset':0}))
        rows,total=unpack(payload,('leitos',))
        if rows:
            # Não confiar num retorno que ignore o filtro de competência.
            for row in rows:
                got=parse_number(pick(row,'nu_comp','competencia'))
                if got is not None and got!=comp:
                    raise ValueError(f'API ignorou filtro nu_comp={comp}')
            return comp
        if total is not None and total>0:
            raise ValueError('CNES leitos: total positivo sem registros na página inicial')
    raise ValueError('Nenhuma competência de leitos foi encontrada nos últimos 18 meses')

def update_beds(s):
    competence=latest_bed_competence()
    data=[]
    n=paginate('/assistencia-a-saude/cnes-leitos',
        {'co_ibge':int(IBGE_6),'nu_comp':competence},1000,60,data.append,('leitos',))
    # Nunca misturar períodos: somar vários meses multiplicaria artificialmente os leitos.
    for r in data:
        period=parse_number(pick(r,'nu_comp','competencia'))
        if period is not None and period!=competence:
            raise ValueError('Leitos com competência divergente da consultada')
        code=pick(r,'co_ibge','codigo_municipio')
        if code is not None and not valid_canoas(r):
            raise ValueError('Consulta de leitos retornou outro município')
    total=sus=recognized=0
    per_cnes=defaultdict(int)
    # Registros publicados por tipo de leito são somáveis, mas respostas duplicadas não.
    uniq={json.dumps(r,ensure_ascii=False,sort_keys=True):r for r in data}
    for r in uniq.values():
        a=parse_number(pick(r,'qt_exist','qt_existente','qt_existentes','qt_leitos_existentes','qt_leitos','quantidade_existente'))
        b=parse_number(pick(r,'qt_sus','qt_leitos_sus','quantidade_sus'))
        if a is None and b is None:continue
        if (a is not None and a<0) or (b is not None and b<0):
            raise ValueError('Quantidades negativas de leitos na fonte')
        recognized+=1;total+=(a or 0);sus+=(b or 0)
        cn=str(pick(r,'co_cnes','codigo_cnes','cnes') or '')
        if cn:per_cnes[cn]+=(a or 0)
    if not recognized:raise ValueError('CNES leitos não contém campos de quantidade reconhecidos')
    if not per_cnes:raise ValueError('CNES leitos não contém códigos CNES reconhecidos; filtro de leitos suspenso')
    if sus>total:raise ValueError('Leitos SUS superam o total existente; conferir mapeamento')
    s['beds']={'total':total,'sus':sus,'asOf':str(competence)}
    mark(s,'beds',f'Competência {competence}',n)
    if GEO.exists():
        geo=json.loads(GEO.read_text('utf8'))
        for f in geo['features']:
            cn=f['properties']['cnes']
            f['properties']['hasBeds']=per_cnes.get(cn,0)>0
        write_json(GEO,geo)

def annual(s,key,endpoint,params,fields):
    """Atualiza anos separadamente. Não transforma ano ausente/falho em 0.

    Um ano válido não deve desaparecer por uma falha isolada de outro ano.
    """
    result=[];count=0;failures=[]
    for year in YEARS:
        amount=0;known=0
        def consume(r):
            nonlocal amount,known
            if fields is None:
                amount+=1;known+=1
            else:
                n=parse_number(pick(r,*fields))
                if n is not None and n>=0:amount+=n;known+=1
        try:
            n=paginate(endpoint,{**params,'nu_ano':year},1000,MAX_PAGES,consume,(key,'dados','procedimentos'))
            if not known:raise ValueError('nenhum valor agregável retornado')
        except Exception as exc:
            failures.append(year)
            LOG.warning('%s %s indisponível: %s',key,year,exc)
            continue
        count+=n;result.append({'year':year,'value':amount})
    if not result:raise ValueError(f'{key}: nenhum dos anos pôde ser extraído integralmente')
    # Preserve anos anteriores que não foram reconsultados com êxito nesta rodada.
    previous={r['year']:r for r in s['series'].get(key,[]) if r.get('year') in failures}
    previous.update({r['year']:r for r in result})
    s['series'][key]=sorted(previous.values(),key=lambda r:r['year'])
    mark(s,key,'; '.join(str(x['year']) for x in result),count)
    if failures:
        s['sourceInfo'][key]['status']='partial'
        s['sourceInfo'][key]['note']='Sem atualização validada nos anos: '+', '.join(map(str,failures))+'. Séries previamente coletadas foram preservadas.'

def get_logo():
    # Só armazena o arquivo original, quando disponibilizado pelo domínio institucional.
    target=ROOT/'public/assets/geocanoas-oficial.webp'
    try:
        req=Request('https://geo.canoas.rs.gov.br/assets/img/profile/GEOCANOAS_Vetorizado2.webp',headers={'User-Agent':'Mozilla/5.0'})
        with urlopen(req,timeout=15) as resp:raw=resp.read(3_000_001)
        if len(raw)<=3_000_000 and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' and (not target.exists() or target.read_bytes()!=raw):target.write_bytes(raw)
    except Exception as e:LOG.warning('Logo institucional não pode ser obtida agora: %s',e)

def run():
    s=json.loads(SUMMARY.read_text('utf8'));success=0
    for key,call in [('ibge',lambda:update_ibge(s))]:
        try:call();success+=1
        except Exception as e:fail(s,key,e)
    try:
        rows,n=fetch_cnes();geo,stats=build_cnes(rows)
        if not geo['features']:raise ValueError('CNES sem pontos geográficos válidos')
        write_json(GEO,geo);s['facilities']=stats
        mark(s,'cnes',f'Estabelecimentos ativos · coleta {now()[:10]}',n);success+=1
    except Exception as e:fail(s,'cnes',e)
    try:update_beds(s);success+=1
    except Exception as e:fail(s,'beds',e)
    if os.environ.get('SKIP_HEAVY','false').lower()!='true':
        jobs=[('dengue','/arboviroses/dengue',{'id_municip':IBGE_6},None),
              ('sia','/assistencia-a-saude/sia-procedimentos-ambulatoriais',{'co_ibge':int(IBGE_6)},('qt_produzida','qt_producao','qt_aprovada','qt_prod')),
              ('sih','/assistencia-a-saude/sih-procedimentos-hospitalares',{'co_ibge':int(IBGE_6)},('qt_aih','qt_aih_aprovadas','qt_aihs','qt_internacoes'))]
        for key,endpoint,params,fields in jobs:
            try:annual(s,key,endpoint,params,fields);success+=1
            except Exception as e:fail(s,key,e)
    get_logo()
    if success:s['generatedAt']=now()
    write_json(SUMMARY,s)
    LOG.info('Atualização: %s fonte(s) concluída(s); falhas preservaram snapshots.',success)
    if not success:raise SystemExit('Nenhuma fonte atualizada. Verifique as APIs e rode novamente.')

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    run()
