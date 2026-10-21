import {fmtDate, safe, urlAsset, nf} from './utils';

type Status = 'ok' | 'partial' | 'not_loaded' | 'error';
type Entry = {
 label:string; status:Status; url:string; reference:string|null;
 retrievedAt:string|null; cadence?:string; note?:string; unit?:string;
};
type Sample = {period:string; value:number};
type Snapshot = {
 schemaVersion:string; municipality:string; updatedAt:string|null;
 sources:Record<string,Entry>; series:Record<string,Sample[]>;
};
let epoch=0;
export function stopFarmaciaSiaps(){epoch++;}
const statusText=(s:Status)=>s==='ok'?'Validado':s==='partial'?'Fonte identificada; dados pendentes':s==='error'?'Falha na coleta':'Não integrado';
const pill=(status:Status)=>
 '<span class="pill '+(status==='ok'?'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-200':'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-200')+'">'+statusText(status)+'</span>';

const bnafar=['bnafar_envio','qualifar_monitoramento'];
const siaps=['siaps_cofinanciamento','siaps_qualidade','siaps_praticas'];
function sourceCard(key:string,entry?:Entry,series:Sample[]=[]){
 if(!entry)return '';
 const items=entry.status==='ok'&&series.length?series:[];
 const latest=items.length?items[items.length-1]:null;
 return '<article class="panel p-4 sm:p-5 min-w-0">'+
  '<div class="flex flex-wrap justify-between gap-2 items-start"><h3 class="subheading text-sm">'+safe(entry.label)+'</h3>'+pill(entry.status)+'</div>'+
  (latest?'<p class="kpi-val mt-3">'+nf(latest.value)+'</p><p class="text-xs text-slate-500 mt-1">'+safe(entry.unit||'')+' · '+safe(latest.period)+'</p>':
   '<p class="text-xl font-bold mt-4 text-slate-500 dark:text-slate-300" aria-label="Sem indicador validado">—</p><p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Nenhum valor municipal validado neste painel</p>')+
  '<dl class="mt-3 space-y-1 text-xs text-slate-500 dark:text-slate-300">'+
  '<div><dt class="inline font-semibold">Periodicidade: </dt><dd class="inline">'+safe(entry.cadence||'não informada')+'</dd></div>'+
  '<div><dt class="inline font-semibold">Referência: </dt><dd class="inline">'+safe(entry.reference||'não validada')+'</dd></div>'+
  '<div><dt class="inline font-semibold">Extração municipal: </dt><dd class="inline">'+safe(entry.retrievedAt?fmtDate(entry.retrievedAt):'pendente')+'</dd></div>'+
  '</dl>'+
  '<p class="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-300">'+safe(entry.note||'Consulte a documentação da fonte.')+'</p>'+
  (/^https:\/\/[^\s]+$/.test(entry.url)?'<a class="mt-3 inline-flex text-xs font-semibold text-teal-700 dark:text-teal-300 underline break-all" href="'+safe(entry.url)+'" target="_blank" rel="noopener noreferrer">Abrir a fonte oficial ↗</a>':'')+
  '</article>';
}

export function farmaciaSiapsPage(){
 return '<section aria-label="Farmácia e indicadores atuais SIAPS">'+
 '<header class="mb-5"><p class="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300">Assistência farmacêutica · Atenção Primária</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">Farmácia e SIAPS</h2>'+
 '<p class="mt-2 text-sm max-w-3xl text-slate-500 dark:text-slate-300">Fontes do Ministério da Saúde para acompanhar envio de informações farmacêuticas e indicadores atuais de desempenho da Atenção Primária. A apresentação distingue publicação oficial de dado municipal validado.</p></header>'+
 '<div class="ui-context mb-5" role="note"><strong>Importante:</strong> status de envio à BNAFAR não corresponde à disponibilidade de medicamentos. Os indicadores atuais do SIAPS não são diretamente comparáveis à série histórica do Previne Brasil.</div>'+
 '<div id="farmacia-siaps-status" role="status" aria-live="polite" class="panel p-4 text-sm text-slate-500 dark:text-slate-300">Carregando catálogo das fontes…</div>'+
 '<div id="farmacia-siaps-content" class="mt-5 space-y-7"></div>'+
 '<div class="mt-5 flex flex-wrap gap-2"><button type="button" data-page="aps-history" class="rounded-lg border border-teal-300 text-teal-700 dark:text-teal-300 text-xs font-bold px-3 py-2">Consultar histórico SISAB →</button>'+
 '<button type="button" data-page="sources" class="rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-bold px-3 py-2">Metodologia e fontes →</button></div></section>';
}

function section(title:string,subtitle:string,entries:string[],data:Snapshot){
 return '<section aria-label="'+safe(title)+'"><h2 class="subheading text-xl">'+safe(title)+'</h2>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1 mb-4">'+safe(subtitle)+'</p>'+
 '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">'+entries.map(key=>sourceCard(key,data.sources[key],data.series[key]||[])).join('')+'</div></section>';
}
export async function mountFarmaciaSiaps(){
 const token=++epoch;
 const status=document.getElementById('farmacia-siaps-status');
 const content=document.getElementById('farmacia-siaps-content');
 if(!status||!content)return;
 try{
  const response=await fetch(urlAsset('data/farmacia_siaps.json'),{cache:'no-cache'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const doc=await response.json() as Snapshot;
  if(doc.schemaVersion!=='1.0'||doc.municipality!=='4304606'||!doc.sources||!doc.series
     ||![...bnafar,...siaps].every(key=>doc.sources[key]&&typeof doc.sources[key].url==='string'))
   throw Error('Arquivo de fontes incompatível');
  if(token!==epoch||!content.isConnected)return;
  const count=[...bnafar,...siaps].filter(key=>doc.sources[key].status==='ok'&&(doc.series[key]||[]).length).length;
  status.textContent=count+' de 5 conjuntos com indicadores municipais validados · Referência do catálogo: '+
   (doc.updatedAt?fmtDate(doc.updatedAt):'publicação inicial; atualização automática pendente')+
   '. Fontes identificadas não entram nos totais enquanto não houver série validada.';
  content.innerHTML=section('Assistência farmacêutica · BNAFAR',
    'Status mensal de envio municipal e planilhas semanais de monitoramento Qualifar-SUS. Não representam estoque ou dispensações disponíveis em Canoas.',bnafar,doc)+
   section('Atenção Primária · SIAPS',
    'Módulos de cofinanciamento, qualidade e práticas assistenciais. Exige exportação pública municipal conferida, com competência e unidade de medida.',siaps,doc)+
   '<div class="ui-context text-xs" role="note">O BNAFAR publica o status mensal por meio de painel externo (Looker Studio), e o Qualifar-SUS disponibiliza planilhas XLSX. O SIAPS disponibiliza relatórios CSV/XLSX na consulta pública; até uma extração oficial validada ser incorporada, nenhum valor é apresentado. Dados individuais de pacientes não são utilizados.</div>';
 }catch(error){
  console.warn('Fonte BNAFAR/SIAPS:',error);
  if(token===epoch&&status.isConnected)
   status.textContent='O catálogo BNAFAR/SIAPS está temporariamente indisponível. Consulte diretamente os portais oficiais.';
 }
}
