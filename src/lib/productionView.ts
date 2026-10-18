import {safe,nf,fmtDate,urlAsset,dlCsv} from './utils';
import {selectedFacility} from './facilityExplorer';

type Count={quantity:number;valueBRL:number};
type MonthSource={rowsState:number;rowsCity:number;municipal:Count;byCnes:Record<string,Count>;suppressedUnits:number};
type Month={sih?:MonthSource;sia?:MonthSource};
type Source={label:string;status:string;monthsAvailable:string[];monthsRequested:number;monthsRequestedPeriods?:string[];rejectedMonths?:string[];reference:string|null;method:string;url:string;access:string;privacy:string};
type Snapshot={schemaVersion:string;generatedAt:string|null;periods:Record<string,Month>;sources:Record<string,Source>;geography:string};
let active=0;
let chart:any=null;
let ro:ResizeObserver|null=null;
const pretty=(period:string)=>period.length===6?period.slice(4)+'/'+period.slice(0,4):period;
const number=(value:number|null,format:string)=>value===null?'—':format==='valueBRL'?
 new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(value):nf(value);
const systems:[string,string][]=[['sih','Internações hospitalares · SIH/RD'],['sia','Procedimentos ambulatoriais · SIA/PA']];
export function stopProduction(){active++;ro?.disconnect();ro=null;chart?.dispose();chart=null;}
export function productionPage(){
 const current=selectedFacility();
 return '<section aria-label="Produção SIH/SIA">'+
 '<header class="mb-5"><p class="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300">DATASUS · SIH/RD e SIA/PA</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">Produção hospitalar e ambulatorial</h2>'+
 '<p class="ui-lead mt-2">Dados mensais do local de atendimento em Canoas. No SIH, são registros de AIH/RD; no SIA, quantidades de procedimentos aprovados PA. Não representam pacientes únicos, ocupação hospitalar ou a produção ambulatorial integral. Meses faltantes não são tratados como zero.</p></header>'+
 (current?'<div class="panel p-4 mb-4 text-sm"><strong>Unidade selecionada:</strong> '+safe(current.name)+' · CNES '+safe(current.cnes)+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-2">Selecione “Estabelecimento” para visualizar apenas seus agregados que atingiram o mínimo de divulgação. Dados suprimidos não significam produção zero.</p></div>':'')+
 '<div id="production-status" role="status" aria-live="polite" class="panel p-4 mb-4 text-sm">Carregando extratos oficiais…</div>'+
 '<div id="production-body" class="space-y-4"></div></section>';
}
export async function mountProduction(dark:boolean){
 const token=++active;
 const status=document.querySelector<HTMLElement>('#production-status');
 const body=document.querySelector<HTMLElement>('#production-body');
 if(!status||!body)return;
 try{
  const response=await fetch(urlAsset('data/production.json'),{cache:'no-cache'});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const data=await response.json() as Snapshot;
  if(!data||data.schemaVersion!=='1.0'||typeof data.periods!=='object'||typeof data.sources!=='object')
   throw new Error('Estrutura de produção incorreta');
  if(token!==active||!body.isConnected)return;
  const chosen=selectedFacility();
  const available=systems.filter(([k])=>(data.sources[k]?.monthsAvailable||[]).length>0);
  status.innerHTML='<div class="flex justify-between flex-wrap gap-2">'+
   '<strong>'+available.length+' de 2 sistemas com meses processados</strong>'+
   '<span class="text-xs text-slate-500 dark:text-slate-300">Atualizado: '+safe(fmtDate(data.generatedAt))+' · Município do estabelecimento</span></div>';
  body.innerHTML='<section class="grid grid-cols-1 sm:grid-cols-2 gap-4">'+systems.map(([k,label])=>{
    const source=data.sources[k];
    const count=source?.monthsAvailable?.length||0;
    const latest=source?.reference||'—';
    return '<article class="panel p-4"><h3 class="subheading text-base">'+label+'</h3>'+
     '<div class="text-2xl font-bold mt-3 tabular-nums">'+count+' <span class="text-sm font-normal text-slate-500">meses validados</span></div>'+
     '<p class="text-xs mt-2 text-slate-500 dark:text-slate-300">Última competência: '+safe(pretty(latest))+' · '+count+'/'+(source?.monthsRequested||'—')+' meses do intervalo</p>'+
     '<p class="text-xs mt-3 text-slate-500 dark:text-slate-300">'+safe(source?.method||'Arquivo ainda não disponível')+'</p><p class="text-xs font-semibold text-teal-700 dark:text-teal-300 mt-2">'+(count?'Dados parcialmente disponíveis':'Sem mês validado')+'</p></article>';
   }).join('')+'</section>'+
   '<section class="panel p-5"><div class="flex flex-wrap gap-3 items-end justify-between">'+
   '<div><h3 class="subheading text-base">Produção por competência</h3><p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Meses não coletados aparecem como indisponíveis. Nunca extrapolamos um total anual.</p></div>'+
   '<button id="production-export" type="button" class="text-xs px-3 py-2 border border-teal-200 rounded-lg text-teal-700 dark:text-teal-300 font-bold">Exportar CSV</button></div>'+
   '<div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">'+
   '<label class="text-xs font-semibold">Sistema <select id="production-system" class="field w-full mt-1"><option value="sih">SIH · Internações</option><option value="sia">SIA · Procedimentos</option></select></label>'+
   '<label class="text-xs font-semibold">Medida <select id="production-metric" class="field w-full mt-1"><option value="quantity">Quantidade</option><option value="valueBRL">Valor (R$)</option></select></label>'+
   '<label class="text-xs font-semibold">Abrangência <select id="production-scope" class="field w-full mt-1">'+
    '<option value="municipal">Município de Canoas</option>'+
    (chosen?'<option value="facility" selected>Estabelecimento · CNES '+safe(chosen.cnes)+'</option>':'')+
   '</select></label></div>'+
   '<div id="production-chart" role="img" aria-label="Gráfico de produção SUS por mês; utilize o controle inferior para navegar nas competências" style="height:340px;min-height:340px" class="mt-4"></div>'+
   '<p class="text-xs text-slate-500 dark:text-slate-300 mt-2">Arraste a barra inferior do gráfico ou deslize para consultar outros meses. “—” representa ausência ou supressão, não zero.</p><div id="production-notes" class="text-xs text-slate-500 dark:text-slate-300 mt-4"></div></section>'+
   '<section class="panel p-5"><h3 class="subheading text-base mb-3">Tabela e períodos de referência</h3>'+
   '<div id="production-table"></div></section>'+
   '<section class="panel p-5"><h3 class="subheading text-base mb-2">Metodologia, transparência e privacidade</h3>'+
   '<p class="text-sm text-slate-500 dark:text-slate-300">SIH/RD: registros de AIH e valores do atendimento hospitalar; não são pacientes únicos nem internações por residência. SIA/PA: procedimentos aprovados e valores correspondentes; não abrange todos os instrumentos ambulatoriais. O filtro municipal considera o local do estabelecimento. Para proteger grupos pequenos, valores por CNES podem ser omitidos sem reduzir o total municipal. Arquivos suspeitos são sinalizados e retirados da série. Acompanhe as competências disponíveis antes de comparar períodos.</p>'+
   '<a class="text-xs mt-3 inline-block font-semibold underline text-teal-700 dark:text-teal-300" href="https://datasus.saude.gov.br/assistencia-a-saude/" target="_blank" rel="noopener noreferrer">Fonte DATASUS ↗</a></section>';
  const echarts=await import('echarts');
  if(token!==active||!body.isConnected)return;
  function rows(){
   const system=(document.querySelector<HTMLSelectElement>('#production-system')?.value||'sih') as 'sih'|'sia';
   const kind=document.querySelector<HTMLSelectElement>('#production-metric')?.value||'quantity';
   const scope=document.querySelector<HTMLSelectElement>('#production-scope')?.value||'municipal';
   const periods=[...new Set([...(data.sources[system]?.monthsRequestedPeriods||[]),...Object.keys(data.periods),...(data.sources[system]?.monthsAvailable||[])])].sort();
   const records=periods.map(period=>{
    const doc=data.periods[period]?.[system];
    const value=doc?(scope==='facility'&&chosen?doc.byCnes?.[chosen.cnes]?.[kind as keyof Count]:doc.municipal[kind as keyof Count]):null;
    return {period,value:typeof value==='number'?value:null,hasSystem:Boolean(doc),quarantined:Boolean(data.sources[system]?.rejectedMonths?.includes(period))};
   });
   return {system,kind,scope,records};
  }
  function draw(){
   if(token!==active)return;
   const {system,kind,scope,records}=rows();
   chart?.dispose();chart=null;ro?.disconnect();ro=null;
   const target=document.getElementById('production-chart');
   if(!target)return;
   target.innerHTML='';
   const yColor=dark?'#a6b7c9':'#66778a';
   chart=echarts.init(target);
   const narrow=window.matchMedia('(max-width: 640px)').matches;
   const range=records.length>8?Math.max(0,100-100*(narrow?6:10)/records.length):0;
   chart.setOption({grid:{top:25,left:12,right:20,bottom:75,containLabel:true},
     tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
      valueFormatter:(v:number)=>v===null||v===undefined?'Sem dado':number(Number(v),kind)},
     dataZoom:[{type:'inside',start:range,end:100,zoomLock:false},
      {type:'slider',height:16,bottom:5,start:range,end:100,
       textStyle:{color:yColor,fontSize:10},borderColor:'transparent'}],
     xAxis:{type:'category',data:records.map(r=>pretty(r.period)),axisLabel:{color:yColor,rotate:narrow?45:25,hideOverlap:true,fontSize:10},axisTick:{show:false}},
     yAxis:{type:'value',axisLabel:{color:yColor,formatter:(v:number)=>new Intl.NumberFormat('pt-BR',{notation:'compact',maximumFractionDigits:1}).format(v)},splitLine:{lineStyle:{color:dark?'#30465d':'#eef2f6'}}},
     series:[{name:kind==='valueBRL'?'Valor em reais':system==='sih'?'AIHs RD':'Procedimentos PA',type:'bar',
       data:records.map(r=>r.value),barMaxWidth:60,itemStyle:{color:'#0d9488',borderRadius:[6,6,0,0]}}]});
   ro=new ResizeObserver(()=>chart?.resize());ro.observe(target);
   const table=document.querySelector<HTMLElement>('#production-table');
   if(table)table.innerHTML='<div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr class="text-xs text-slate-500 border-b border-slate-200 dark:border-slate-700"><th class="text-left py-2">Competência</th><th class="text-right py-2">Valor</th><th class="text-right py-2">Qualidade</th></tr></thead><tbody>'+
    records.map(r=>'<tr class="border-b border-slate-100 dark:border-slate-700"><td class="py-2">'+pretty(r.period)+'</td><td class="py-2 text-right font-semibold tabular-nums">'+number(r.value,kind)+'</td><td class="py-2 text-right text-xs text-slate-500">'+(r.value!==null?'Agregado validado':r.quarantined?'Arquivo em revisão de qualidade':r.hasSystem?'Não divulgado por CNES':'Mês não processado')+'</td></tr>').join('')+'</tbody></table></div>';
   const note=document.querySelector<HTMLElement>('#production-notes');
   if(note)note.textContent=(data.sources[system]?.method||'')+' · '+(scope==='municipal'?'Município de produção':'CNES '+chosen?.cnes)+
     ' · Meses em revisão de qualidade: '+(data.sources[system]?.rejectedMonths?.map(pretty).join(', ')||'nenhum')+
     ' · Unidade: '+(kind==='quantity'?(system==='sih'?'registros de AIH RD':'procedimentos aprovados PA'):'R$ aprovados/pagos')+'. Ausência de dado não representa zero.';
  }
  for(const id of ('#production-system,#production-metric,#production-scope').split(','))
   document.querySelector(id)?.addEventListener('change',draw);
  document.querySelector('#production-export')?.addEventListener('click',()=>{
    const {system,kind,scope,records}=rows();
    dlCsv(records.map(x=>({Sistema:system,Competencia:x.period,Medida:kind,
      Abrangencia:scope==='facility'?'CNES '+chosen?.cnes:'Canoas',Valor:x.value,
      Situacao:x.value!==null?'Validado':'Indisponível'})),
      'producao-sus-canoas-'+system+'-'+kind+'.csv');
  });
  draw();
 }catch(error){
  console.error('Produção SIH/SIA',error);
  if(token===active&&status.isConnected)status.textContent='Produção SIH/SIA ainda não disponível. Outros módulos municipais permanecem acessíveis.';
 }
}