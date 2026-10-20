import {safe,nf,fmtDate,urlAsset} from './utils';
import type {DataSummary} from './types';

type Entry={year:number;value:number;provisional?:boolean;scanned:number;breakdown:Record<string,number>};
type Source={label:string;url:string;status:string;note:string;retrievedAt:string|null};
type Snapshot={updatedAt:string|null;series:Record<string,Entry[]>;sources:Record<string,Source>;definitions:Record<string,string>};
const LABELS:Record<string,string>={dengue:'Notificações de dengue',chikungunya:'Chikungunya',zika:'Zika',sinasc:'Nascidos vivos',sim:'Óbitos não fetais',sia:'Produção ambulatorial',sih:'Produção hospitalar'};
let active=0;
let instance:any=null;
let resize:ResizeObserver|null=null;
export function disposeHealth(){active++;resize?.disconnect();resize=null;instance?.dispose();instance=null;}
export function healthPage(mode:'surveillance'|'vital'='surveillance'):string{
 const surveillance=mode==='surveillance';
 return '<section aria-label="Indicadores epidemiológicos e vitais">'+
 '<header class="mb-5"><p class="text-xs font-semibold uppercase tracking-wider text-teal-700 dark:text-teal-300">'+(surveillance?'SINAN · arboviroses':'SIM · SINASC · residentes')+'</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">'+(surveillance?'Vigilância epidemiológica':'Nascimentos e mortalidade')+'</h2>'+
 '<p class="text-sm text-slate-500 dark:text-slate-300 mt-2 max-w-2xl">'+(surveillance?'Notificações de dengue, chikungunya e zika entre residentes. Notificação não é sinônimo de caso confirmado ou de incidência.':'Nascidos vivos e óbitos não fetais de residentes, independentemente de onde ocorreu o atendimento. São contagens anuais, não taxas.')+'</p></header>'+
 '<div role="status" aria-live="polite" id="health-status" class="panel p-4 text-sm">Carregando séries oficiais…</div>'+
 '<div id="health-panel" class="mt-5 space-y-5"></div></section>';
}
function stateLabel(value:string){
 return value==='ok'?'<span class="pill bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200">Validado</span>':
 value==='partial'?'<span class="pill bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200">Parcial</span>':
 '<span class="pill bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-200">Pendente</span>';
}
function yearsTable(rows:Entry[]){
 if(!rows.length)return '<p class="text-sm text-slate-500 dark:text-slate-300 py-4">Nenhum período com dados validados.</p>';
 return '<div class="overflow-x-auto"><table class="w-full text-sm"><caption class="sr-only">Dados anuais da série selecionada</caption>'+
 '<thead><tr class="text-left text-slate-500 text-xs border-b border-slate-200 dark:border-slate-700"><th class="py-2">Ano</th><th class="py-2 text-right">Total</th><th class="py-2 text-right">Qualidade</th></tr></thead><tbody>'+
 rows.slice().sort((a,b)=>b.year-a.year).map(r=>'<tr class="border-b border-slate-100 dark:border-slate-700"><td class="py-3">'+r.year+'</td>'+
 '<td class="text-right tabular-nums font-semibold">'+nf(r.value)+'</td><td class="text-right text-xs text-slate-500">'+(r.provisional?'Preliminar':'Anual')+'</td></tr>').join('')+
 '</tbody></table></div>';
}
function statCard(key:string,data:Snapshot){
 const rows=data.series[key]||[],last=rows.length?rows[rows.length-1]:null;
 const m=data.sources[key];
 return '<button type="button" data-health-metric="'+safe(key)+'" class="panel p-4 sm:p-5 min-w-0 text-left w-full hover:border-teal-400 focus-visible:ring-2 focus-visible:ring-teal-500"><span class="flex flex-wrap items-start justify-between gap-2"><strong class="subheading text-sm">'+safe(LABELS[key])+'</strong>'+
 stateLabel(m?.status||'not_loaded')+'</span><div class="kpi-val mt-3">'+(last?nf(last.value):'—')+'</div>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">'+(last?String(last.year)+(last.provisional?' · preliminar':' · referência anual'):'Ainda sem coleta validada')+'</p>'+
 '<p class="text-xs leading-relaxed text-slate-500 dark:text-slate-300 mt-4 min-h-[64px]">'+safe(data.definitions[key]||m?.note||'')+'</p>'+
 '<span class="block mt-3 text-xs font-semibold text-teal-700 dark:text-teal-300">Ver evolução anual →</span></button>';
}
export async function mountHealth(dark:boolean,summary:DataSummary,mode:'surveillance'|'vital'='surveillance'){
 const token=++active;
 const status=document.getElementById('health-status');
 const panel=document.getElementById('health-panel');
 if(!status||!panel)return;
 try{
  const response=await fetch(urlAsset('data/indicators.json'),{cache:'no-cache'});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const data=await response.json() as Snapshot;
  if(!data||typeof data.series!=='object'||typeof data.sources!=='object')throw new Error('Estrutura inválida');
  if(token!==active||!panel.isConnected)return;
  const keys=mode==='surveillance'?['dengue','chikungunya','zika']:['sinasc','sim'];
  const available=keys.filter(k=>(data.series[k]||[]).length>0);
  status.innerHTML='<div class="flex flex-wrap items-center justify-between gap-3"><strong>'+available.length+' de '+keys.length+' séries disponíveis</strong>'+
   '<span class="text-xs text-slate-500 dark:text-slate-300">Extração: '+safe(fmtDate(data.updatedAt))+' · Somente dados agregados</span></div>';
  panel.innerHTML='<section aria-label="Indicadores principais" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">'+keys.map(k=>statCard(k,data)).join('')+'</section>'+
  '<section class="grid grid-cols-1 xl:grid-cols-12 gap-4"><article class="panel p-5 xl:col-span-8">'+
  '<div class="flex flex-wrap gap-3 justify-between items-center mb-4"><div><h3 class="subheading text-base">Evolução anual</h3><p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Selecione um indicador para comparar anos da mesma fonte.</p></div>'+
  '<label class="text-xs font-semibold">Indicador <select id="health-series-select" class="field mt-1 w-full sm:ml-1 sm:mt-0" aria-label="Indicador a exibir">'+
  keys.map(k=>'<option value="'+k+'" '+(k===(available[0]||'dengue')?'selected':'')+'>'+LABELS[k]+'</option>').join('')+'</select></label></div>'+
  '<div id="health-series-chart" style="height:305px;min-height:305px" role="img" aria-label="Série histórica selecionada"></div>'+
  '<p id="health-method" class="text-xs text-slate-500 dark:text-slate-400 mt-3"></p></article>'+
  '<article class="panel p-5 xl:col-span-4"><h3 class="subheading text-base mb-3">Tabela por ano</h3><div id="health-values"></div></article></section>'+
  '<section class="panel p-5"><h3 class="subheading text-base">Critérios de interpretação</h3><p class="text-sm text-slate-500 dark:text-slate-300 mt-2">Indicadores por residência não representam necessariamente eventos em estabelecimentos de Canoas. Notificações não equivalem a casos confirmados. Nascimentos e óbitos não medem diretamente o desempenho de hospitais locais. Dados preliminares podem ser revisados. População de referência IBGE: '+nf(summary.municipality.population)+' ('+safe(summary.municipality.populationYear)+'). Nunca foram publicados registros individuais.</p></section>';
  const ec=await import('echarts');
  if(token!==active||!panel.isConnected)return;
  const draw=(key:string)=>{
    if(token!==active)return;
    const target=document.querySelector<HTMLElement>('#health-series-chart');
    const table=document.getElementById('health-values'),method=document.getElementById('health-method');
    if(!target||!table||!method)return;
    const rows=data.series[key]||[];
    method.textContent=(data.definitions[key]||data.sources[key]?.note||'')+' · Contagem anual de residentes, não taxa. '+(rows.some(r=>r.provisional)?'Há dados preliminares sujeitos a revisão.':'');
    table.innerHTML=yearsTable(rows);
    instance?.dispose();instance=null;
    if(!rows.length){target.innerHTML='<div class="empty p-6">A série selecionada ainda não possui dados validados.</div>';return;}
    target.innerHTML='';
    instance=ec.init(target);
    document.querySelectorAll<HTMLElement>('[data-health-metric]').forEach(el=>el.classList.toggle('ui-metric-selected',el.dataset.healthMetric===key));
    const c=dark?'#9fb6c6':'#68798e';
    instance.setOption({grid:{top:22,left:12,bottom:28,right:16,containLabel:true},
      tooltip:{trigger:'axis'},
      xAxis:{type:'category',data:rows.map(r=>String(r.year)),axisLabel:{color:c},axisTick:{show:false},axisLine:{show:false}},
      yAxis:{type:'value',axisLabel:{color:c},splitLine:{lineStyle:{color:dark?'#31465c':'#edf1f5'}}},
      series:[{type:'bar',data:rows.map(r=>r.value),barMaxWidth:80,itemStyle:{color:'#0d9488',borderRadius:[6,6,0,0]},label:{show:true,position:'top',fontSize:11,color:c}}]});
    resize?.disconnect();resize=new ResizeObserver(()=>instance?.resize());resize.observe(target);
  };
  draw(available[0]||'dengue');
  document.querySelector<HTMLSelectElement>('#health-series-select')?.addEventListener('change',e=>draw((e.target as HTMLSelectElement).value));
  panel.querySelectorAll<HTMLElement>('[data-health-metric]').forEach(el=>el.addEventListener('click',()=>{
   const metric=el.dataset.healthMetric||available[0]||'dengue';
   const select=document.querySelector<HTMLSelectElement>('#health-series-select');if(select)select.value=metric;
   draw(metric);document.getElementById('health-series-chart')?.scrollIntoView({behavior:'smooth',block:'nearest'});
  }));
 }catch(error){
  console.warn('Health view:',error);
  if(active===token&&status.isConnected)status.textContent='Indicadores temporariamente indisponíveis. Verifique a conexão e o arquivo indicators.json publicado. Os demais módulos continuam disponíveis.';
 }
}