import {nf,safe,urlAsset} from './utils';
import type {FacilitiesGeoJSON} from './types';

export interface FacilityRecord {
 cnes:string;name:string;type:string;category:string;address:string;neighborhood:string;
 phone:string;sus:boolean|null;hasBeds:boolean|null;coordinates:[number,number]|null;
 bedsTotal:number|null;bedsSus:number|null;bedsAsOf:string|null;
 legalNature?:string|null;management?:string|null;utiTotal?:number|null;utiSus?:number|null;
}
interface Catalog{schemaVersion:string;updatedAt:string|null;facilities:FacilityRecord[]}
let records:FacilityRecord[]=[];
let byCode=new Map<string,FacilityRecord>();
let current:string|null=null;
let fallbackMode=false;
let chart:any=null;
let chartResize:ResizeObserver|null=null;
let updateNumber=0;
let chartVersion=0;
const clean=(value:string)=>value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
const cnesKey=(s:string)=>/^\d{1,7}$/.test(s)?s.padStart(7,'0'):null;

export function selectedCnes(){return current}
export function selectedFacility(){return current?byCode.get(current)||null:null}
export function getFacility(cnes:string){return byCode.get(cnesKey(String(cnes))||'')||null}
export function allFacilities(){return records}
export function hasCatalogFallback(){return fallbackMode}

export async function loadFacilityCatalog(geo:FacilitiesGeoJSON){
 const mapped=geo.features.map(f=>({
  ...f.properties,coordinates:f.geometry.coordinates,
  bedsTotal:f.properties.bedsTotal??null,bedsSus:f.properties.bedsSus??null,
  bedsAsOf:f.properties.bedsAsOf??null,utiTotal:null,utiSus:null
 })) as FacilityRecord[];
 let rows=mapped;
 fallbackMode=true;
 try{
  const result=await fetch(urlAsset('data/facilities.json'),{cache:'no-cache'});
  if(!result.ok)throw new Error('Catálogo HTTP '+result.status);
  const data=await result.json() as Catalog;
  if(data.schemaVersion!=='1.1'||!Array.isArray(data.facilities)||data.facilities.length<mapped.length)throw new Error('Catálogo incompleto');
  const ids=new Set<string>();
  for(const item of data.facilities){
   if(!cnesKey(item.cnes)||!item.name||ids.has(item.cnes))throw new Error('CNES inválido ou repetido');
   ids.add(item.cnes);
  }
  rows=data.facilities;
  fallbackMode=false;
 }catch(error){console.warn('Catálogo detalhado indisponível; dados geográficos preservados',error)}
 records=rows;
 byCode=new Map(records.map(item=>[item.cnes,item]));
 const requested=new URL(location.href).searchParams.get('cnes');
 if(requested&&getFacility(requested))current=cnesKey(requested);
 if(current&&!byCode.has(current))current=null;
}

export function pickFacility(value:string|null,updateUrl=true){
 const next=value===null?null:cnesKey(String(value));
 if(next&&!byCode.has(next))return false;
 current=next;
 if(updateUrl){
  const url=new URL(location.href);
  if(next)url.searchParams.set('cnes',next);
  else url.searchParams.delete('cnes');
  history.replaceState(history.state,'',url);
 }
 const input=document.querySelector<HTMLInputElement>('#facility-search-global');
 if(input){input.value='';input.setAttribute('aria-expanded','false')}
 const suggested=document.querySelector<HTMLElement>('#facility-suggest');
 if(suggested)suggested.replaceChildren();
 refreshFacilityExplorer();
 window.dispatchEvent(new CustomEvent('webgis:facility-selected',{detail:{cnes:next}}));
 return true;
}

export function facilityExplorerMarkup(){
 return '<section id="facility-explorer" class="panel p-4 sm:p-5 mb-5" aria-label="Explorar estabelecimento individual">'+
 '<div class="flex flex-wrap justify-between items-start gap-3 mb-3"><div><p class="text-[11px] uppercase font-bold tracking-wider text-teal-700 dark:text-teal-300">Exploração interativa · CNES</p>'+
 '<h2 class="subheading text-lg mt-1">Selecionar estabelecimento</h2>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">A seleção atualiza o popup, a ficha e os gráficos por unidade em qualquer aba.</p></div>'+
 '<span class="pill bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-200">Fonte: CNES + Leitos</span></div>'+
 '<div class="relative"><label for="facility-search-global" class="sr-only">Pesquisar estabelecimento por nome, CNES ou bairro</label>'+
 '<input id="facility-search-global" autocomplete="off" type="search" role="combobox" aria-autocomplete="list" aria-controls="facility-suggest" aria-expanded="false" '+
 'class="field w-full" placeholder="Pesquise uma UBS, hospital, CNES ou bairro…"/>'+
 '<div id="facility-suggest" role="listbox" class="absolute z-40 w-full bg-white dark:bg-[#152b3c] rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 mt-1 max-h-72 overflow-auto hidden"></div></div>'+
 '<div id="facility-details" class="mt-4" aria-live="polite"></div></section>';
}
const fmt=(v:number|null|undefined)=>typeof v==='number'?nf(v):'—';
const textLabel=(v:unknown)=>v===null||v===undefined||v===''?'Não informado':safe(v);
const badge=(k:string,v:string)=>'<div class="rounded-xl border border-slate-100 dark:border-slate-700 p-3"><p class="text-[11px] text-slate-500 dark:text-slate-300">'+k+'</p><p class="text-base font-bold mt-1 tabular-nums">'+v+'</p></div>';
function scopePanel(item:FacilityRecord){
 const hasBeds=typeof item.bedsTotal==='number';
 const susStatement=item.sus===true?'Atendimento SUS declarado no CNES':item.sus===false?'Atendimento SUS não declarado no campo disponível':'Vínculo SUS não informado';
 return '<div class="border-t border-slate-100 dark:border-slate-700 pt-4">'+
 '<div class="flex flex-wrap items-start justify-between gap-2"><div class="min-w-0"><h3 class="subheading text-lg leading-snug">'+safe(item.name)+'</h3>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">'+safe(item.type)+' · CNES '+safe(item.cnes)+'</p></div>'+
 '<button type="button" data-facility-clear class="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-xs font-semibold" aria-label="Limpar seleção">Limpar seleção</button></div>'+
 '<div class="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-2">'+
 badge('Leitos existentes',fmt(item.bedsTotal))+badge('Leitos SUS',fmt(item.bedsSus))+
 badge('Leitos não SUS',hasBeds&&item.bedsSus!==null?fmt(item.bedsTotal!-item.bedsSus):'—')+
 badge('UTI existente',fmt(item.utiTotal))+'</div>'+
 '<div class="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4"><div class="rounded-xl bg-slate-50 dark:bg-slate-800/40 p-4 text-sm space-y-2">'+
 '<p><strong>Bairro:</strong> '+textLabel(item.neighborhood)+'</p>'+
 '<p><strong>Endereço:</strong> '+textLabel(item.address)+'</p>'+
 '<p><strong>Telefone:</strong> '+textLabel(item.phone)+'</p>'+
 '<p><strong>Natureza organizacional (CNES):</strong> '+textLabel(item.legalNature)+'</p>'+
 '<p><strong>Gestão cadastrada:</strong> '+textLabel(item.management)+'</p>'+
 '<p><strong>Relação com o SUS:</strong> '+safe(susStatement)+'</p>'+
 (item.coordinates?'<p class="text-xs text-emerald-700 dark:text-emerald-300">Coordenadas geográficas disponíveis</p>':'<p class="text-xs text-amber-700 dark:text-amber-300">Sem localização CNES para este cadastro</p>')+
 '</div><div class="rounded-xl border border-slate-100 dark:border-slate-700 p-4"><h4 class="subheading text-sm">Capacidade hospitalar · unidade selecionada</h4>'+
 (hasBeds?'<div id="facility-beds-chart" role="img" aria-label="Composição de leitos SUS e não SUS" style="height:165px"></div>':
 '<p class="text-sm text-slate-500 dark:text-slate-300 mt-4">Esta unidade não possui contagem individual de leitos validada na competência consultada. Isso não significa zero.</p>')+
 '<p class="text-[11px] text-slate-500 dark:text-slate-300 mt-2">Competência: '+(item.bedsAsOf?safe(item.bedsAsOf.slice(4,6)+'/'+item.bedsAsOf.slice(0,4)):'não disponível')+'. Os dados são cadastrais; não representam ocupação ou vagas livres.</p></div></div>'+
 '<div class="mt-4"><div class="flex items-center justify-between flex-wrap gap-2 mb-2"><h4 class="subheading text-sm">Comparação entre estabelecimentos com leitos informados</h4>'+
 '<span class="text-xs text-slate-500">Clique em uma barra para selecionar outra unidade</span></div>'+
 '<div id="facility-peer-chart" role="img" aria-label="Comparativo interativo de leitos por estabelecimento" style="height:210px"></div></div>'+
 '<div class="flex flex-wrap justify-between items-center mt-3 gap-3"><span class="text-[11px] text-slate-500 dark:text-slate-300">'+(fallbackMode?'Catálogo de contingência · alguns campos podem faltar':'Catálogo individual CNES · atualizado automaticamente')+'</span>'+
 (item.coordinates?'<button type="button" data-facility-map class="rounded-lg bg-[#0d857e] text-white text-xs font-bold px-3 py-2">Localizar no mapa →</button>':'')+'</div></div>';
}
function renderSuggestions(){
 const input=document.querySelector<HTMLInputElement>('#facility-search-global');
 const el=document.querySelector<HTMLElement>('#facility-suggest');
 if(!input||!el)return;
 const needle=clean(input.value.trim());
 if(needle.length<2){el.innerHTML='';el.classList.add('hidden');input.setAttribute('aria-expanded','false');return}
 const found=records.filter(f=>clean([f.name,f.cnes,f.neighborhood,f.type].join(' ')).includes(needle)).slice(0,9);
 el.innerHTML=found.length?found.map(f=>
  '<button type="button" role="option" aria-selected="false" data-facility-pick="'+safe(f.cnes)+'" class="w-full text-left p-3 hover:bg-teal-50 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700">'+
  '<span class="font-semibold text-sm">'+safe(f.name)+'</span><span class="block text-xs text-slate-500 dark:text-slate-300">'+safe(f.type)+' · '+safe(f.neighborhood)+' · CNES '+safe(f.cnes)+'</span></button>').join(''):
  '<p class="p-3 text-sm text-slate-500">Nenhuma unidade encontrada.</p>';
 el.classList.remove('hidden');input.setAttribute('aria-expanded','true');
}
function disposeCharts(){
 updateNumber++;
 chartVersion++;
 chartResize?.disconnect();chartResize=null;
 if(chart){chart.dispose();chart=null}
 const existing=document.querySelector<HTMLElement>('#facility-beds-chart');
 if(existing)(existing as any).__facilityChart?.dispose();
}
async function paintCharts(item:FacilityRecord){
 const token=++updateNumber;
 const echart=await import('echarts');
 if(token!==updateNumber||!document.getElementById('facility-details'))return;
 const bed=document.querySelector<HTMLElement>('#facility-beds-chart');
 if(bed&&item.bedsTotal!==null&&item.bedsSus!==null){
  const instance=echart.init(bed);
  (bed as any).__facilityChart=instance;
  instance.setOption({animationDuration:280,tooltip:{trigger:'item',formatter:'{b}: {c} leitos'},
    series:[{type:'pie',radius:['54%','80%'],center:['50%','50%'],label:{show:true,formatter:'{b}: {c}',fontSize:10},
    data:[{name:'SUS',value:item.bedsSus,itemStyle:{color:'#0d9488'}},
          {name:'Não SUS',value:item.bedsTotal-item.bedsSus,itemStyle:{color:'#64748b'}}]}]});
 }
 const peers=records.filter(f=>typeof f.bedsTotal==='number').sort((a,b)=>(b.bedsTotal||0)-(a.bedsTotal||0)).slice(0,12);
 const el=document.querySelector<HTMLElement>('#facility-peer-chart');
 if(el){
  if(!peers.length){el.textContent='Sem dados individuais de leitos para comparação.';return}
  chart=echart.init(el);
  chart.setOption({animationDuration:280,grid:{top:8,left:18,right:32,bottom:76,containLabel:true},
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:(params:any)=>{
      const datum=params?.[0]; const index=datum?.dataIndex??-1;const selected=peers[index];
      return selected?safe(selected.name)+'<br>Existentes: '+fmt(selected.bedsTotal)+'<br>SUS: '+fmt(selected.bedsSus):'';}},
    xAxis:{type:'category',data:peers.map(f=>f.name),axisLabel:{rotate:30,width:115,overflow:'truncate',fontSize:10}},
    yAxis:{type:'value',axisLabel:{fontSize:10}},
    series:[{name:'Existentes',type:'bar',data:peers.map(f=>({value:f.bedsTotal,
      itemStyle:{color:f.cnes===item.cnes?'#0f766e':'#94a3b8'}})),barMaxWidth:58}]});
  chart.on('click',(params:any)=>{const selected=peers[params.dataIndex];if(selected)pickFacility(selected.cnes)});
  chartResize=new ResizeObserver(()=>{chart?.resize();(bed as any)?.__facilityChart?.resize()});
  chartResize.observe(el);if(bed)chartResize.observe(bed);
 }
}
export function refreshFacilityExplorer(){
 disposeCharts();
 const slot=document.getElementById('facility-details');
 if(!slot)return;
 const chosen=selectedFacility();
 if(!chosen){
  slot.innerHTML='<div class="rounded-xl bg-slate-50 dark:bg-slate-800/40 p-4 text-sm text-slate-500 dark:text-slate-300">'+
    'Selecione uma unidade para consultar cadastro, leitos disponíveis na fonte e comparar suas características com outros estabelecimentos.'+
    '<span class="block text-xs mt-2">'+nf(records.length)+' estabelecimentos consultáveis.'+(fallbackMode?' Parte do catálogo está indisponível.':'')+'</span></div>';
  return;
 }
 slot.innerHTML=scopePanel(chosen);
 void paintCharts(chosen).catch(error=>{console.warn('Gráficos individuais indisponíveis',error)});
}
export function mountFacilityExplorer(){
 const root=document.getElementById('facility-explorer');
 if(!root)return;
 root.addEventListener('click',(event)=>{
  const target=event.target as HTMLElement;
  const pick=target.closest<HTMLElement>('[data-facility-pick]');
  if(pick){pickFacility(pick.dataset.facilityPick||'');return}
  if(target.closest('[data-facility-clear]')){pickFacility(null);return}
  if(target.closest('[data-facility-map]'))window.dispatchEvent(new CustomEvent('webgis:facility-open-map'));
 });
 const search=root.querySelector<HTMLInputElement>('#facility-search-global');
 search?.addEventListener('input',renderSuggestions);
 search?.addEventListener('keydown',(event)=>{
  if(event.key==='Escape'){search.value='';renderSuggestions()}
  if(event.key==='Enter'){
   const first=root.querySelector<HTMLElement>('[data-facility-pick]');
   if(first){event.preventDefault();pickFacility(first.dataset.facilityPick||'')}
  }
 });
 refreshFacilityExplorer();
}
export function facilityPopupHTML(cnes:string){
 const item=getFacility(cnes);
 if(!item)return '<p>Estabelecimento não encontrado.</p>';
 return '<div class="map-tooltip"><h3>'+safe(item.name)+'</h3><div class="small">'+safe(item.type)+'<br><b>CNES '+safe(item.cnes)+'</b>'+
 '<br>'+safe(item.address||'Endereço não informado')+
 '<br>Bairro: '+safe(item.neighborhood||'não informado')+
 (item.phone?'<br>Contato: '+safe(item.phone):'')+
 '<br>Leitos existentes: '+fmt(item.bedsTotal)+' · SUS: '+fmt(item.bedsSus)+
 '<br>Leitos UTI: '+fmt(item.utiTotal)+
 (item.bedsAsOf?'<br>Competência '+safe(item.bedsAsOf):'')+
 '<br><span class="text-teal-700 font-bold">Unidade selecionada · detalhes e gráficos no painel</span></div></div>';
}
