#!/usr/bin/env python3
"""Investigação temporária de esquema, tamanho e acessibilidade sem expor microdados."""
import csv, io, json, os, tempfile, urllib.request, zipfile
from pathlib import Path

URLS={
 "sisab_2024q3":"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/sisab/indicador_desempenho/csv/sisab_indicador_desempenho_2024Q3.csv.zip",
 "sisab_2024q2":"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/sisab/indicador_desempenho/csv/sisab_indicador_desempenho_2024Q2.csv.zip",
 "pni_2026_09":"https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv/vacinacao_set_2026_csv.zip",
}
def head(url):
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"WebGIS-Saude-Canoas/1.3"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.status,int(r.headers.get("Content-Length") or 0),r.headers.get("Content-Type")
def inspect(name,url,size):
    if not 1024<size<=90*1024*1024:return print("SOURCE_PROBE",name,"SKIP_DOWNLOAD_SIZE",size,flush=True)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/"test.zip"
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"WebGIS-Saude-Canoas/1.3"}),timeout=120) as f,path.open("wb") as out:
            n=0
            while chunk:=f.read(1024*1024):
                n+=len(chunk)
                if n>90*1024*1024:raise ValueError("Archive too large for this probe")
                out.write(chunk)
        with zipfile.ZipFile(path) as z:
            matches=[x for x in z.infolist() if x.filename.lower().endswith(".csv")]
            if len(matches)!=1:raise ValueError("CSV count "+str(len(matches)))
            entry=matches[0]
            with z.open(entry) as raw:
                sample=raw.peek(8192)[:8192]
                encoding="utf-8-sig"
                try:sample.decode(encoding)
                except UnicodeDecodeError:encoding="cp1252"
                stream=io.TextIOWrapper(raw,encoding=encoding,errors="replace",newline="")
                line=stream.readline();separator=";" if line.count(";")>line.count(",") else ","
                cols=[c.strip() for c in next(csv.reader([line],delimiter=separator))]
                print("SOURCE_PROBE",name,"COLUMNS",json.dumps(cols,ensure_ascii=False),"CSV_SIZE",entry.file_size,flush=True)
                reader=csv.DictReader(stream,fieldnames=cols,delimiter=separator)
                municipal=[k for k in cols if any(z in k.upper() for z in ("MUNIC","IBGE","CODMUN","CO_MUN"))]
                freq={};samples=[];read=0;found=0
                for row in reader:
                    read+=1
                    if any(str(row.get(k,"")).strip().startswith(("430460","Canoas","CANOAS")) for k in municipal):
                        found+=1
                        if len(samples)<3:
                            # Only publish explicitly statistical columns. Never log personal data fields.
                            patterns=("INDICADOR","NUMERADOR","DENOMINADOR","RESULTADO","META","PERCENT","MUNIC","IBGE","COMPET","ANO","QUADRIMESTRE","CO_EQUIPE","CO_CNES")
                            samples.append({k:str(v)[:60] for k,v in row.items() if any(t in k.upper() for t in patterns)})
                    if read>300000:break
                print("SOURCE_PROBE",name,"ROWS_SCANNED",read,"MATCHES",found,"MUNICIPAL_FIELDS",municipal,"PUBLIC_METRICS",json.dumps(samples,ensure_ascii=False),flush=True)
def pysus():
    try:
        import pysus
        print("SOURCE_PROBE", "PYSUS_VERSION",getattr(pysus,"__version__","unknown"),flush=True)
        for name in ("sih","sia"):
            try:
                fn=getattr(pysus.ftp,name)
                files=fn(state="RS",year=2025,month=1,download=False)
                print("SOURCE_PROBE","PYSUS",name,"COUNT",len(files),"SAMPLE_PATHS",[str(x)[:200] for x in list(files)[:4]],flush=True)
            except Exception as e:
                print("SOURCE_PROBE","PYSUS",name,"ERROR",type(e).__name__,str(e)[:230],flush=True)
    except Exception as e:
        print("SOURCE_PROBE","PYSUS_IMPORT_ERROR",type(e).__name__,str(e)[:230],flush=True)
if __name__=="__main__":
    for k,u in URLS.items():
        try:
            status,size,type_=head(u)
            print("SOURCE_PROBE",k,"HEAD",status,size,type_,flush=True)
            inspect(k,u,size)
        except Exception as e:print("SOURCE_PROBE",k,"ERROR",type(e).__name__,str(e)[:240],flush=True)
    pysus()
