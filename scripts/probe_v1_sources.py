#!/usr/bin/env python3
"""Investigação temporária de disponibilidade e esquemas de fontes oficiais; SEM exportar microdados."""
import csv, io, zipfile, tempfile
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from pathlib import Path

S3="https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br"
files={
 "dengue2026":S3+"/SINAN/Dengue/csv/DENGBR26.csv.zip",
 "dengue2025":S3+"/SINAN/Dengue/csv/DENGBR25.csv.zip",
 "sinasc2024":S3+"/SINASC/csv/SINASC_2024_csv.zip",
 "sim2024":S3+"/SIM/csv/DO24OPEN_csv.zip",
 "sim2025":S3+"/SIM/csv/Mortalidade_Geral_2025_csv.zip",
 "sinasc2025":S3+"/SINASC/csv/SINASC_2025_csv.zip",
}
def inspect_zip(label,url):
    try:
        with urlopen(Request(url,method="HEAD",headers={"User-Agent":"WebGIS-Saude-Canoas/1.0"}),timeout=22) as r:
            size=int(r.headers.get("Content-Length") or "0")
        print("PROBE",label,"bytes",size,"URL",url,flush=True)
        if not (100<size<125*1024*1024):
            print("PROBE",label,"SKIP_DUE_TO_SIZE_OR_UNKNOWN",flush=True);return
        with tempfile.TemporaryDirectory(prefix="health-probe") as folder:
            target=Path(folder)/"source.zip"
            with urlopen(Request(url,headers={"User-Agent":"WebGIS-Saude-Canoas/1.0"}),timeout=120) as response,target.open("wb") as file:
                amount=0
                while True:
                    part=response.read(1024*1024)
                    if not part:break
                    amount+=len(part)
                    if amount>125*1024*1024:raise ValueError("Exceeded file limit")
                    file.write(part)
            if not zipfile.is_zipfile(target):raise ValueError("not zip")
            with zipfile.ZipFile(target) as archive:
                members=[m for m in archive.infolist() if m.filename.lower().endswith(".csv")]
                if not members:raise ValueError("no CSV in ZIP")
                item=max(members,key=lambda m:m.file_size)
                with archive.open(item) as raw:
                    head=raw.peek(8192)[:8192]
                    encoding="utf-8-sig"
                    try:head.decode(encoding)
                    except UnicodeDecodeError:encoding="latin-1"
                    reader=io.TextIOWrapper(raw,encoding=encoding,errors="replace",newline="")
                    first=reader.readline()
                    sep=";" if first.count(";")>first.count(",") else ","
                    columns=next(csv.reader([first],delimiter=sep))
                    print("PROBE",label,"CSV",item.filename,"unc_bytes",item.file_size,"columns",[x.strip() for x in columns[:110]],"separator",repr(sep),flush=True)
    except Exception as e:
        print("PROBE",label,"ERROR",type(e).__name__,str(e)[:240],flush=True)

def inspect_api(key,path,params):
    url="https://apidadosabertos.saude.gov.br"+path+"?"+urlencode(dict(params,limit=5,offset=0))
    try:
        import json
        with urlopen(Request(url,headers={"User-Agent":"WebGIS-Saude-Canoas/1.0","Accept":"application/json"}),timeout=25) as r: data=json.loads(r.read(250000))
        if isinstance(data,dict):
            rows=next((v for v in data.values() if isinstance(v,list)),[])
            print("PROBE",key,"payload_keys",list(data),"row_count",len(rows),"row_fields",list(rows[0]) if rows and isinstance(rows[0],dict) else [],flush=True)
            if rows and isinstance(rows[0],dict):
                print("PROBE",key,"municipal_ids",[{f:v for f,v in rows[0].items() if any(k in f for k in ('municip','ibge','nu_ano','nu_comp'))}],flush=True)
        else:print("PROBE",key,"payload_type",str(type(data)),flush=True)
    except Exception as e: print("PROBE",key,"ERROR",type(e).__name__,str(e)[:240],flush=True)

if __name__=="__main__":
    for key,url in files.items():inspect_zip(key,url)
    for key,path in [
      ("sia","/assistencia-a-saude/sia-procedimentos-ambulatoriais"),
      ("sih","/assistencia-a-saude/sih-procedimentos-hospitalares"),
      ("dengue_api","/arboviroses/dengue")
    ]:inspect_api(key,path,{"id_municip":"430460","co_ibge":430460,"nu_ano":2025})
