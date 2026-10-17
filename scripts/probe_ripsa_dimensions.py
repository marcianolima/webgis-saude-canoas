#!/usr/bin/env python3
"""Diagnóstico de cardinalidade de dados oficiais agregados, sem valores pessoais."""
from scripts.sus_sources import CONFIG,download_records,decimal_value
for key in ('consultas_aps_razao','consultas_especializadas_razao','valor_medio_aih'):
    print('RIPSA_PROBE',key,'START',flush=True)
    try:
        with download_records(CONFIG[key]) as (fields,rows):
            print('RIPSA_PROBE',key,'columns',fields,flush=True)
            samples=[];distinct={};count=0
            for row in rows:
                count+=1
                if str(row.get('co_ibge') or '').strip()!='430460':continue
                period=str(row.get('co_anomes') or '')
                val=str(row.get('vl_indicador_calculado_mun') or '')
                if len(samples)<4:samples.append({'period':period,'value':val,
                    'granularidade':row.get('sg_granularidade'),'ds_granularidade':row.get('ds_granularidade'),
                    'region_code':row.get('co_regiao_saude'),'year':row.get('co_ano')})
                if period and val:
                    previous=distinct.get(period)
                    if previous and previous!=val:
                        print('RIPSA_PROBE',key,'conflict',{'period':period,'previous':previous,'current':val,
                            'granularidade':row.get('sg_granularidade'),'ds_granularidade':row.get('ds_granularidade')},flush=True)
                        if len(samples)>10:break
                    else: distinct[period]=val
                if len(distinct)>250 or count>1_800_000:break
            print('RIPSA_PROBE',key,'read',count,'samples',samples,'periods',len(distinct),flush=True)
    except Exception as e:
        print('RIPSA_PROBE',key,'error',str(e)[:250],flush=True)
