import {safe,nf,fmtDate,urlAsset,dlCsv} from './utils';
import {selectedFacility} from './facilityExplorer';

type Sample={period:string;value:number};
type Source={
 label:string;status:string;url:string;method?:string;note?:string;unit?:string;
 kind?:string;cadence?:string;reference?:string|null;retrievedAt?:string|null;municipalRecords?:number;
 totalPeriods?:number
};
type Data={schemaVersion:string;updatedAt:string|null;series:Record<string,Sample[]>;sources:Record<string,Source>};
let active=0;
let graph:any=null;
let observer:ResizeObserver|null=null;
const formatPeriod=(str:string,cadence?:string)=>{
 const q=str.match(/^(\d{4})Q([1-3])$/);if(q)return q[2]+'º quadrimestre de '+q[1];
 if(str.length!==6)return str;
 if(cadence==='annual')return str.slice(0,4)+(str.slice(4,6)==='12'?'':' · ref. '+str.slice(4,6));
 return str.slice(4,6)+'/'+str.slice(0,4);
};
const num=(n:number,k:string)=>{
 if(k==='currency')return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:2}).format(n);
 if(k==='rate')return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(n);
 return nf(n);
};
export type SusMode='primary'|'screening'|'finance'|'historic';
const groups:Record<SusMode,{title:string;eyebrow:string;intro:string;ids:string[];note:string}>={
 primary:{title:'Atenção Primária e equipes',eyebrow:'MGDI · APS · eMulti',
  intro:'Equipes multiprofissionais custeadas e homologadas, além das razões de consultas na APS e na atenção especializada. Equipes não representam quantidade de profissionais, e razões por 100 habitantes não são totais de consultas.',
  ids:['emulti_custeadas','emulti_homologadas','consultas_aps_razao','consultas_especializadas_razao'],
  note:'Indicadores por município, sem desagregação por CNES. Razão de consultas: número de consultas para cada 100 habitantes, segundo a metodologia RIPSA.'},
 screening:{title:'Prevenção e rastreamento',eyebrow:'Rastreamento · Ministério da Saúde',
  intro:'Séries municipais de exames citopatológicos e mamografias. Os números representam procedimentos registrados, não necessariamente pessoas distintas ou cobertura de rastreamento.',
  ids:['citopatologicos','mamografias'],
  note:'Os resultados disponíveis têm referência predominantemente anual; o último ano pode estar incompleto. Não comparar com taxas de cobertura sem população-alvo.'},
 historic:{title:'Atenção Primária · série histórica',eyebrow:'SISAB · Previne Brasil · 2024',
  intro:'Indicadores históricos por quadrimestre de Canoas. O Previne Brasil foi substituído em 2024: estes percentuais não medem o desempenho atual da APS nem a cobertura vacinal municipal do PNI.',
  ids:['aps_prenatal','aps_gestantes_testes','aps_gestantes_odontologia','aps_citopatologico','aps_vacinacao_infantil','aps_diabetes'],
  note:'Os percentuais utilizam numeradores e denominadores próprios do Previne Brasil. Não somar indicadores nem tratar seus registros como totais de atendimentos.'},
 finance:{title:'Financiamento e indicadores hospitalares',eyebrow:'Repasses federais · RIPSA',
  intro:'Repasses federais de equipes eMulti e indicadores anuais de internações hospitalares SUS. Valores de repasse, valores médios por AIH e quantidade de internações são grandezas diferentes.',
  ids:['emulti_repasses','sih_internacoes_anuais','valor_medio_aih'],
  note:'Repasses eMulti são mensais; valor médio por AIH e internações RIPSA são anuais. Não somar com a série mensal SIH/RD nem tratar valor médio por AIH como despesa hospitalar total.'}
};
export function stopSus(){active++;observer?.disconnect();observer=null;graph?.dispose();graph=null;}
export function susPage(mode:SusMode='primary'){
 const group=groups[mode];
 const selected=selectedFacility();
 return '<section aria-label="Assistência e financiamento SUS">'+
 '<header class="mb-5"><p class="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300">'+group.eyebrow+'</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">'+group.title+'</h2>'+
 '<p class="mt-2 text-sm max-w-3xl text-slate-500 dark:text-slate-300">'+group.intro+'</p>'+
 '</header>'+
 (selected?'<div role="note" class="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 text-xs text-amber-800 dark:text-amber-200">'+
 'Estabelecimento selecionado: <strong>'+safe(selected.name)+' · CNES '+safe(selected.cnes)+'</strong>. Estes indicadores são municipais e não podem ser atribuídos automaticamente à unidade. Os dados individuais permanecem disponíveis na ficha CNES acima.</div>':'')+
 '<div role="status" aria-live="polite" id="sus-status" class="panel p-4 text-sm text-slate-500 dark:text-slate-300">Carregando indicadores oficiais de assistência…</div>'+
 '<div class="flex flex-wrap gap-3 mt-4">'+(mode==='historic'?'<button data-page="sus" type="button" class="ui-section-link">APS e equipes atuais →</button>':'<button data-page="aps-history" type="button" class="ui-section-link">Indicadores históricos do SISAB →</button>')+'<button data-page="production" type="button" class="ui-section-link">Produção SIH/SIA por CNES →</button></div>'+
 '<div class="ui-context mt-4">'+safe(group.note)+'</div>'+
 '<div id="sus-content" class="space-y-5 mt-5"></div></section>';
}
const badge=(s:string)=>{
 if(s==='ok')return '<span class="pill bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200">Validado</span>';
 if(s==='partial')return '<span class="pill bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200">Parcial</span>';
 return '<span class="pill bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-200">Não integrado</span>';
};
function cards(data:Data,indicators:string[]){
 return indicators.map(id=>{
  const source=data.sources[id];
  const records=data.series[id]||[];
  const latest=records.length?records[records.length-1]:null;
  const label=source?.label||id,typ=source?.kind||'count';
  return '<button type="button" data-sus-metric="'+safe(id)+'" class="panel p-4 sm:p-5 text-left hover:ring-2 hover:ring-teal-400 focus-visible:ring-2 focus-visible:ring-teal-500 w-full" aria-label="Ver evolução de '+safe(label)+'">'+
  '<span class="flex flex-wrap justify-between gap-2 items-start"><strong class="text-sm leading-snug max-w-[200px]">'+safe(label)+'</strong>'+badge(source?.status||'not_loaded')+'</span>'+
  '<span class="block kpi-val mt-3">'+(latest?num(latest.value,typ):'—')+'</span>'+
  '<span class="block text-xs text-slate-500 dark:text-slate-300 mt-2">'+(latest?formatPeriod(latest.period,source?.cadence)+' · '+safe(source?.unit||''):'Sem série municipal validada')+'</span>'+
  '<span class="ui-card-summary mt-2">'+safe(source?.method||source?.note||'Consulte a definição detalhada ao selecionar este indicador.')+'</span>'+
  '<span class="block text-xs font-bold text-teal-700 dark:text-teal-300 mt-3">Explorar série →</span></button>'
 }).join('');
}
function table(rows:Sample[],kind:string,unit:string,cadence?:string){
 if(!rows.length)return '<div class="empty p-5">Nenhum dado municipal validado disponível.</div>';
 return '<div class="overflow-x-auto"><table class="w-full text-sm"><caption class="sr-only">Série histórica municipal da fonte selecionada</caption>'+
 '<thead><tr class="text-xs text-slate-500 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700"><th class="py-2 text-left">Competência</th><th class="py-2 text-right">'+safe(unit||'Valor')+'</th></tr></thead><tbody>'+
 rows.slice().reverse().map(v=>'<tr class="border-b border-slate-100 dark:border-slate-700"><td class="py-2">'+formatPeriod(v.period,cadence)+'</td><td class="py-2 text-right tabular-nums font-semibold">'+num(v.value,kind)+'</td></tr>').join('')+'</tbody></table></div>';
}
export async function mountSus(dark:boolean,mode:SusMode='primary'){
 const group=groups[mode];
 const indicators=group.ids;
 const token=++active;
 const status=document.getElementById('sus-status'),panel=document.getElementById('sus-content');
 if(!status||!panel)return;
 try{
  const response=await fetch(urlAsset(mode==='historic'?'data/aps.json':'data/sus.json'),{cache:'no-cache'});
  if(!response.ok)throw new Error('Erro HTTP '+response.status);
  const data=await response.json() as Data;
  if(!data||data.schemaVersion!=='1.0'||typeof data.sources!=='object'||typeof data.series!=='object')
   throw new Error('Contrato de dados incompatível');
  if(token!==active||!panel.isConnected)return;
  const available=indicators.filter(k=>data.sources[k]?.status==='ok'&&(data.series[k]||[]).length);
  status.innerHTML='<div class="flex justify-between items-center gap-3 flex-wrap"><span class="font-semibold">'+available.length+' de '+indicators.length+' fontes municipais com séries validadas</span>'+
   '<span class="text-xs text-slate-500 dark:text-slate-300">Última extração: '+fmtDate(data.updatedAt)+' · Fonte: '+(mode==='historic'?'SISAB · Previne Brasil (histórico)':'Ministério da Saúde · MGDI/RIPSA')+'</span></div>';
  const pending=['sih','sia','pni'].map(k=>({key:k,...data.sources[k]})).filter(x=>x.label);
  panel.innerHTML='<section aria-label="Indicadores municipais" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">'+cards(data,indicators)+'</section>'+
   '<section class="grid grid-cols-1 xl:grid-cols-12 gap-4">'+
   '<article class="panel p-5 xl:col-span-8"><div class="flex flex-wrap items-start justify-between gap-3 mb-4"><div><h3 class="subheading text-base">Evolução por competência</h3><p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Clique em um cartão para trocar a série; valores com unidades diferentes não são somados.</p></div>'+
   '<button id="sus-export" type="button" class="text-xs px-3 py-2 border border-teal-200 rounded-lg font-bold text-teal-700 dark:text-teal-300">Exportar série CSV</button></div>'+
   '<h4 id="sus-chart-title" class="text-sm font-semibold mb-2"></h4><div id="sus-chart" style="height:300px;min-height:300px" role="img" aria-label="Gráfico de indicador SUS por competência"></div>'+
   '<p class="text-xs text-slate-500 dark:text-slate-300 mt-2">Use a barra inferior para consultar outros períodos. Valores percentuais, taxas e contagens têm unidades distintas.</p>'+
   '<p id="sus-method" class="text-xs leading-relaxed text-slate-500 dark:text-slate-300 mt-4"></p>'+
   '<a id="sus-source-link" target="_blank" rel="noopener noreferrer" class="underline text-xs text-teal-700 dark:text-teal-300 mt-2 inline-block">Consultar a fonte oficial</a></article>'+
   '<article class="panel p-5 xl:col-span-4"><h3 class="subheading text-base mb-4">Valores por competência</h3>'+
   '<div id="sus-table"></div></article></section>'+
   '<div role="note" class="ui-context">Cada gráfico apresenta uma grandeza e sua respectiva unidade. Consulte a definição abaixo do gráfico; ausência de dado não significa zero. Fontes pendentes estão no catálogo.</div>';
  const ec=await import('echarts');
  if(token!==active||!panel.isConnected)return;
  let selected=available[0]||indicators[0];
  const draw=(key:string)=>{
   if(token!==active)return;
   selected=key;
   const source=data.sources[key],rows=data.series[key]||[];
   const target=document.getElementById('sus-chart');
   const details=document.getElementById('sus-method');
   const link=document.querySelector<HTMLAnchorElement>('#sus-source-link');
   const tableTarget=document.getElementById('sus-table');
   if(!target||!details||!tableTarget||!link)return;
   graph?.dispose();graph=null;observer?.disconnect();observer=null;
   document.getElementById('sus-chart-title')!.textContent=source?.label||key;
   details.textContent=(source?.method||source?.note||'')+' · Referência mais recente: '+(source?.reference?formatPeriod(source.reference,source.cadence):'não informada')+'.';
   if(source?.url){link.href=source.url;link.hidden=false}else link.hidden=true;
   tableTarget.innerHTML=table(rows,source?.kind||'count',source?.unit||'',source?.cadence);
   document.querySelectorAll<HTMLElement>('[data-sus-metric]').forEach(node=>{
    node.classList.toggle('ring-2',node.dataset.susMetric===key);
    node.classList.toggle('ring-teal-500',node.dataset.susMetric===key);
   });
   if(!rows.length){target.innerHTML='<div class="empty p-6">Série indisponível: o arquivo municipal ainda não passou na validação.</div>';return}
   target.innerHTML='';
   graph=ec.init(target);
   const color=dark?'#9fb6c6':'#64748b';
   const mobile=window.matchMedia('(max-width: 640px)').matches;
   const visible=mobile?6:10;
   const begin=rows.length>visible?Math.max(0,100-visible*100/rows.length):0;
   graph.setOption({animationDuration:250,grid:{top:24,left:15,right:14,bottom:76,containLabel:true},
    tooltip:{trigger:'axis',valueFormatter:(v:number)=>num(Number(v),source?.kind||'count')+
     ((source?.kind==='rate'||source?.kind==='count')&&source?.unit?' '+source.unit:'')},
    dataZoom:[{type:'inside',start:begin,end:100},
     {type:'slider',height:14,bottom:5,start:begin,end:100,textStyle:{color,fontSize:10}}],
    xAxis:{type:'category',data:rows.map(x=>formatPeriod(x.period,source?.cadence)),
      axisLabel:{color,rotate:mobile?45:25,fontSize:10,hideOverlap:true},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color,formatter:(value:number)=>new Intl.NumberFormat('pt-BR',{notation:'compact',maximumFractionDigits:1}).format(value)},
       splitLine:{lineStyle:{color:dark?'#30455b':'#edf2f7'}}},
    series:[{type:'line',smooth:true,symbolSize:5,lineStyle:{color:'#0d9488',width:2.5},itemStyle:{color:'#0d9488'},
      data:rows.map(x=>x.value),areaStyle:{color:'rgba(13,148,136,.09)'}}]});
   observer=new ResizeObserver(()=>graph?.resize());observer.observe(target);
  };
  draw(selected);
  panel.addEventListener('click',(event)=>{
   const target=event.target as HTMLElement;
   const action=target.closest<HTMLElement>('[data-sus-metric]');
   if(action){draw(action.dataset.susMetric||selected);document.getElementById('sus-chart-title')?.scrollIntoView({behavior:'smooth',block:'nearest'});}
  });
  document.getElementById('sus-export')?.addEventListener('click',()=>{
   const source=data.sources[selected];const rows=data.series[selected]||[];
   dlCsv(rows.map(v=>({Indicador:source?.label||selected,Competencia:v.period,Valor:v.value,Unidade:source?.unit||''})),
    'sus-canoas-'+selected+'.csv');
  });
 }catch(error){
  console.error('Dados MGDI:',error);
  if(token===active&&status.isConnected)status.textContent='Não foi possível carregar as novas fontes de assistência. O CNES e os demais módulos permanecem disponíveis.';
 }
}