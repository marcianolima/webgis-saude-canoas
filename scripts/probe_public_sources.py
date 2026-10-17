#!/usr/bin/env python3
"""Diagnóstico temporário SISAB/SIH/SIA sem emitir microdados pessoais."""
import csv,io,json,os,tempfile,urllib.request,zipfile
from pathlib import Path

def sisab():
 url="https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/sisab/indicador_desempenho/csv/sisab_indicador_desempenho_2024Q3.csv.zip"
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/"sisab.zip"
  with urllib.request.urlopen(url,timeout=90) as resp,path.open("wb") as out:
   while buf:=resp.read(1024*1024):out.write(buf)
  with zipfile.ZipFile(path) as archive:
   member=next(i for i in archive.infolist() if i.filename.endswith(".csv"))
   with archive.open(member) as raw:
    sample=raw.peek(4096)
    enc="utf-8-sig"
    try:sample.decode(enc)
    except UnicodeDecodeError:enc="cp1252"
    stream=io.TextIOWrapper(raw,encoding=enc,errors="replace",newline="")
    head=stream.readline();sep=";" if head.count(";")>head.count(",") else ","
    fields=[c.strip() for c in next(csv.reader([head],delimiter=sep))]
    data=[r for r in csv.DictReader(stream,fieldnames=fields,delimiter=sep) if str(r.get("ibge") or "")=="430460"]
    print("DEEP_PROBE SISAB ROWS",len(data),"INDICATORS",sorted({r.get("co_tipo_indicador") for r in data}),flush=True)
    for r in data[:23]:
     print("DEEP_PROBE SISAB SUMMARY",json.dumps({
       k:r.get(k) for k in ('ibge','co_tipo_indicador','visao_equipe','vl_perc_quad',
        'percentual','numerador','denominador_utilizador','nu_competencia','ds_quadrimestre')
      },ensure_ascii=False),flush=True)
def parquet_probe(kind,filename):
 import pysus
 import pyarrow.parquet as pq
 bag=getattr(pysus.ftp,kind)(state="RS",year=2025,month=1,download=False)
 entries=list(bag)
 indexes=[i for i,x in enumerate(entries) if filename in str(x).upper()]
 print("DEEP_PROBE",kind,"BAG_TYPE",type(bag).__name__,"ROWS",len(entries),
       "INDEXES",indexes,"METHODS",[x for x in ('download_one','download') if hasattr(bag,x)],flush=True)
 if not indexes:return
 idx=indexes[0]
 try:
  files=bag.download_one(idx)
  print("DEEP_PROBE",kind,"DOWNLOADED_TYPE",type(files).__name__,flush=True)
  paths=[]
  if isinstance(files,(list,tuple)):paths=[str(getattr(x,'path',x)) for x in files]
  elif hasattr(files,'__iter__') and not isinstance(files,(str,bytes)):
   paths=[str(getattr(x,'path',x)) for x in files]
  elif files:paths=[str(getattr(files,'path',files))]
  if not paths or not any(Path(p).exists() for p in paths):
   paths=[str(p) for p in Path(os.getenv('PYSUS_CACHEPATH','/tmp')).rglob('*.parquet') if filename in str(p).upper()]
  print("DEEP_PROBE",kind,"LOCAL_FILES",[(Path(x).name,Path(x).stat().st_size) for x in paths if Path(x).exists()][:5],flush=True)
  for path in paths:
   if not Path(path).exists():continue
   parquet=pq.ParquetFile(path)
   print("DEEP_PROBE",kind,"PARQUET",parquet.metadata.num_rows,"COLUMNS",parquet.schema.names,flush=True)
   break
 except Exception as exc:print("DEEP_PROBE",kind,"ERROR",type(exc).__name__,str(exc)[:270],flush=True)
if __name__=="__main__":
 try:sisab()
 except Exception as exc:print("DEEP_PROBE SISAB ERROR",type(exc).__name__,str(exc)[:280],flush=True)
 with tempfile.TemporaryDirectory(prefix="pysus-") as folder:
  os.environ["PYSUS_CACHEPATH"]=folder
  for kind,prefix in (("sih","RDRS2501"),("sia","PARS2501")):
   try:parquet_probe(kind,prefix)
   except Exception as exc:print("DEEP_PROBE",kind,"ERROR",type(exc).__name__,str(exc)[:280],flush=True)
