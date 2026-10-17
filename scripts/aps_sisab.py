#!/usr/bin/env python3
"""SISAB/Previne Brasil: indicadores históricos municipais 2024Q1–Q3.

Utiliza exclusivamente a visão 'geral' de cada indicador; não mistura
visões de equipes, não produz métricas atuais do novo modelo de financiamento.
"""
import csv, io, json, logging, os, re, tempfile, urllib.request, zipfile
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public/data/aps.json"
LOG=logging.getLogger("webgis.sisab")
BASE="https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/sisab/indicador_desempenho/csv/"
FILES={period:BASE+"sisab_indicador_desempenho_"+period+".csv.zip"
       for period in ("2024Q1","2024Q2","2024Q3")}
DESCRIPTIONS={
 "10":("aps_prenatal","Pré-natal — acompanhamento das gestantes",
       "Indicador histórico 1 do Previne Brasil, medido em percentual conforme o dicionário e as regras do respectivo quadrimestre."),
 "20":("aps_gestantes_testes","Gestantes — exames de sífilis e HIV",
       "Indicador histórico 2 do Previne Brasil; percentual de acompanhamento conforme a metodologia vigente no período."),
 "30":("aps_gestantes_odontologia","Gestantes — atendimento odontológico",
       "Indicador histórico 3 do Previne Brasil; percentual de atendimento conforme o cadastro SISAB."),
 "40":("aps_citopatologico","Rastreamento citopatológico na APS",
       "Indicador histórico 4 de realização de exame citopatológico na população-alvo do Previne Brasil."),
 "50":("aps_vacinacao_infantil","Vacinação infantil — indicador APS",
       "Indicador histórico 5 de vacinação infantil do Previne Brasil; não equivale à cobertura vacinal PNI do município."),
 "60":("aps_hipertensao","Hipertensão — acompanhamento",
       "Indicador histórico 6 de acompanhamento de pessoas com hipertensão na APS."),
 "70":("aps_diabetes","Diabetes — acompanhamento",
       "Indicador histórico 7 de acompanhamento de pessoas com diabetes na APS.")
}
def number(value):
    text=str(value or "").strip().replace("%","")
    if "," in text and "." in text:text=text.replace(".","").replace(",",".")
    elif "," in text:text=text.replace(",",".")
    try:
        amount=Decimal(text)
        if not amount.is_finite():return None
        return amount
    except InvalidOperation:return None
def extract(rows,fields,period):
    required={"ibge","nu_competencia","ds_quadrimestre","co_tipo_indicador",
              "vl_perc_quad","visao_equipe","numerador","denominador_utilizador"}
    missing=required-set(fields)
    if missing:raise ValueError("SISAB: colunas ausentes: "+str(sorted(missing)))
    scanned=0;local=0;national=set();result={}
    for row in rows:
        scanned+=1
        ibge=str(row.get("ibge") or "").strip()
        if ibge:national.add(ibge)
        if ibge!="430460":continue
        local+=1
        if str(row.get("ds_quadrimestre") or "").strip()!=period:
            raise ValueError("SISAB: quadrimestre diferente do arquivo em Canoas")
        if str(row.get("visao_equipe") or "").strip().lower()!="geral":continue
        kind=str(row.get("co_tipo_indicador") or "").strip()
        if kind not in DESCRIPTIONS:continue
        percentage=number(row.get("vl_perc_quad"))
        numerator=number(row.get("numerador"))
        denominator=number(row.get("denominador_utilizador"))
        if percentage is None or not 0<=percentage<=100:
            raise ValueError("SISAB: indicador percentual fora da faixa")
        if numerator is None or denominator is None or denominator<=0 or numerator<0:
            raise ValueError("SISAB: numerador ou denominador inconsistente")
        if abs(percentage-numerator*100/denominator)>Decimal("4"):
            raise ValueError("SISAB: percentual incompatível com numerador/denominador")
        if kind in result:raise ValueError("SISAB: tipo duplicado na visão geral")
        result[kind]=round(float(percentage),2)
    if scanned<30000 or len(national)<200:raise ValueError("SISAB: extrato nacional incompleto")
    if local<6 or len(result)<5:raise ValueError("SISAB: cobertura municipal insuficiente")
    return result,{"scanned":scanned,"municipalRows":local,"municipalIndicators":len(result)}

def iter_csv(url):
    """Iterador cujo ZIP permanece aberto durante a leitura."""
    with tempfile.TemporaryDirectory(prefix="sisab-") as d:
        path=Path(d)/"archive.zip"
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"WebGIS-Saude-Canoas/1.4"}),timeout=120) as response,path.open("wb") as output:
            total=0
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>70*1024*1024:raise ValueError("SISAB: ZIP acima do limite 70 MiB")
                output.write(block)
        with zipfile.ZipFile(path) as archive:
            csv_files=[item for item in archive.infolist() if item.filename.lower().endswith(".csv")]
            if len(csv_files)!=1:raise ValueError("SISAB: quantidade de CSV inesperada")
            with archive.open(csv_files[0]) as raw:
                peek=raw.peek(4096)[:4096]
                try:peek.decode("utf-8-sig");encoding="utf-8-sig"
                except UnicodeDecodeError:encoding="cp1252"
                text=io.TextIOWrapper(raw,encoding=encoding,errors="replace",newline="")
                first=text.readline()
                sep=";" if first.count(";")>first.count(",") else ","
                header=[h.strip().lower() for h in next(csv.reader([first],delimiter=sep))]
                yield header,csv.DictReader(text,fieldnames=header,delimiter=sep)
def run():
    if OUT.exists():
        try:doc=json.loads(OUT.read_text(encoding="utf8"))
        except (OSError,ValueError):doc={}
    else:doc={}
    if doc.get("schemaVersion")!="1.0":
        doc={"schemaVersion":"1.0","updatedAt":None,"program":"Previne Brasil",
             "historicalOnly":True,"series":{},"sources":{}}
    collected=0
    for period,url in FILES.items():
        if any(any(row.get("period")==period for row in values) for values in doc["series"].values()):
            continue
        try:
            (fields,rows),=iter_csv(url)
            amounts,quality=extract(rows,fields,period)
            for code,value in amounts.items():
                key,label,method=DESCRIPTIONS[code]
                doc["series"].setdefault(key,[]).append({"period":period,"value":value})
                doc["sources"][key]={
                    "label":label,"status":"ok","reference":period,
                    "method":method+" Série histórica descontinuada: financiamento APS mudou em 2024.",
                    "url":"https://dadosabertos.saude.gov.br/dataset/indicadores_desempenho_sisab",
                    "unit":"%","kind":"rate","cadence":"quadrimestral",
                    "retrievedAt":datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "historicalOnly":True}
            collected+=1
            LOG.info("SISAB %s: %d indicadores de Canoas; %d registros nacionais",
                     period,len(amounts),quality["scanned"])
        except Exception as e:
            LOG.warning("SISAB %s: coleta não validada: %s",period,str(e)[:150])
    for values in doc["series"].values():values.sort(key=lambda r:r["period"])
    if collected:doc["updatedAt"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    target=OUT.with_suffix(".json.tmp")
    target.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n",encoding="utf8")
    os.replace(target,OUT)
    if not doc["series"]:raise RuntimeError("Nenhum indicador histórico SISAB validado")
if __name__=="__main__":
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    run()
