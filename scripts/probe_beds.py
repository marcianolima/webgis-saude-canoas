#!/usr/bin/env python3
"""Diagnóstico sem dados individuais: inspeciona o esquema do CSV anual de leitos."""
import csv, io, logging, tempfile, zipfile
from pathlib import Path
from urllib.request import Request,urlopen

SOURCE="https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/Leitos_SUS/Leitos_csv_2026.zip"

def run():
    with tempfile.TemporaryDirectory(prefix="webgis-leitos-probe-") as folder:
        target=Path(folder)/"beds.zip"
        req=Request(SOURCE,headers={"User-Agent":"WebGISSaudeCanoas/1.3 (dados abertos)"})
        total=0
        with urlopen(req,timeout=240) as response, target.open("wb") as fd:
            while True:
                data=response.read(1024*1024)
                if not data:break
                total+=len(data)
                if total>200*1024*1024:raise ValueError("ZIP acima do limite 200 MiB")
                fd.write(data)
        if not zipfile.is_zipfile(target):raise ValueError("Recurso de leitos não é ZIP")
        print("LEITOS_DIAG bytes_zip=",total,flush=True)
        with zipfile.ZipFile(target) as archive:
            members=[x for x in archive.infolist() if x.filename.lower().endswith(".csv")]
            print("LEITOS_DIAG membros_csv=",[(x.filename,x.file_size) for x in members[:15]],flush=True)
            for item in members[:3]:
                with archive.open(item) as raw:
                    preview=raw.peek(32768)[:32768]
                    enc="utf-8-sig"
                    try:preview.decode(enc)
                    except UnicodeDecodeError:enc="cp1252"
                    txt=io.TextIOWrapper(raw,encoding=enc,errors="replace",newline="")
                    line=txt.readline()
                    if not line:continue
                    sep=";" if line.count(";")>line.count(",") else ","
                    headers=next(csv.reader([line],delimiter=sep))
                    print("LEITOS_DIAG schema",item.filename,"separator",repr(sep),"encoding",enc,"fields",headers,flush=True)
                    reader=csv.DictReader(txt,fieldnames=headers,delimiter=sep)
                    candidates=[]
                    scanned=0
                    for record in reader:
                        scanned+=1
                        normalized={str(k).strip().lower():v for k,v in record.items() if k}
                        municipality=next((normalized[k] for k in ["co_ibge","codigo_municipio","co_municipio_gestor","ibge"] if normalized.get(k)),None)
                        if municipality and str(municipality).split(".")[0] in ("430460","4304606"):
                            candidates.append({k:v for k,v in normalized.items() if ("comp" in k or "leito" in k or "qt_" in k or "cnes" in k or k in ("co_ibge","tp_unidade"))})
                            if len(candidates)>=2:break
                        if scanned>=200000:break
                    print("LEITOS_DIAG amostra_canoas",item.filename,"linhas_lidas",scanned,"valores_numericos",candidates,flush=True)

if __name__=="__main__":run()
