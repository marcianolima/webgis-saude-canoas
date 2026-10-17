import {safe,fmtDate,urlAsset,nf,dlCsv} from './utils';
import type {DataSummary} from './types';

type Evidence={label?:string;status?:string;url?:string;reference?:string|null;retrievedAt?:string|null;
  note?:string;method?:string;records?:number|null;yearsAvailable?:number[];unit?:string;cadence?:string;kind?:string};
type Json={sources:Record<string,Evidence>;series?:Record<string,Array<Record<string,unknown>>>;updatedAt?:string|null};
type Row=Evidence & {id:string;family:string;years?:string};
let active=0;
export function stopSources(){active++;}
export function sourcesPage(){
 return '<section aria-label="Catálogo e qualidade dos dados">'+
 '<header class="mb-5"><p class="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-300">Dados abertos e metodologia</p>'+
 '<h2 class="subheading text-2xl md:text-3xl mt-1">Fontes e qualidade da informação</h2>'+
 '<p class="text-sm text-slate-500 dark:text-slate-300 mt-2 max-w-3xl">Consulte a origem, o período, o estado da integração e as limitações metodológicas. Cada fonte mantém sua própria periodicidade; indisponível não significa zero.</p></header>'+
 '<div class="panel p-4 mb-4"><p class="text-sm">Os estabelecimentos CNES e os leitos são dados cadastrais; notificações e estatísticas vitais são agregadas por residência; produção RIPSA e MGDI segue a metodologia própria do indicador. A seleção por CNES não altera resultados exclusivamente municipais.</p></div>'+
 '<div class="panel p-4 sm:p-5"><div class="flex gap-3 items-center justify-between flex-wrap"><div><h3 class="subheading text-base">Inventário de fontes</h3><p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Status verificado nos arquivos efetivamente publicados.</p></div>'+
 '<button type="button" id="source-export" class="rounded-lg border border-teal-300 text-teal-700 dark:text-teal-200 text-xs font-bold px-3 py-2" disabled>Exportar catálogo CSV</button></div>'+
 '<div id="source-status" role="status" aria-live="polite" class="mt-3 text-xs text-slate-500">Carregando metadados das fontes…</div>'+
 '<div class="flex flex-wrap items-center gap-3 mt-4 mb-3"><label for="sources-filter" class="text-xs font-bold">Filtrar situação</label>'+
 '<select id="sources-filter" class="field" aria-label="Filtrar fontes por situação"><option value="all">Todas</option><option value="ok">Disponíveis</option><option value="pending">Pendentes ou falhas</option></select>'+
 '<label for="sources-search" class="text-xs font-bold">Pesquisar</label><input type="search" id="sources-search" class="field min-w-[180px]" placeholder="Fonte, tema ou metodologia…"/></div>'+
 '<div id="source-groups" class="space-y-5"></div></div>'+
 '<p class="mt-4 text-xs text-slate-500 dark:text-slate-300">Fontes classificadas como pendentes não foram utilizadas para compor totais municipais. Indicadores históricos podem ser preliminares ou utilizar métodos atualmente substituídos.</p></section>';
}
const statusText=(s:string)=>s==='ok'?'Validado':s==='partial'?'Parcial':s==='error'?'Falha na coleta':'Não integrado';
const pill=(s:string)=>'<span class="pill '+(s==='ok'?'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-200':'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-200')+'">'+statusText(s)+'</span>';
const keyDate=(s:string|null|undefined)=>s?(/^\d{6}$/.test(s)?s.slice(4)+'/'+s.slice(0,4):(/^\d{4}$/.test(s)?s:s)):'Não informado';
const sourceCard=(r:Row)=>'<article class="rounded-xl border border-slate-100 dark:border-slate-700 p-4 min-w-0">'+
 '<div class="flex justify-between items-start gap-2"><h4 class="font-bold text-sm">'+safe(r.label||r.id)+'</h4>'+pill(r.status||'not_loaded')+'</div>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-2">Referência: <strong>'+safe(keyDate(r.reference))+'</strong>'+
 (r.unit?' · '+safe(r.unit):'')+(r.years?' · '+safe(r.years):'')+'</p>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-1">Última extração: '+safe(fmtDate(r.retrievedAt))+'</p>'+
 (typeof r.records==='number'?'<p class="text-xs text-slate-500 dark:text-slate-300">Registros: '+nf(r.records)+'</p>':'')+
 (r.method||r.note?'<p class="text-xs leading-relaxed text-slate-500 dark:text-slate-300 mt-3">'+safe(r.method||r.note)+'</p>':'')+
 (r.url&&/^https:\/\//.test(r.url)?'<a class="mt-3 inline-flex text-xs font-semibold underline text-teal-700 dark:text-teal-300" href="'+safe(r.url)+'" target="_blank" rel="noopener noreferrer">Consultar fonte oficial ↗</a>':'')+'</article>';
export async function mountSources(summary:DataSummary){
 const token=++active;
 const status=document.getElementById('source-status');
 const parent=document.getElementById('source-groups');
 if(!status||!parent)return;
 const rows:Row[]=Object.entries(summary.sourceInfo||{}).map(([id,item])=>({
  id,family:'IBGE, cadastro CNES e leitos',...item}));
 async function readOptional(file:string):Promise<Json|null>{
  try{
   const res=await fetch(urlAsset('data/'+file),{cache:'no-cache'});
   if(!res.ok)return null;
   const doc=await res.json();
   return doc&&typeof doc.sources==='object'?doc:null;
  }catch{return null}
 }
 const [health,sus]=await Promise.all([readOptional('indicators.json'),readOptional('sus.json')]);
 if(token!==active||!parent.isConnected)return;
 for(const [group,document] of [['Vigilância e estatísticas vitais',health],['Assistência, APS e financiamento',sus]] as const){
  if(!document)continue;
  for(const [id,item] of Object.entries(document.sources)){
   const series=document.series?.[id]||[];
   const reference=String(item.reference|| (series.length?(series[series.length-1].period||series[series.length-1].year||''):''));
   rows.push({id,family:group,...item,reference,years:item.yearsAvailable?.length?item.yearsAvailable.join(', '):undefined});
  }
 }
 const duplicates=new Set<string>();
 const list=rows.filter(row=>{const k=row.family+':'+row.id;if(duplicates.has(k))return false;duplicates.add(k);return true});
 const groups=['IBGE, cadastro CNES e leitos','Vigilância e estatísticas vitais','Assistência, APS e financiamento'];
 function render(){
  const filter=(document.querySelector<HTMLSelectElement>('#sources-filter')?.value||'all');
  const q=(document.querySelector<HTMLInputElement>('#sources-search')?.value||'').toLocaleLowerCase('pt-BR');
  const display=list.filter(r=>(filter==='all'||filter==='ok'&&r.status==='ok'||filter==='pending'&&r.status!=='ok')&&
   (!q||[r.label,r.id,r.note,r.method,r.family].some(x=>String(x||'').toLocaleLowerCase('pt-BR').includes(q))));
  parent.innerHTML=groups.map(name=>{
   const group=display.filter(r=>r.family===name);
   if(!group.length)return '';
   return '<section><h3 class="subheading text-base mb-3">'+safe(name)+' <span class="text-xs font-normal text-slate-500">('+group.length+')</span></h3>'+
    '<div class="grid grid-cols-1 md:grid-cols-2 gap-3">'+group.map(sourceCard).join('')+'</div></section>';
  }).join('')||'<div class="empty p-4">Nenhuma fonte corresponde ao filtro.</div>';
  status.textContent=list.filter(x=>x.status==='ok').length+' fontes/indicadores disponíveis de '+list.length+' cadastrados. '+display.length+' exibidos.';
 }
 render();
 document.getElementById('sources-filter')?.addEventListener('change',render);
 document.getElementById('sources-search')?.addEventListener('input',render);
 const exportButton=document.querySelector<HTMLButtonElement>('#source-export');
 if(exportButton){exportButton.disabled=false;exportButton.onclick=()=>dlCsv(list.map(r=>({
  Categoria:r.family,Indicador:r.label||r.id,Situacao:statusText(r.status||''),Referencia:r.reference||'',
  Unidade:r.unit||'',Fonte:r.url||'',Metodologia:r.method||r.note||'',Coleta:r.retrievedAt||''
 })),'catalogo-fontes-webgis-saude-canoas.csv')}
}