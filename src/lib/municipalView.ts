import {safe,nf,fmtDate,urlAsset} from './utils';
import type {DataSummary} from './types';

type Annual={year:number;value:number;provisional?:boolean};
type Month={period:string;value:number};
type Origin={label:string;status:string;url?:string;note?:string;method?:string;unit?:string;kind?:string;cadence?:string;reference?:string};
type Health={updatedAt:string|null;series:Record<string,Annual[]>;sources:Record<string,Origin>;definitions:Record<string,string>};
type SUS={updatedAt:string|null;series:Record<string,Month[]>;sources:Record<string,Origin>};
type APS={updatedAt:string|null;series:Record<string,Month[]>;sources:Record<string,Origin>};
type Selection={label:string;key:string;section:'health'|'sus'|'aps';value:number;reference:string;unit:string;kind:string;notes:string;source?:string;series:{period:string;value:number}[];provisional?:boolean};
const display=(value:number|null|undefined,kind='count')=>{
 if(value===null||value===undefined||!Number.isFinite(value))return '—';
 if(kind==='currency')return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:2}).format(value);
 if(kind==='rate')return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(value);
 if(kind==='rate')return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(value);
 return nf(value);
};
const stamp=(text:string)=>text.length===6?text.slice(4,6)+'/'+text.slice(0,4):text;
let live=0;
let plot:any=null;
let obs:ResizeObserver|null=null;
let stored:{health:Health|null;sus:SUS|null;aps:APS|null}|null=null;
export function stopMunicipal(){live++;obs?.disconnect();obs=null;plot?.dispose();plot=null;}
export function municipalPage(summary:DataSummary){
 const population=summary.municipality;
 const kpi=(title:string,value:string,unit:string,source:string)=>
  '<article class="panel p-4 sm:p-5"><p class="text-xs font-semibold text-slate-500 dark:text-slate-300">'+title+'</p>'+
  '<p class="kpi-val mt-2">'+value+'</p><p class="text-xs text-slate-500 dark:text-slate-300 mt-1">'+safe(unit)+'</p>'+
  '<p class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 text-[11px] text-slate-400">'+safe(source)+'</p></article>';
 return '<section aria-label="Painel Municipal de Saúde de Canoas">'+
 '<header class="mb-5"><p class="text-xs font-bold uppercase tracking-[.13em] text-teal-700 dark:text-teal-300">Canoas / RS · Município IBGE '+safe(population.ibge)+'</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">Painel Municipal de Saúde</h2>'+
 '<p class="text-sm text-slate-500 dark:text-slate-300 max-w-3xl mt-2">Visão consolidada e independente dos estabelecimentos: demografia, rede assistencial, vigilância, estatísticas vitais, Atenção Primária, rastreamento e financiamento. Clique em um indicador para analisar sua evolução.</p></header>'+
 '<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 mb-5" aria-label="Números gerais de Canoas">'+
 kpi('População',display(population.population??population.censusPopulation),'habitantes · '+(population.populationYear||population.censusYear||'—'),'IBGE · estimativa populacional')+
 kpi('Estabelecimentos de saúde',display(summary.facilities.total),'inclui prestadores públicos e privados','CNES · '+(summary.facilities.asOf||'sem data'))+
 kpi('Unidades básicas',display(summary.facilities.ubs),'classificadas pelo tipo CNES','CNES · retrato cadastral')+
 kpi('Hospitais',display(summary.facilities.hospitals),'inclui hospital-dia','CNES · retrato cadastral')+
 kpi('Leitos existentes',display(summary.beds.total),'estoque cadastral','CNES · competência '+stamp(summary.beds.asOf||'—'))+
 kpi('Leitos SUS',display(summary.beds.sus),'parcela do estoque existente','CNES · competência '+stamp(summary.beds.asOf||'—'))+
 kpi('Com geolocalização',display(summary.facilities.withCoordinates),'estabelecimentos com coordenadas','CNES · não é cobertura territorial')+
 kpi('Área territorial',display(population.areaKm2,'rate'),'km²','IBGE · área municipal')+
 '</div>'+
 '<section class="panel p-4 sm:p-5 mb-5" aria-label="Indicadores por área"><div class="flex flex-wrap justify-between items-start gap-3"><div>'+
 '<h3 class="subheading text-lg">Indicadores municipais por tema</h3>'+
 '<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Cada número informa período, unidade e origem. Ausência de dados não representa zero.</p></div>'+
 '<div id="municipal-status" role="status" aria-live="polite" class="text-xs text-slate-500 dark:text-slate-300">Carregando bases oficiais…</div></div>'+
 '<div id="municipal-indicator-list" class="mt-4 space-y-5"></div></section>'+
 '<section class="grid grid-cols-1 xl:grid-cols-12 gap-4 mb-5" aria-label="Evolução do indicador municipal">'+
 '<article class="panel p-5 xl:col-span-8"><div class="flex items-start justify-between gap-2 flex-wrap mb-2"><div><h3 class="subheading text-base">Evolução do indicador selecionado</h3>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Selecione um cartão acima; as grandezas não são combinadas em um único eixo.</p></div>'+
 '<span id="municipal-plot-source" class="text-xs text-teal-700 dark:text-teal-300"></span></div>'+
 '<h4 id="municipal-plot-title" class="font-semibold text-sm my-3">Selecione um indicador para explorar</h4>'+
 '<div id="municipal-chart" role="img" aria-label="Série temporal municipal" style="height:310px;min-height:310px"></div>'+
 '<p id="municipal-method" class="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-300"></p></article>'+
 '<article class="panel p-5 xl:col-span-4"><h3 class="subheading text-base mb-3">Valores por referência</h3><div id="municipal-table"></div></article></section>'+
 '<section class="panel p-5 mb-5"><div class="flex justify-between gap-3 items-start flex-wrap"><div><h3 class="subheading text-base">Fontes ainda em integração</h3>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Pendências de acesso e validação não são escondidas.</p></div>'+
 '<button type="button" data-page="sources" class="text-xs font-bold text-teal-700 dark:text-teal-300 underline">Metodologia →</button></div>'+
 '<div id="municipal-pending" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3"></div></section>'+
 '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">'+
 '<button type="button" data-page="overview" class="panel p-4 text-left text-sm font-semibold text-teal-700 dark:text-teal-300">Analisar o território e CNES →</button>'+
 '<button type="button" data-page="health" class="panel p-4 text-left text-sm font-semibold text-teal-700 dark:text-teal-300">Vigilância e estatísticas vitais →</button>'+
 '<button type="button" data-page="sus" class="panel p-4 text-left text-sm font-semibold text-teal-700 dark:text-teal-300">Assistência e financiamento SUS →</button>'+ '<button type="button" data-page="production" class="panel p-4 text-left text-sm font-semibold text-teal-700 dark:text-teal-300">Produção mensal SIH/SIA →</button></div>'+
 '</section>';
}
const healthLabels:Record<string,string>={
 dengue:'Dengue · notificações de residentes',chikungunya:'Chikungunya · notificações de residentes',
 zika:'Zika · notificações de residentes',sinasc:'Nascidos vivos',sim:'Óbitos não fetais'};
const susOrder=['emulti_custeadas','emulti_homologadas','emulti_repasses','citopatologicos','mamografias','consultas_aps_razao','consultas_especializadas_razao','sih_internacoes_anuais','valor_medio_aih'];
const sourcePeriod=(row:Month,source?:Origin)=>
 source?.cadence==='annual'?row.period.slice(0,4)+(row.period.slice(4,6)==='12'?'':' · referência '+row.period.slice(4,6)):stamp(row.period);
function buildMetrics(health:Health|null,sus:SUS|null,aps:APS|null):Selection[]{
 const values:Selection[]=[];
 if(health)for(const id of ['dengue','chikungunya','zika','sinasc','sim']){
  const rows=(health.series[id]||[]).slice().sort((a,b)=>a.year-b.year);
  const src=health.sources[id];
  if(src?.status!=='ok'&&src?.status!=='partial')continue;
  const last=rows[rows.length-1];if(!last)continue;
  values.push({label:healthLabels[id],key:id,section:'health',value:last.value,reference:String(last.year),
   unit:id==='sinasc'?'nascidos vivos':id==='sim'?'óbitos':'notificações',kind:'count',
   notes:health.definitions?.[id]||src.note||'',source:src.url,
   series:rows.map(r=>({period:String(r.year),value:r.value})),provisional:last.provisional});
 }
 if(sus)for(const id of susOrder){
  const rows=(sus.series[id]||[]).slice().sort((a,b)=>a.period.localeCompare(b.period));
  const src=sus.sources[id];
  if(src?.status!=='ok')continue;
  const last=rows[rows.length-1];if(!last)continue;
  values.push({label:src.label,key:id,section:'sus',value:last.value,
   reference:sourcePeriod(last,src),unit:src.unit||'indicador',kind:src.kind||'count',
   notes:src.method||'',source:src.url,series:rows.map(r=>({period:sourcePeriod(r,src),value:r.value}))});
 }
 if(aps)for(const [id,src] of Object.entries(aps.sources||{})){
  const rows=(aps.series?.[id]||[]).slice().sort((a,b)=>a.period.localeCompare(b.period));
  if(src?.status!=='ok'||!rows.length)continue;
  const last=rows[rows.length-1];
  values.push({label:src.label,key:id,section:'aps',value:last.value,
   reference:last.period,unit:src.unit||'%',kind:'rate',notes:src.method||'Indicador histórico Previne Brasil.',
   source:src.url,series:rows.map(r=>({period:r.period,value:r.value}))});
 }
 return values;
}
function indicatorCard(row:Selection){
 const state=row.provisional?' · preliminar':'';
 return '<button type="button" data-municipal-metric="'+safe(row.key)+'" data-municipal-group="'+row.section+'" '+
 'class="text-left rounded-xl border border-slate-200 dark:border-slate-700 p-4 focus-visible:ring-2 focus-visible:ring-teal-500 hover:border-teal-400">'+
 '<span class="block text-xs font-semibold text-slate-600 dark:text-slate-300">'+safe(row.label)+'</span>'+
 '<span class="block mt-2 text-xl font-bold tabular-nums">'+display(row.value,row.kind)+'</span>'+
 '<span class="block mt-1 text-xs text-slate-500 dark:text-slate-300">'+safe(row.unit)+' · '+safe(row.reference+state)+'</span>'+
 '<span class="block mt-2 text-[11px] font-semibold text-teal-700 dark:text-teal-300">Ver evolução →</span></button>';
}
const stages:{name:string;keys:string[]}[]=[
 {name:'Vigilância epidemiológica',keys:['dengue','chikungunya','zika']},
 {name:'Natalidade e mortalidade',keys:['sinasc','sim']},
 {name:'Atenção Primária e financiamento',keys:['emulti_custeadas','emulti_homologadas','emulti_repasses','consultas_aps_razao','consultas_especializadas_razao']},
 {name:'Assistência hospitalar · RIPSA',keys:['sih_internacoes_anuais','valor_medio_aih']},
 {name:'Prevenção e rastreamento',keys:['citopatologicos','mamografias']},
 {name:'Atenção Primária · Previne Brasil (histórico até 2024)',keys:['aps_prenatal','aps_gestantes_testes','aps_gestantes_odontologia','aps_citopatologico','aps_vacinacao_infantil','aps_hipertensao','aps_diabetes']}
];
export async function mountMunicipal(dark:boolean){
 const nonce=++live;
 const status=document.getElementById('municipal-status'),cards=document.getElementById('municipal-indicator-list');
 const pending=document.getElementById('municipal-pending');
 if(!status||!cards||!pending)return;
 try{
  if(!stored){
   const load=async(path:string)=>{
    const result=await fetch(urlAsset('data/'+path),{cache:'no-cache'});
    if(!result.ok)throw new Error(path+' HTTP '+result.status);
    return result.json();
   };
   const [h,s,a]=await Promise.allSettled([load('indicators.json'),load('sus.json'),load('aps.json')]);
   stored={health:h.status==='fulfilled'?h.value as Health:null,sus:s.status==='fulfilled'?s.value as SUS:null,aps:a.status==='fulfilled'?a.value as APS:null};
  }
  if(nonce!==live||!cards.isConnected)return;
  const metrics=buildMetrics(stored.health,stored.sus,stored.aps);
  status.textContent=metrics.length+' séries municipais com extração validada';
  cards.innerHTML=stages.map(group=>{
   const entries=group.keys.map(key=>metrics.find(m=>m.key===key)).filter((m):m is Selection=>Boolean(m));
   const missing=group.keys.filter(k=>!metrics.some(m=>m.key===k)).length;
   return '<section><h4 class="subheading text-sm mb-3">'+group.name+
    '<span class="text-xs ml-2 text-slate-400 font-normal">'+entries.length+' disponíveis'+(missing?' · '+missing+' pendente(s)':'')+'</span></h4>'+
    '<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">'+entries.map(indicatorCard).join('')+
    (entries.length?'':'<div class="text-sm text-slate-500 dark:text-slate-300">Fonte ainda não validada para Canoas.</div>')+'</div></section>';
  }).join('');
  const sources=[...(stored.health?Object.entries(stored.health.sources):[]),...(stored.sus?Object.entries(stored.sus.sources):[]),...(stored.aps?Object.entries(stored.aps.sources):[])]
   .filter(([key,s])=>!metrics.some(m=>m.key===key)&&(s.status==='not_loaded'||s.status==='error'||s.status==='partial'));
  const unique=new Map<string,Origin>();
  for(const [key,s] of sources)if(!unique.has(key))unique.set(key,s);
  pending.innerHTML=[...unique].map(([key,s])=>'<article class="rounded-xl border border-slate-200 dark:border-slate-700 p-3">'+
   '<div class="text-sm font-semibold">'+safe(s.label||key)+'</div><p class="mt-1 text-xs text-slate-500 dark:text-slate-300">'+
   safe(s.note||s.method||'Extração municipal ainda não validada.')+'</p></article>').join('')||
   '<p class="text-sm text-slate-500">Não há novas pendências registradas.</p>';
  const ec=await import('echarts');
  if(nonce!==live||!cards.isConnected)return;
  const renderPlot=(record:Selection)=>{
   const target=document.getElementById('municipal-chart');
   if(!target)return;
   plotCleanup();target.innerHTML='';
   document.getElementById('municipal-plot-title')!.textContent=record.label;
   document.getElementById('municipal-method')!.textContent=record.notes+
    ' · Série municipal. Não é produção atribuída ao CNES selecionado.';
   const source=document.getElementById('municipal-plot-source');
   if(source)source.innerHTML=record.source?'<a href="'+safe(record.source)+'" target="_blank" rel="noopener noreferrer" class="underline">Fonte oficial ↗</a>':'Fonte oficial';
   const table=document.getElementById('municipal-table');
   if(table)table.innerHTML='<div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr class="text-xs text-slate-500 border-b border-slate-200 dark:border-slate-700"><th class="text-left py-2">Período</th><th class="text-right py-2">Valor</th></tr></thead><tbody>'+
    record.series.slice().reverse().map(v=>'<tr class="border-b border-slate-100 dark:border-slate-700"><td class="py-2">'+safe(v.period)+'</td><td class="py-2 text-right font-semibold tabular-nums">'+display(v.value,record.kind)+'</td></tr>').join('')+'</tbody></table></div>';
   document.querySelectorAll<HTMLElement>('[data-municipal-metric]').forEach(e=>e.classList.toggle('ring-2',e.dataset.municipalMetric===record.key));
   if(!record.series.length){target.innerHTML='Sem dados por período.';return}
   plot=ec.init(target);
   const muted=dark?'#9db3c5':'#64748b';
   plot.setOption({animationDuration:280,grid:{top:18,left:12,right:16,bottom:50,containLabel:true},
    tooltip:{trigger:'axis',valueFormatter:(value:number)=>display(Number(value),record.kind)},
    xAxis:{type:'category',data:record.series.map(x=>x.period),axisLabel:{color:muted,rotate:35},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color:muted},splitLine:{lineStyle:{color:dark?'#32475a':'#edf2f6'}}},
    series:[{type:record.series.length<=3?'bar':'line',smooth:true,barMaxWidth:72,
      lineStyle:{color:'#0d9488',width:3},itemStyle:{color:'#0d9488'},data:record.series.map(x=>x.value)}]});
   obs=new ResizeObserver(()=>plot?.resize());obs.observe(target);
  };
  function plotCleanup(){obs?.disconnect();obs=null;plot?.dispose();plot=null}
  cards.addEventListener('click',event=>{
   const button=(event.target as HTMLElement).closest<HTMLElement>('[data-municipal-metric]');
   if(!button)return;
   const found=metrics.find(m=>m.key===button.dataset.municipalMetric&&m.section===button.dataset.municipalGroup);
   if(found){renderPlot(found);document.getElementById('municipal-plot-title')?.scrollIntoView({behavior:'smooth',block:'nearest'});}
  });
  if(metrics.length)renderPlot(metrics.find(m=>m.key==='dengue')||metrics[0]);
  else document.getElementById('municipal-chart')!.innerHTML='<div class="empty p-5">Séries adicionais indisponíveis. Os dados demográficos e CNES permanecem no painel.</div>';
 }catch(error){
  console.error('Painel municipal',error);
  if(nonce===live&&status.isConnected)status.textContent='Algumas bases municipais não responderam. Os indicadores IBGE e CNES continuam disponíveis.';
 }
}
