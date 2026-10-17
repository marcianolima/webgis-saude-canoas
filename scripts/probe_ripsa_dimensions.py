#!/usr/bin/env python3
"""Diagnóstico de dimensões oficiais MGDI e da tabela RIPSA AIH; sem dados pessoais."""
from scripts.sus_sources import CONFIG,download_records
for key in ('consultas_aps_razao','consultas_especializadas_razao','valor_medio_aih'):
 print('RIPSA_DIM',key,'START',flush=True)
 try:
  with download_records(CONFIG[key]) as (columns,rows):
   print('RIPSA_DIM',key,'FIELDS',columns,flush=True)
   found=0;by_category={};by_item={}
   seen={};seen_aih=set()
   for row in rows:
    if key=='valor_medio_aih':
     if len(seen_aih)<8:
      mn=str(row.get('municipio') or '')
      if mn and mn not in seen_aih:
       seen_aih.add(mn)
       print('RIPSA_DIM',key,'MUNIC_SAMPLE',{'municipio':mn,'ano':row.get('ano'),'indicador':row.get('indicador'),'multiplicador':row.get('multiplicador'),
         'total_internacoes':row.get('denominador - número de internaçoes hospitalares'),
         'total_pago':row.get('numerador - valor de internaçoes hospitalares')},flush=True)
     mun=str(row.get('municipio') or '')
     if 'CANOAS' not in mun.upper() and not mun.strip().startswith('430460'):continue
     found+=1
     if found<=12:
      print('RIPSA_DIM',key,'MATCH',{'municipio':mun,'ano':row.get('ano'),'indicador':row.get('indicador'),'multiplicador':row.get('multiplicador'),
       'internacoes':row.get('denominador - número de internaçoes hospitalares'),
       'valor':row.get('numerador - valor de internaçoes hospitalares')},flush=True)
     continue
    if str(row.get('co_ibge') or '').strip()!='430460':continue
    found+=1
    cat=str(row.get('sg_categoria') or '')
    item=str(row.get('co_item_categoria') or '')
    by_category[cat]=by_category.get(cat,0)+1
    by_item[item]=by_item.get(item,0)+1
    if found<=16:
     print('RIPSA_DIM',key,'MUNIC_SAMPLE',{'period':row.get('co_anomes'),'value':row.get('vl_indicador_calculado_mun'),
       'sg_categoria':cat,'ds_categoria':row.get('ds_categoria'),
       'co_item_categoria':item,'ds_item_categoria':row.get('ds_item_categoria')},flush=True)
   print('RIPSA_DIM',key,'END',{'municipal_rows':found,'category_counts':by_category,'item_sample':dict(list(by_item.items())[:15])},flush=True)
 except Exception as e:print('RIPSA_DIM',key,'ERROR',type(e).__name__,str(e)[:240],flush=True)
