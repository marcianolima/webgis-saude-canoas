#!/usr/bin/env python3
"""Sondagem do espelho estadual PNI; expõe apenas estrutura do arquivo e volume."""
import os,tempfile
from pathlib import Path
def probe():
 import pysus
 for year in (2025,2026):
  try:
   bag=pysus.ftp.pni(state="RS",year=year,download=False)
   items=list(bag)
   print("PNI_PROBE YEAR",year,"FILES",len(items),"PATHS",[str(x)[:190] for x in items[:3]],flush=True)
  except Exception as exc:print("PNI_PROBE YEAR",year,"ERROR",type(exc).__name__,str(exc)[:200],flush=True)
if __name__=="__main__":
 with tempfile.TemporaryDirectory(prefix="pni-parquet-") as folder:
  os.environ["PYSUS_CACHEPATH"]=folder
  probe()
