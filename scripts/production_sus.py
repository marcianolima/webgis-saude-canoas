#!/usr/bin/env python3
"""SIH-RD e SIA-PA no município de produção: agregados a partir de Parquet PySUS.

NUNCA publica linhas individuais nem identificadores pessoais. A cobertura
temporal é explicitamente limitada aos meses integralmente processados.
"""
import json, logging, os, re, tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

LOG=logging.getLogger("webgis.production")
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public/data/production.json"
MIN_UNIT_COUNT=5
COLUMNS={
 "sih":("MUNIC_MOV","CNES","VAL_TOT","MORTE"),
 "sia":("PA_UFMUN","PA_CODUNI","PA_QTDAPR","PA_VALAPR")
}
SOURCE_LABELS={
 "sih":"SIH/SUS — AIHs RD por município de internação",
 "sia":"SIA/SUS — produção aprovada PA por município do estabelecimento"
}
METHODS={
 "sih":"Contagem de registros de AIH reduzida (RD) e soma de VAL_TOT no mês de competência, por município do hospital; não representa pacientes únicos ou internações por residência.",
 "sia":"Quantidade de procedimentos aprovados PA_QTDAPR e soma de PA_VALAPR na competência, por município do estabelecimento; não representa pacientes únicos nem produção SIA integral de todos os instrumentos."
}
def now():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def code7(value):
    value=str(value or "").strip().split(".")[0]
    return value.zfill(7) if value.isdigit() and 1<=len(value)<=7 else None
def is_canoas(value):
    return str(value or "").strip().split(".")[0] in ("430460","4304606")
def money(raw):
    text=str(raw or "0").strip()
    if "," in text and "." not in text:text=text.replace(",",".")
    try:
        amount=Decimal(text)
        if not amount.is_finite() or amount<0:raise ValueError("Valor monetário inválido")
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation as exc:raise ValueError("Valor monetário inválido") from exc
def int_value(raw):
    try:
        value=Decimal(str(raw or "0").strip())
        if value<0 or value!=value.to_integral_value() or not value.is_finite():
            raise ValueError("Quantidade inválida")
        return int(value)
    except InvalidOperation as exc:raise ValueError("Quantidade inválida") from exc
def aggregate_rows(rows,system):
    """Agrupa exclusivamente municipio de PRODUÇÃO; nenhum microdado sai daqui."""
    if system not in ("sih","sia"):raise ValueError("Sistema desconhecido")
    city_records=0; read=0;total_qty=0;total_brl=Decimal(0);by_code=defaultdict(lambda:[0,Decimal(0)])
    for row in rows:
        read+=1
        if system=="sih":
            if not is_canoas(row.get("MUNIC_MOV")):continue
            code=code7(row.get("CNES"))
            qty=1
            val=money(row.get("VAL_TOT"))
        else:
            if not is_canoas(row.get("PA_UFMUN")):continue
            code=code7(row.get("PA_CODUNI"))
            qty=int_value(row.get("PA_QTDAPR"))
            val=money(row.get("PA_VALAPR"))
        city_records+=1
        total_qty+=qty
        total_brl+=val
        if code:
            by_code[code][0]+=qty
            by_code[code][1]+=val
    if read<500 or city_records<5:raise ValueError("Extrato estadual incompleto ou Canoas ausente")
    if total_qty<1:raise ValueError("Produção aprovada sem quantidades positivas")
    # Evita publicar grupos de produção individual potencialmente reidentificáveis.
    units={c:{"quantity":n,"valueBRL":float(v)} for c,(n,v) in by_code.items() if n>=MIN_UNIT_COUNT}
    return {"rowsState":read,"rowsCity":city_records,
            "municipal":{"quantity":total_qty,"valueBRL":float(total_brl)},
            "byCnes":units,"suppressedUnits":sum(n<MIN_UNIT_COUNT for n,_ in by_code.values())}

def batch_rows(parquet,columns):
    for batch in parquet.iter_batches(batch_size=20000,columns=list(columns)):
        data=batch.to_pydict()
        for idx in range(batch.num_rows):
            yield {name:data[name][idx] for name in columns}
def fetch_parquet(system,period):
    """Consulta o catálogo público S3 do PySUS, baixa só RD/PA, nunca DBC FTP."""
    import pysus
    import pyarrow.parquet as pq
    year,month=int(period[:4]),int(period[4:])
    prefix=("RDRS" if system=="sih" else "PARS")+period[2:]
    bag=getattr(pysus.ftp,system)(state="RS",year=year,month=month,download=False)
    options=list(bag)
    matching=[i for i,item in enumerate(options) if prefix in str(item).upper()]
    if len(matching)!=1:raise ValueError("Arquivo mensal RD/PA ausente ou duplicado: "+prefix)
    local=bag.download_one(matching[0])
    paths=[]
    # PySUS FileBag.download_one retorna objeto Parquet com atributo .path;
    # esse objeto é iterável, mas a iteração NÃO representa arquivos.
    single=getattr(local,"path",None)
    if single is not None and Path(str(single)).exists():
        paths=[Path(str(single))]
    elif isinstance(local,(list,tuple)):paths=[Path(str(getattr(x,"path",x))) for x in local]
    elif hasattr(local,"__iter__") and not isinstance(local,(str,bytes)):
        paths=[Path(str(getattr(x,"path",x))) for x in local]
    elif local:paths=[Path(str(getattr(local,"path",local)))]
    paths=[p for p in paths if p.exists() and p.suffix==".parquet"]
    if len(paths)!=1:
        # FileBag.download_one pode retornar um wrapper iterable; os bytes
        # ficam no cache público definido pelo próprio PySUS.
        cache=Path(os.environ.get("PYSUS_CACHEPATH","/tmp"))
        paths=[p for p in cache.rglob("*.parquet") if prefix.upper() in p.name.upper()]
    if len(paths)!=1:raise ValueError("Parquet local ausente ou não único: "+prefix)
    parquet=pq.ParquetFile(paths[0])
    required=set(COLUMNS[system])
    if not required.issubset(parquet.schema.names):
        raise ValueError("Colunas necessárias ausentes: "+str(sorted(required-set(parquet.schema.names))))
    if parquet.metadata.num_rows<500:raise ValueError("Arquivo estadual muito pequeno")
    return aggregate_rows(batch_rows(parquet,COLUMNS[system]),system)

def load():
    try:
        state=json.loads(OUT.read_text(encoding="utf8"))
        if state.get("schemaVersion")=="1.0":return state
    except (OSError,ValueError):pass
    return {"schemaVersion":"1.0","generatedAt":None,"geography":"município do estabelecimento/procedimento",
            "periods":{},"sources":{}}
def periods():
    raw=os.getenv("PRODUCTION_PERIODS","").strip()
    if raw:
        found=raw.split(",")
    else:
        # Jan–Dez de 2025 e Jan–Set de 2026; execução incremental limitada.
        found=[f"2025{m:02d}" for m in range(1,13)]+[f"2026{m:02d}" for m in range(1,10)]
    result=[]
    for p in found:
        if not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])",p):
            raise ValueError("Competência inválida: "+p)
        if p not in result:result.append(p)
    return result
def save(state):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n",encoding="utf8")
    os.replace(temp,OUT)
def run():
    state=load()
    wanted=periods()
    limit=int(os.getenv("PRODUCTION_MAX_DOWNLOADS","6"))
    limit=max(1,min(limit,42))
    force=os.getenv("PRODUCTION_FORCE","false").lower()=="true"
    processed=0
    attempted=0
    for period in wanted:
        for system in ("sih","sia"):
            existing=state["periods"].get(period,{}).get(system)
            if existing and not force:continue
            if attempted>=limit:break
            attempted+=1
            try:
                with tempfile.TemporaryDirectory(prefix="production-pysus-") as root:
                    os.environ["PYSUS_CACHEPATH"]=root
                    result=fetch_parquet(system,period)
                state["periods"].setdefault(period,{})[system]=result
                processed+=1
                LOG.info("PRODUCTION %s %s OK: registros municipais %d, quantidade %d, R$ %.2f",
                    system,period,result["rowsCity"],result["municipal"]["quantity"],
                    result["municipal"]["valueBRL"])
            except Exception as exc:
                LOG.warning("PRODUCTION %s %s FAILED: %s",system,period,str(exc)[:190])
                # Não marca sucesso nem publica zero. Próxima execução tentará novamente.
            # Não bloquear o processamento de fontes disponíveis se outra fonte falhar.
        if attempted>=limit:break
    for system in ("sih","sia"):
        available=[p for p in sorted(wanted) if system in state["periods"].get(p,{})]
        state["sources"][system]={
            "label":SOURCE_LABELS[system],
            "status":"ok" if len(available)==len(wanted) else "partial" if available else "not_loaded",
            "monthsAvailable":available,"monthsRequested":len(wanted),"method":METHODS[system],
            "reference":available[-1] if available else None,
            "url":"https://datasus.saude.gov.br/assistencia-a-saude/",
            "access":"PySUS 2.11.7; catálogo público Parquet S3, apenas RD/PA",
            "privacy":"Sem registros individuais; suprimir grupos CNES com menos de 5 unidades de produção"
        }
    if processed:state["generatedAt"]=now()
    save(state)
    LOG.info("PRODUCTION finished: %d novos arquivos. SIH %d meses; SIA %d meses",
        processed,len(state["sources"]["sih"]["monthsAvailable"]),
        len(state["sources"]["sia"]["monthsAvailable"]))
    if not any(state["sources"][k]["monthsAvailable"] for k in ("sih","sia")):
        raise RuntimeError("Nenhum mês de produção SIH/SIA validado")
if __name__=="__main__":
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    run()
