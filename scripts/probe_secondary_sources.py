#!/usr/bin/env python3
"""Pesquisa de formato somente; não grava microdados nem expõe linhas originais."""
import io,csv,zipfile,urllib.request,datetime
SOURCES={
 'emultcust':'https://demas-dados-abertos.s3.amazonaws.com/csv/emultcust.csv.zip',
 'emulthomol':'https://demas-dados-abertos.s3.amazonaws.com/csv/emulthomol.csv.zip',
 'emultvlrff':'https://demas-dados-abertos.s3.amazonaws.com/csv/emultvlrff.csv.zip',
 'mgdi_ate':'https://demas-dados-abertos.s3.amazonaws.com/csv/mgdi_ms_3f6.csv.zip',
 'pate_cirpre':'https://demas-dados-abertos.s3.amazonaws.com/csv/pnrfcirpre.csv.zip',
 'ftp_sih':'https://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDRS2607.dbc',
 'ftp_sia':'https://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/PARS2607.dbc'
}
def run():
 for name,url in SOURCES.items():
  print("SCHEMA_PROBE",name,"START",flush=True)
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"WebGIS Saude Canoas 1.2"},method="HEAD")
   with urllib.request.urlopen(req,timeout=15) as response:
    size=response.headers.get('Content-Length');status=response.status
   print("SCHEMA_PROBE",name,"head",status,"bytes",size,flush=True)
   if name.startswith('ftp_'):continue
   if size and int(size)>30*1024*1024:
    print("SCHEMA_PROBE",name,"SKIP large file",flush=True);continue
   with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"WebGIS Saude Canoas 1.2"}),timeout=40) as response:
    payload=response.read(30*1024*1024+1)
   if len(payload)>30*1024*1024:raise ValueError("uncompressed download limit")
   with zipfile.ZipFile(io.BytesIO(payload)) as z:
    items=[x for x in z.infolist() if x.filename.lower().endswith('.csv')]
    print("SCHEMA_PROBE",name,"zip_members",[(x.filename,x.file_size) for x in items[:3]],flush=True)
    if not items:continue
    member=items[0]
    with z.open(member) as f:
     preview=f.peek(32768)[:32768]
     try:preview.decode('utf-8-sig');enc='utf-8-sig'
     except UnicodeDecodeError:enc='cp1252'
     stream=io.TextIOWrapper(f,encoding=enc,errors='replace',newline='')
     first=stream.readline();sep=';' if first.count(';')>first.count(',') else ','
     fields=[x.strip() for x in next(csv.reader([first],delimiter=sep))]
     print("SCHEMA_PROBE",name,"CSV columns",fields[:110],"sep",sep,"encoding",enc,flush=True)
     reader=csv.DictReader(stream,fieldnames=fields,delimiter=sep)
     count=0;matches=0;mun_fields=[];examples=[]
     for row in reader:
      count+=1
      relevant=[key for key in row if any(x in key.lower() for x in ('ibge','municip','locali','cidade','muni','codmun','co_mun'))]
      if not mun_fields:mun_fields=relevant
      vals=[str(row.get(k,'')).strip() for k in relevant]
      if any(v.startswith('430460') or v.upper()=='CANOAS' for v in vals):
       matches+=1
       if len(examples)<3:
        examples.append({k:str(v)[:60] for k,v in row.items() if any(x in k.lower() for x in ('ibge','municip','ano','comp','data','qtd','quant','val','valor','nume','total','proced','regiao','uf'))})
      if count>=150000:break
     print("SCHEMA_PROBE",name,"lines",count,"municipal_fields",mun_fields,"matches",matches,"municipal_sample_numeric_or_geo",examples,flush=True)
  except Exception as exc:
   print("SCHEMA_PROBE",name,"ERROR",type(exc).__name__,str(exc)[:180],flush=True)
if __name__=='__main__':run()
