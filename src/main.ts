import './style.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import {createIcons, LayoutDashboard, MapPinned, Building2, Database, HeartPulse, Moon, Sun, Download, Activity, Users, Hospital, BedDouble, TrendingUp, RefreshCw, MapPin, Search, ExternalLink, Info, ArrowUpRight, BarChart3, Filter, Menu, X, ChevronRight, ClipboardList} from 'lucide';
import {getData} from './lib/data';
import {leafletFallback} from './lib/leafletFallback';
import {healthPage,mountHealth,disposeHealth} from './lib/healthView';
import {susPage,mountSus,stopSus} from './lib/susView';
import {municipalPage,mountMunicipal,stopMunicipal} from './lib/municipalView';
import {sourcesPage as sourcesV2Page,mountSources,stopSources} from './lib/sourcesView';
import {farmaciaSiapsPage,mountFarmaciaSiaps,stopFarmaciaSiaps} from './lib/farmaciaSiapsView';
import {productionPage,mountProduction,stopProduction} from './lib/productionView';
import {allFacilities,loadFacilityCatalog,facilityExplorerMarkup,mountFacilityExplorer,selectedCnes,selectedFacility,getFacility,pickFacility,facilityPopupHTML} from './lib/facilityExplorer';
import {dec,dlCsv,fmtDate,nf,safe,urlAsset} from './lib/utils';
import type {DataSummary,FacilitiesGeoJSON,FacilityFeature} from './lib/types';

type Page='municipal'|'overview'|'map'|'facilities'|'health'|'vital'|'sus'|'farmacia-siaps'|'aps-history'|'screening'|'finance'|'production'|'sources';
const state:{page:Page;dark:boolean;type:string;year:string;search:string;summary:DataSummary|null;geo:FacilitiesGeoJSON|null;map:any;charts:any[];chartObserver:ResizeObserver|null;error:string|null}={page:'municipal',dark:localStorage.getItem('saude-theme')==='dark',type:'all',year:'all',search:'',summary:null,geo:null,map:null,charts:[],chartObserver:null,error:null};
const app=document.querySelector<HTMLElement>('#app')!;
const repoUrl='https://github.com/marcianolima/webgis-saude-canoas';

const icon=(name:string,size=18)=>`<i data-lucide="${name}" style="width:${size}px;height:${size}px;stroke-width:2"></i>`;
function icons(){createIcons({icons:{LayoutDashboard,MapPinned,Building2,Database,HeartPulse,Moon,Sun,Download,Activity,Users,Hospital,BedDouble,TrendingUp,RefreshCw,MapPin,Search,ExternalLink,Info,ArrowUpRight,BarChart3,Filter,Menu,X,ChevronRight,ClipboardList}})}

type NavEntry={page:Page;label:string;icon:string};
const navEntries:NavEntry[]=[
 {page:'municipal',label:'Panorama municipal',icon:'layout-dashboard'},
 {page:'overview',label:'Rede e território',icon:'bar-chart-3'},
 {page:'map',label:'Mapa',icon:'map-pinned'},
 {page:'facilities',label:'Estabelecimentos',icon:'building-2'},
 {page:'health',label:'Vigilância',icon:'activity'},
 {page:'vital',label:'Nascimentos e óbitos',icon:'users'},
 {page:'sus',label:'Atenção Primária',icon:'heart-pulse'},
 {page:'farmacia-siaps',label:'Farmácia e SIAPS',icon:'heart-pulse'},
 {page:'aps-history',label:'APS · histórico',icon:'trending-up'},
 {page:'screening',label:'Prevenção e exames',icon:'heart-pulse'},
 {page:'finance',label:'Financiamento e RIPSA',icon:'bar-chart-3'},
 {page:'production',label:'Produção SIH/SIA',icon:'clipboard-list'},
 {page:'sources',label:'Fontes e metodologia',icon:'database'}
];
type NavGroup={id:string;label:string;icon:string;pages:Page[]};
const navGroups:NavGroup[]=[
 {id:'territorio',label:'Território e rede',icon:'map-pinned',pages:['overview','map','facilities']},
 {id:'assistencia',label:'Saúde e atendimento',icon:'heart-pulse',pages:['health','vital','sus','farmacia-siaps','aps-history','screening']},
 {id:'indicadores',label:'Financiamento e produção',icon:'bar-chart-3',pages:['finance','production']}
];
const expandedGroups=new Set<string>(['territorio']);
function nav(mode:'desktop'|'mobile'){
 const link=(page:Page)=>{
  const entry=navEntries.find(item=>item.page===page)!;
  return '<button type="button" data-page="'+page+'" aria-current="'+(state.page===page?'page':'false')+'" class="sidebar-link '+(state.page===page?'active':'')+'">'+icon(entry.icon)+'<span>'+entry.label+'</span></button>';
 };
 navGroups.filter(group=>group.pages.includes(state.page)).forEach(group=>expandedGroups.add(group.id));
 return link('municipal')+'<p class="nav-caption">Explorar informações</p>'+navGroups.map(group=>{
  const expanded=expandedGroups.has(group.id);
  const selected=group.pages.includes(state.page);
  const panelId='nav-'+mode+'-'+group.id;
  return '<section class="nav-group" aria-label="'+group.label+'"><button type="button" data-nav-group="'+group.id+'" aria-expanded="'+expanded+'" aria-controls="'+panelId+'" class="sidebar-link nav-group-toggle '+(selected?'group-selected':'')+'">'+icon(group.icon)+'<span>'+group.label+'</span>'+icon('chevron-right',15)+'</button><div id="'+panelId+'" data-group-items="'+group.id+'" class="nav-group-items" '+(expanded?'':'hidden')+'>'+group.pages.map(link).join('')+'</div></section>';
 }).join('')+'<p class="nav-caption nav-caption-support">Apoio</p>'+link('sources');
}
const pageTitles:Record<Page,string>={municipal:'Painel Municipal de Saúde',overview:'Análise territorial',map:'Mapa interativo',facilities:'Rede assistencial',health:'Vigilância epidemiológica',vital:'Nascimentos e mortalidade',sus:'Atenção Primária','farmacia-siaps':'Farmácia e SIAPS','aps-history':'APS · indicadores históricos',screening:'Prevenção e rastreamento',finance:'Financiamento e RIPSA',production:'Produção SIH/SIA por CNES',sources:'Transparência dos dados'};
type HeaderAction={page:Page;label:string;icon:string};
const headerActions:Partial<Record<Page,HeaderAction[]>>={
 municipal:[{page:'sources',label:'Fontes',icon:'database'}],
 overview:[{page:'health',label:'Vigilância',icon:'activity'},{page:'production',label:'Produção',icon:'clipboard-list'}],
 health:[{page:'vital',label:'Nascimentos e óbitos',icon:'users'}],
 vital:[{page:'health',label:'Vigilância',icon:'activity'}],
 sus:[{page:'farmacia-siaps',label:'Farmácia e SIAPS',icon:'heart-pulse'},{page:'aps-history',label:'Histórico APS',icon:'trending-up'},{page:'production',label:'Produção',icon:'clipboard-list'}],
 'farmacia-siaps':[{page:'sus',label:'Atenção Primária',icon:'heart-pulse'},{page:'sources',label:'Fontes',icon:'database'}],
 'aps-history':[{page:'sus',label:'APS atual',icon:'heart-pulse'},{page:'production',label:'Produção',icon:'clipboard-list'}],
 screening:[{page:'sus',label:'Atenção Primária',icon:'heart-pulse'}],
 map:[{page:'facilities',label:'Estabelecimentos',icon:'building-2'}],
 facilities:[{page:'map',label:'Mapa',icon:'map-pinned'}],
 finance:[{page:'production',label:'Produção',icon:'clipboard-list'}],
 production:[{page:'finance',label:'Financiamento',icon:'bar-chart-3'}]
};
function top(){
 const actions=(headerActions[state.page]||[]).map(action=>'<button type="button" data-page="'+action.page+'" aria-label="'+action.label+'" title="'+action.label+'" class="header-shortcut">'+icon(action.icon,15)+'<span>'+action.label+'</span></button>').join('');
 return `<header class="health-topbar px-3 sm:px-6 flex items-center justify-between gap-2 bg-white/95 dark:bg-[#142638] border-b border-slate-100 dark:border-slate-700 sticky top-0 z-30 backdrop-blur-md"><div class="flex min-w-0 items-center gap-2 sm:gap-3"><button type="button" data-open-nav class="mobile-menu-trigger lg:hidden" aria-label="Abrir menu principal" aria-controls="mobile-drawer" aria-expanded="false">${icon('menu',20)}</button><span class="mobile-brand-mark lg:hidden" aria-hidden="true">${icon('heart-pulse',17)}</span><div class="min-w-0"><p class="text-[9px] font-bold tracking-[.12em] uppercase text-teal-700 dark:text-emerald-300 hidden sm:block">Inteligência em saúde pública</p><h1 class="heading text-[15px] sm:text-base truncate">${pageTitles[state.page]}</h1></div></div><div class="header-actions flex shrink-0 items-center gap-1.5 sm:gap-2">${actions}<button id="theme" class="h-9 w-9 rounded-lg border border-slate-200 dark:border-slate-700 grid place-items-center" aria-label="Alternar tema">${icon(state.dark?'sun':'moon')}</button><a href="${repoUrl}" target="_blank" rel="noopener noreferrer" aria-label="Repositório GitHub" class="h-9 px-2 sm:px-3 rounded-lg border border-slate-200 dark:border-slate-700 text-teal-800 dark:text-teal-200 text-xs font-bold flex items-center gap-1.5">${icon('external-link',15)}<span class="hidden md:inline">GitHub</span></a></div></header>`;
}
function layout(body:string){return `<div class="app-shell"><a class="skip-link" href="#conteudo-principal">Pular para o conteúdo principal</a><div id="mobile-drawer" class="health-drawer" hidden><button type="button" class="drawer-backdrop" data-close-nav aria-label="Fechar menu"></button><aside class="drawer-panel" role="dialog" aria-modal="true" aria-label="Menu principal móvel"><div class="drawer-head"><div class="flex items-center gap-2"><div class="brand-mark">${icon('heart-pulse',20)}</div><strong class="text-white text-sm">WebGIS Saúde</strong></div><button type="button" data-close-nav id="close-nav" aria-label="Fechar menu principal" class="drawer-close">${icon('x',19)}</button></div><nav class="drawer-nav" aria-label="Menu principal móvel">${nav('mobile')}</nav><div class="drawer-foot"><a href="https://geo.canoas.rs.gov.br/" target="_blank" rel="noopener noreferrer">Portal GeoCanoas ↗</a></div></aside></div><aside class="sidebar px-3 py-5"><div class="flex items-center gap-3 px-3"><div class="brand-mark">${icon('heart-pulse',24)}</div><div><p class="text-white font-display font-extrabold leading-tight">WebGIS Saúde</p><p class="text-xs font-semibold tracking-widest text-[#64d2bd]">CANOAS / RS</p></div></div><nav class="health-desktop-nav mt-5" aria-label="Menu principal">${nav('desktop')}</nav><div class="mt-auto mx-1 p-4 bg-[#1b3b4e] rounded-2xl"><p class="text-[11px] text-[#92bac8] uppercase font-bold tracking-widest">Projeto de dados abertos</p><p class="text-white text-sm mt-1 font-bold">Transparência territorial em saúde</p><p class="text-xs text-[#a9c5d1] mt-2 leading-relaxed">Informações públicas com fonte e referência identificadas.</p></div><p class="text-[11px] text-[#7895a7] mx-3 mt-5"><a href="https://geo.canoas.rs.gov.br/" target="_blank" rel="noopener noreferrer" class="underline hover:text-white">Portal GeoCanoas</a> · Versão 1.4</p></aside><div class="main-shift">${top()}<main id="conteudo-principal" tabindex="-1" class="content-width px-4 sm:px-6 lg:px-9 py-6 lg:py-8">${state.error?`<div role="alert" class="mb-5 p-4 border border-amber-200 bg-amber-50 text-amber-900 rounded-xl text-sm">${safe(state.error)}</div>`:''}${['overview','facilities','production'].includes(state.page)?facilityExplorerMarkup():''}${body}</main><footer class="px-6 lg:px-10 pb-8 text-xs text-slate-400 flex flex-wrap justify-between gap-3"><span>© ${new Date().getFullYear()} WebGIS Saúde Canoas · Projeto demonstrativo de dados públicos</span><span>Não substitui sistemas oficiais do SUS · <a class="underline" href="${repoUrl}" target="_blank" rel="noopener noreferrer">Código-fonte</a></span></footer></div></div>`}
function label(title:string,sub:string){return `<div class="mb-5"><h2 class="subheading text-[22px] md:text-[27px]">${title}</h2><p class="text-sm text-slate-500 dark:text-slate-400 mt-1">${sub}</p></div>`}
function kpi(title:string,value:string,sub:string,iconName:string,bg:string,tag=''){return `<article class="panel kpi p-4 sm:p-5"><div class="flex justify-between items-start"><span class="text-xs sm:text-sm font-semibold text-slate-500 dark:text-slate-300">${title}</span><div class="kpi-icon" style="background:${bg}">${icon(iconName,20)}</div></div><div class="kpi-val mt-3">${value}</div><div class="text-[11px] mt-1 flex items-center justify-between gap-1 text-slate-400">${sub}${tag?`<span class="font-bold text-teal-600">${tag}</span>`:''}</div></article>`}
function panelHeading(title:string,desc:string){return `<div class="flex flex-wrap gap-2 justify-between items-start mb-3"><div><h3 class="subheading text-[15px] md:text-base">${title}</h3><p class="text-xs text-slate-400 mt-1">${desc}</p></div></div>`}
function dataNotice(){
 const info=state.summary?.sourceInfo.cnes;
 if(info?.status==='ok')return '';
 const message=info?.status==='error'?'A coleta do CNES falhou. Consulte o histórico do GitHub Actions.':'A primeira coleta do CNES ainda não foi concluída. Por isso, os quantitativos e pontos de saúde estão indisponíveis.';
 return `<div role="status" class="mb-5 p-4 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-100 text-sm flex flex-wrap items-center gap-2">${icon('info',16)}<span>${message}</span><a target="_blank" rel="noopener noreferrer" href="${repoUrl}/actions/workflows/update-data.yml" class="underline font-bold">Acompanhar coleta</a></div>`;
}
function overview(){const s=state.summary!,f=s.facilities,m=s.municipality,picked=selectedFacility();return `${label(picked?'Painel do estabelecimento':'Panorama da saúde em Canoas',picked?'Dados individuais por CNES e comparação cadastral territorial.':'Explore indicadores e a distribuição territorial dos serviços de saúde.')}${dataNotice()}
<div class="mb-5 flex flex-wrap items-center gap-2"><span class="pill bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-200">${icon('map-pin',12)} Canoas, Rio Grande do Sul</span><span class="pill bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-300">IBGE ${m.ibge}</span><span class="text-xs text-slate-400 ml-auto">Última atualização: ${fmtDate(s.generatedAt)}</span></div>
<section aria-label="Indicadores principais" class="grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 mb-5">${kpi(picked?'Leitos existentes':'População',picked?nf(picked.bedsTotal):nf(m.population??m.censusPopulation),picked?('Competência '+(picked.bedsAsOf||'não informada')):(m.populationYear?`Estimativa ${m.populationYear}`:`Censo ${m.censusYear??'—'}`),'users','#ecf4ff')}${kpi(picked?'Leitos SUS':'Estabelecimentos',picked?nf(picked.bedsSus):nf(f.total),picked?'Estabelecimento selecionado':'CNES · Todas as unidades','building-2','#eafaf3')}${kpi(picked?'Leitos UTI':'Unidades básicas',picked?nf(picked.utiTotal):nf(f.ubs),picked?'Subconjunto dos leitos da unidade':'Classificação CNES','heart-pulse','#e6f6f9')}${kpi(picked?'Coordenadas':'Hospitais',picked?(picked.coordinates?'Sim':'—'):nf(f.hospitals),picked?'Geolocalização da unidade':'Classificação CNES','hospital','#fff4e9')}</section>
<section class="grid grid-cols-1 xl:grid-cols-12 gap-4 mb-5"><article class="panel p-5 xl:col-span-7">${panelHeading(picked?'Tipos no bairro selecionado':'Estabelecimentos por tipo',picked?'Bairro: '+picked.neighborhood+' · não é atendimento clínico':'Classificação disponível na fonte CNES')}<div id="type-chart" class="chart chart-tall"></div></article><article class="panel p-5 xl:col-span-5">${panelHeading(picked?'Capacidade da unidade':'Indicadores complementares',picked?'Os dados de leitos são individuais, por competência CNES.':'Informações divulgadas pelas fontes oficiais')}<div class="grid grid-cols-2 gap-3 mt-6">${mini(picked?'Leitos existentes':'Leitos totais',nf(picked?picked.bedsTotal:s.beds.total),'bed-double')}${mini('Leitos SUS',nf(picked?picked.bedsSus:s.beds.sus),'heart-pulse')}${mini('Com coordenadas',picked?(picked.coordinates?'Sim':'Não'):nf(f.withCoordinates),'map-pin')}${mini(picked?'Leitos UTI':'Densidade',picked?nf(picked.utiTotal):(m.density===null?'—':dec(m.density)+' hab/km²'),'users')}</div><div class="mt-6 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl text-xs text-amber-800 dark:text-amber-200 flex gap-2">${icon('info',15)} Valores sem integração validada aparecem como “—”, nunca como zero.</div></article></section>
<section class="grid grid-cols-1 xl:grid-cols-12 gap-4 mb-5"><article class="panel p-5 xl:col-span-7">${panelHeading('Evolução demográfica · IBGE','População residente de Canoas por ano de referência. Este número é municipal e não pertence à unidade selecionada.')}<div class="flex flex-wrap items-center gap-2 mb-2"><label class="text-xs text-slate-500 font-semibold">Ano <select id="year-filter" aria-label="Filtrar ano das séries temporais" class="field ml-2">${['all',...new Set(Object.values(s.series).flat().map(x=>String(x.year)))].map(v=>`<option value="${v}" ${state.year===v?'selected':''}>${v==='all'?'Todos':v}</option>`).join('')}</select></label></div><div id="time-chart" class="chart"></div><p id="series-method" class="text-xs text-slate-500 dark:text-slate-300 mt-2">População de residentes conforme referência IBGE. Não representa usuários do SUS nem pacientes atendidos.</p></article><article class="panel p-5 xl:col-span-5">${panelHeading('Distribuição no território','Pontos com coordenadas disponíveis')}<div id="small-map" class="map-container map-short"></div><button class="text-teal-700 dark:text-teal-300 text-xs font-bold flex items-center gap-1 mt-4" data-page="map">Explorar mapa completo ${icon('arrow-up-right',13)}</button></article></section>
<section class="panel p-5 mb-5">${panelHeading(picked?'Estabelecimentos do mesmo grupo por bairro':'Unidades cadastradas por bairro',picked?'Categoria CNES: '+picked.type+' · contagem territorial, não taxa de atendimento.':'Bairro declarado no CNES; não representa taxa populacional')}<div id="neighborhood-chart" class="chart chart-tall"></div></section><div class="panel p-4 sm:p-5 flex flex-wrap items-center justify-between gap-3"><div class="flex gap-3 items-center"><div class="kpi-icon bg-mint dark:bg-slate-700">${icon('database',19)}</div><div><p class="font-bold text-sm">Metodologia e proveniência dos dados</p><p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Consulte fontes, cobertura e data de referência de cada indicador.</p></div></div></div>`}
function mini(t:string,v:string,i:string){return `<div class="border metric-rule border-slate-100 dark:border-slate-700 rounded-xl p-4"><div class="flex items-center gap-2 text-teal-700 dark:text-emerald-300">${icon(i,16)}<span class="text-xs text-slate-500 dark:text-slate-300">${t}</span></div><p class="kpi-val !text-xl mt-3">${v}</p></div>`}
function options(){return `<option value="all">Todos os estabelecimentos</option><option value="ubs" ${state.type==='ubs'?'selected':''}>Atenção básica / UBS</option><option value="hospital" ${state.type==='hospital'?'selected':''}>Hospitais</option><option value="urgencia" ${state.type==='urgencia'?'selected':''}>Urgência / emergência</option><option value="clinica" ${state.type==='clinica'?'selected':''}>Clínicas / especialidades</option><option value="outros" ${state.type==='outros'?'selected':''}>Outras unidades</option><option value="beds" ${state.type==='beds'?'selected':''}>Com leitos confirmados</option>`}
function filtered(){const needle=state.search.toLocaleLowerCase('pt-BR');return(state.geo?.features??[]).filter(f=>(state.type==='all'||(state.type==='beds'?f.properties.hasBeds===true:f.properties.category===state.type))&&(!needle||[f.properties.name,f.properties.type,f.properties.neighborhood,f.properties.cnes].some(s=>String(s).toLocaleLowerCase('pt-BR').includes(needle))))}
function filteredFacilities(){const needle=state.search.toLocaleLowerCase('pt-BR');return allFacilities().filter(f=>(state.type==='all'||(state.type==='beds'?f.hasBeds===true:f.category===state.type))&&(!needle||[f.name,f.type,f.neighborhood,f.cnes].some(s=>String(s).toLocaleLowerCase('pt-BR').includes(needle))))}
function mapPage(){return `${label('Mapa de estabelecimentos','Mapa das unidades de saúde com coordenadas válidas no CNES. As unidades sem geolocalização continuam disponíveis na lista de estabelecimentos.')}${dataNotice()}<div class="panel p-3 sm:p-5"><div class="flex flex-col md:flex-row gap-3 mb-4"><label class="flex-1"><span class="sr-only">Pesquisar estabelecimento</span><div class="relative">${icon('search',17)}<input id="search" class="field w-full pl-9" placeholder="Nome, CNES ou bairro" value="${safe(state.search)}" /></div></label><label class="md:w-64"><span class="sr-only">Filtrar por tipo</span><select id="type-filter" class="field w-full">${options()}</select></label><button id="export" class="h-10 rounded-xl bg-[#0d857e] text-white text-xs font-bold px-4 inline-flex items-center gap-2 justify-center">${icon('download',15)} Exportar CSV</button></div><div class="flex gap-3 items-center justify-between mb-3 text-xs text-slate-500 dark:text-slate-300"><span><b id="filtered-count">${filtered().length}</b> unidades geolocalizadas no filtro</span><span class="hidden md:inline">Clique nos pontos para obter detalhes</span></div><div id="main-map" class="map-container"></div><p class="text-[11px] text-slate-400 mt-3">Posições são provenientes do CNES e podem conter imprecisões. Mapa © OpenStreetMap / CARTO.</p></div>`}
function facilitiesPage(){return `${label('Rede de estabelecimentos','Catálogo CNES com todas as unidades cadastradas, incluindo aquelas sem coordenadas para o mapa.')}<section class="panel p-4 sm:p-6"><div class="flex flex-col sm:flex-row gap-3 mb-5"><input id="search" class="field flex-1" placeholder="Pesquisar nome, bairro, CNES…" value="${safe(state.search)}" aria-label="Pesquisar"/><select id="type-filter" class="field sm:w-64" aria-label="Tipo">${options()}</select><button id="export" class="rounded-xl bg-[#0d857e] text-white text-xs font-bold px-4 py-3 flex justify-center items-center gap-2">${icon('download',15)} CSV</button></div><p class="text-xs text-slate-500 mb-3"><span id="filtered-count">${filteredFacilities().length}</span> unidades encontradas</p><div id="facility-list" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">${facilityList()}</div></section>`}
function facilityList(){
 const rows=filteredFacilities();
 if(!rows.length)return '<div class="empty col-span-full">Nenhum estabelecimento encontrado para os filtros aplicados.</div>';
 return rows.slice(0,180).map(f=>'<button type="button" data-facility-item="'+safe(f.cnes)+'" aria-label="Selecionar '+safe(f.name)+'" '+
 'class="text-left p-4 rounded-xl border border-slate-100 dark:border-slate-700 hover:border-teal-300 focus-visible:ring-2 focus-visible:ring-teal-600 '+(selectedCnes()===f.cnes?'ring-2 ring-teal-500 bg-teal-50 dark:bg-teal-900/20':'')+'">'+
 '<span class="pill bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300">'+safe(f.type)+'</span>'+
 '<h3 class="subheading text-sm mt-3 leading-snug">'+safe(f.name)+'</h3>'+
 '<p class="text-xs text-slate-500 dark:text-slate-300 mt-2">'+icon('map-pin',13)+' '+safe(f.address||'Endereço não informado')+'</p>'+
 '<p class="text-xs text-slate-400 mt-2">'+safe(f.neighborhood||'Bairro não informado')+' · CNES '+safe(f.cnes)+'</p>'+
 '<p class="text-xs font-semibold text-teal-700 dark:text-teal-300 mt-3">Leitos: '+(f.bedsTotal===null?'sem dado individual':nf(f.bedsTotal))+
 (f.coordinates?' · Localizado no mapa':' · Sem coordenadas')+' · Selecionar →</p></button>').join('')+
 (rows.length>180?'<div class="text-sm text-slate-500 p-4">Exibindo 180 de '+nf(rows.length)+'. Refine a pesquisa para localizar outros estabelecimentos.</div>':'');
}
function sourcesPage(){const s=state.summary!;const list=Object.entries(s.sourceInfo);return `${label('Sobre os dados','Transparência, metodologia, referências e atualização automatizada.')}<div class="panel p-5 mb-4"><div class="flex gap-3 items-center">${icon('info',21)}<div><h3 class="subheading text-base">Critérios de interpretação</h3><p class="text-sm text-slate-500 dark:text-slate-300 mt-1">Os valores refletem a competência da fonte, que pode ser diferente da data de coleta.</p></div></div><div class="mt-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed space-y-2"><p>Unidades e tipos: registros cadastrais CNES no município; não representam automaticamente estabelecimentos ativos exclusivamente SUS. Totais incluem registros sem posição; o mapa exibe apenas coordenadas válidas.</p><p>Hospitais e UBS: categorias classificadas pelo código/tipo CNES. Leitos: quantidade informada pela fonte, sem dedução a partir do tipo de estabelecimento.</p><p>Séries temporais: nunca somar totais de naturezas distintas. Indicadores SIH por local de internação não equivalem necessariamente a internações de residentes; notificações de dengue não equivalem à incidência epidemiológica sem denominador e definição de caso.</p><p>As fontes oficiais possuem periodicidades e metodologias próprias. Dados indisponíveis permanecem vazios, com registro do motivo.</p></div></div><div class="panel p-5"><h3 class="subheading text-base mb-4">Catálogo de fontes e estado da coleta</h3><div class="space-y-3">${list.map(([key,item])=>`<article class="border border-slate-100 dark:border-slate-700 rounded-xl p-4"><div class="flex justify-between gap-2 flex-wrap"><h4 class="font-bold text-sm">${safe(item.label)}</h4><span class="pill ${item.status==='ok'?'bg-emerald-50 text-emerald-700':'bg-amber-50 text-amber-700'}">${item.status==='ok'?'Disponível':item.status==='partial'?'Parcial':item.status==='error'?'Falha na coleta':'Não integrado'}</span></div><p class="text-xs text-slate-500 dark:text-slate-400 mt-2">Referência: ${safe(item.reference||'não informada')} · Coleta: ${fmtDate(item.retrievedAt)}</p>${item.note?`<p class="text-xs text-slate-400 mt-2">${safe(item.note)}</p>`:''}<a href="${safe(item.url)}" target="_blank" rel="noopener noreferrer" class="mt-3 text-xs font-bold text-teal-700 dark:text-teal-300 inline-flex items-center gap-1">Consultar fonte oficial ${icon('external-link',13)}</a></article>`).join('')}</div></div><p class="text-xs mt-4 text-slate-500">Arquivo de metadados atualizado em ${fmtDate(s.generatedAt)}. O workflow do GitHub Actions registra resultados individuais das integrações.</p>`}
let drawerLastFocus:HTMLElement|null=null;
function toggleMobileDrawer(open:boolean){
 const drawer=document.querySelector<HTMLElement>('#mobile-drawer');
 const trigger=document.querySelector<HTMLButtonElement>('[data-open-nav]');
 if(!drawer||!trigger)return;
 if(open)drawerLastFocus=document.activeElement instanceof HTMLElement?document.activeElement:null;
 drawer.hidden=!open;
 document.querySelector<HTMLElement>('.main-shift')?.toggleAttribute('inert',open);
 trigger.setAttribute('aria-expanded',String(open));
 document.body.classList.toggle('nav-lock',open);
 if(open){
  drawer.querySelector<HTMLElement>('.sidebar-link.active')?.scrollIntoView({block:'nearest',behavior:'auto'});
  drawer.querySelector<HTMLButtonElement>('#close-nav')?.focus();
 }else{(drawerLastFocus||trigger).focus();drawerLastFocus=null;}
}
function toggleNavGroup(id:string){
 if(expandedGroups.has(id))expandedGroups.delete(id);else expandedGroups.add(id);
 document.querySelectorAll<HTMLButtonElement>('[data-nav-group="'+id+'"]').forEach(el=>el.setAttribute('aria-expanded',String(expandedGroups.has(id))));
 document.querySelectorAll<HTMLElement>('[data-group-items="'+id+'"]').forEach(el=>el.hidden=!expandedGroups.has(id));
}
document.addEventListener('keydown',event=>{
 const drawer=document.querySelector<HTMLElement>('#mobile-drawer');
 if(!drawer||drawer.hidden)return;
 if(event.key==='Escape'){event.preventDefault();toggleMobileDrawer(false);return}
 if(event.key!=='Tab')return;
 const focusable=Array.from(drawer.querySelectorAll<HTMLElement>('.drawer-panel button:not([disabled]),.drawer-panel a[href],.drawer-panel input:not([disabled]),.drawer-panel select:not([disabled])')).filter(el=>el.getClientRects().length>0);
 if(!focusable.length){event.preventDefault();return}
 const first=focusable[0],last=focusable[focusable.length-1];
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
 else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
});

function render(){if(!state.summary)return;disposeHealth();stopSus();stopMunicipal();stopSources();stopFarmaciaSiaps();stopProduction();document.documentElement.classList.toggle('dark',state.dark);state.chartObserver?.disconnect();state.chartObserver=null;state.map?.remove();state.map=null;state.charts.forEach(x=>x.dispose());state.charts=[];app.innerHTML=layout(({municipal:()=>municipalPage(state.summary!),overview,map:mapPage,facilities:facilitiesPage,health:()=>healthPage('surveillance'),vital:()=>healthPage('vital'),sus:()=>susPage('primary'),'aps-history':()=>susPage('historic'),screening:()=>susPage('screening'),finance:()=>susPage('finance'),production:productionPage,'farmacia-siaps':farmaciaSiapsPage,sources:sourcesV2Page} as Record<Page,()=>string>)[state.page]());icons();document.body.classList.remove('nav-lock');mountFacilityExplorer();app.onclick=(event)=>{const targetNode=event.target as HTMLElement;const group=targetNode.closest<HTMLButtonElement>('[data-nav-group]');if(group){toggleNavGroup(group.dataset.navGroup!);return;}if(targetNode.closest('[data-open-nav]')){toggleMobileDrawer(true);return;}if(targetNode.closest('[data-close-nav]')){toggleMobileDrawer(false);return;}const button=targetNode.closest<HTMLButtonElement>('[data-page]');if(!button)return;const target=button.dataset.page as Page;if(!target)return;if(state.page===target){toggleMobileDrawer(false);return;}state.page=target;state.search='';state.type='all';render();document.querySelector<HTMLElement>('#conteudo-principal')?.focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});};document.querySelector<HTMLButtonElement>('#theme')!.onclick=()=>{state.dark=!state.dark;localStorage.setItem('saude-theme',state.dark?'dark':'light');render()};document.querySelector<HTMLSelectElement>('#type-filter')?.addEventListener('change',e=>{state.type=(e.target as HTMLSelectElement).value;refreshFilters()});document.querySelector<HTMLInputElement>('#search')?.addEventListener('input',e=>{state.search=(e.target as HTMLInputElement).value;refreshFilters()});document.querySelector<HTMLButtonElement>('#export')?.addEventListener('click',()=>dlCsv((state.page==='facilities'?filteredFacilities():filtered().map(f=>({...f.properties,coordinates:f.geometry.coordinates}))).map(f=>({CNES:f.cnes,Nome:f.name,Tipo:f.type,Bairro:f.neighborhood,Endereço:f.address,Telefone:f.phone,Leitos:f.bedsTotal??null,LeitosSUS:f.bedsSus??null,Latitude:f.coordinates?.[1]??null,Longitude:f.coordinates?.[0]??null})),'cnes-canoas-filtrado.csv'));if(state.page==='municipal')void mountMunicipal(state.dark);if(state.page==='sources')void mountSources(state.summary!);if(state.page==='farmacia-siaps')void mountFarmaciaSiaps();if(state.page==='health'||state.page==='vital')void mountHealth(state.dark,state.summary!,state.page==='vital'?'vital':'surveillance');
 if(state.page==='sus'||state.page==='aps-history'||state.page==='screening'||state.page==='finance')void mountSus(state.dark,state.page==='aps-history'?'historic':state.page==='screening'?'screening':state.page==='finance'?'finance':'primary');if(state.page==='production')void mountProduction(state.dark);if(state.page==='overview'){void charts().catch(error=>showViewError('Os gráficos não puderam ser carregados',error));void initMap('small-map',true).catch(error=>showViewError('O mapa não pôde ser carregado',error))}else if(state.page==='map')void initMap('main-map',false).catch(error=>showViewError('O mapa não pôde ser carregado',error))}
function refreshFilters(){const count=document.querySelector('#filtered-count');if(count)count.textContent=String(state.page==='facilities'?filteredFacilities().length:filtered().length);if(state.page==='facilities')document.querySelector('#facility-list')!.innerHTML=facilityList();if(state.page==='map')setMapPoints()}
function showViewError(message:string,error:unknown){
 console.error(message,error);
 const box=document.createElement('div');box.setAttribute('role','alert');box.className='panel p-4 mb-4 text-sm text-amber-700 dark:text-amber-300';box.textContent=message+'. Verifique a conexão ou recarregue a página.';
 document.querySelector('main')?.prepend(box);
}
async function charts(){const echarts=await import('echarts');const muted=state.dark?'#9cb3c6':'#7890a3';const axis={axisLine:{show:false},axisTick:{show:false},axisLabel:{color:muted,fontSize:11},splitLine:{lineStyle:{color:state.dark?'#30445a':'#edf1f5'}}};const create=(id:string,opts:any)=>{const el=document.getElementById(id);if(!el||state.page!=='overview')return null;const c=echarts.init(el);c.setOption(opts);state.charts.push(c);return c};const picked=selectedFacility();
const sameNeighborhood=picked?allFacilities().filter(f=>f.neighborhood===picked.neighborhood):[];
const sameCategory=picked?allFacilities().filter(f=>f.category===picked.category):[];
const countBy=(records:typeof sameNeighborhood,key:(r:typeof sameNeighborhood[number])=>string)=>
  Array.from(records.reduce((acc,record)=>acc.set(key(record),(acc.get(key(record))||0)+1),
  new Map<string,number>()),([name,value])=>({name,value})).sort((a,b)=>b.value-a.value).slice(0,9);
const byType=picked?countBy(sameNeighborhood,r=>r.type):state.summary!.facilities.byType.slice(0,9);
const byNeighborhood=picked?countBy(sameCategory,r=>r.neighborhood):state.summary!.facilities.byNeighborhood.slice(0,9);const chooseGroup=(c:any)=>{c?.on('click',(evt:any)=>{if(!evt?.name)return;state.page='facilities';state.type='all';state.search=String(evt.name);render();window.scrollTo({top:0,behavior:'smooth'});});};chooseGroup(create('neighborhood-chart',byNeighborhood.length?{grid:{top:14,right:26,bottom:20,left:22,containLabel:true},tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},xAxis:{type:'value',...axis},yAxis:{type:'category',data:byNeighborhood.map(x=>x.name).reverse(),axisLabel:{color:muted,fontSize:11,width:135,overflow:'truncate'},axisTick:{show:false},axisLine:{show:false}},series:[{type:'bar',data:byNeighborhood.map(x=>x.value).reverse(),barMaxWidth:18,itemStyle:{color:'#377fae',borderRadius:[0,6,6,0]},label:{show:true,position:'right',color:muted}}]}:{title:{text:'Aguardando bairros do CNES',left:'center',top:'middle',textStyle:{color:muted,fontSize:13,fontWeight:'normal'}}}));chooseGroup(create('type-chart',byType.length?{grid:{top:15,right:23,bottom:18,left:15,containLabel:true},tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},xAxis:{type:'value',...axis},yAxis:{type:'category',data:byType.map(x=>x.name).reverse(),axisLabel:{color:muted,fontSize:11,width:135,overflow:'truncate'},axisTick:{show:false},axisLine:{show:false}},series:[{type:'bar',data:byType.map(x=>x.value).reverse(),barMaxWidth:19,itemStyle:{color:'#119c8b',borderRadius:[0,6,6,0]},label:{show:true,position:'right',color:muted,fontSize:11}}]}:{title:{text:'Aguardando dados CNES',left:'center',top:'middle',textStyle:{color:muted,fontSize:13,fontWeight:'normal'}}}));let c:any;let activeSeries:keyof DataSummary['series']='population';const draw=(name:keyof DataSummary['series'])=>{activeSeries=name;const rows=state.summary!.series[name].filter(r=>state.year==='all'||String(r.year)===state.year);const names:{[k:string]:string}={population:'População (pessoas)',dengue:'Dengue (registros)',sih:'Produção hospitalar (SIH)',sia:'Produção ambulatorial (SIA)'};if(!c)c=create('time-chart',{});if(!c)return;c.clear();c.setOption(rows.length?{tooltip:{trigger:'axis'},grid:{top:25,bottom:25,left:18,right:18,containLabel:true},xAxis:{type:'category',data:rows.map(r=>r.year),...axis},yAxis:{type:'value',...axis},series:[{name:names[name],data:rows.map(r=>r.value),type:'line',smooth:true,symbolSize:8,lineStyle:{width:3,color:'#0c918e'},itemStyle:{color:'#0c918e'},areaStyle:{color:'rgba(13,152,142,.10)'}}]}:{title:{text:'Série ainda não disponibilizada',left:'center',top:'middle',textStyle:{color:muted,fontSize:13,fontWeight:'normal'}}});document.querySelector('#series-method')!.textContent=names[name]+' · Valores anuais de referência da fonte; ausência não implica zero.'};draw('population');document.querySelectorAll<HTMLButtonElement>('.series-btn').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.series-btn').forEach(x=>x.classList.remove('bg-teal-50','text-teal-800'));btn.classList.add('bg-teal-50','text-teal-800');draw(btn.dataset.series as keyof DataSummary['series'])});document.querySelector<HTMLSelectElement>('#year-filter')?.addEventListener('change',e=>{state.year=(e.target as HTMLSelectElement).value;draw(activeSeries)});const r=new ResizeObserver(()=>state.charts.forEach(x=>x.resize()));document.querySelectorAll('.chart').forEach(e=>r.observe(e));state.chartObserver=r}
async function initMap(id:string,compact:boolean){
 const target=document.getElementById(id);
 if(!target)return;
 const isCurrent=()=>target.isConnected && document.getElementById(id)===target;
 const showMapWarning=(text:string)=>{
  if(!isCurrent()||target.parentElement?.querySelector('.map-warning'))return;
  const div=document.createElement('p');div.className='map-warning text-xs text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-slate-800 p-3 rounded-xl mt-2';div.textContent=text;
  target.insertAdjacentElement('afterend',div);
 };
 let map:any;
 let switching=false;
 const useFallback=async (reason:unknown)=>{
  if(switching||!isCurrent())return;
  switching=true;
  console.warn('MapLibre indisponível, ativando Leaflet:',reason);
  if(map){try{map.remove()}catch(e){console.debug(e)}}
  state.map=null;
  try{
   const alternative=await leafletFallback(target,()=>state.page==='overview'?(state.geo?.features??[]):filtered(),isCurrent,showMapWarning,pickFacility);
   if(isCurrent())state.map=alternative;
   else alternative?.remove();
  }catch(error){
   console.error('Falha no mapa alternativo',error);
   showMapWarning('Mapa indisponível: não foi possível carregar as bibliotecas ou o serviço de mapas. Verifique a rede e o console do navegador.');
  }
 };
 try{
  const maplibregl=(await import('maplibre-gl')).default;
  if(!isCurrent())return;
  if(!document.createElement('canvas').getContext('webgl2'))throw new Error('WebGL 2 não é suportado neste navegador');
  map=new maplibregl.Map({
   container:target,
   // CartoCDN now watermarks unauthenticated tiles: use OpenFreeMap
   // Positron vector basemap, which does not require an API key.
   style:'https://tiles.openfreemap.org/styles/positron',
   center:[-51.182,-29.918],zoom:compact?10.8:11.3,attributionControl:false
  });
  state.map=map;
  map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right');
  map.addControl(new maplibregl.AttributionControl({compact:true}));
  let errors=0;
  map.on('error',(event:any)=>{
   console.warn('MapLibre:',event.error);
   if(++errors>=3)void useFallback(event.error);
  });
  map.on('load',()=>{
   if(state.map!==map||switching)return;
   try{
    map.addSource('facilities',{type:'geojson',data:{type:'FeatureCollection',features:[]},cluster:true,clusterMaxZoom:14,clusterRadius:45});
    map.addLayer({id:'clusters',type:'circle',source:'facilities',filter:['has','point_count'],paint:{'circle-color':['step',['get','point_count'],'#087e81',30,'#126b9e',90,'#244c82'],'circle-radius':['step',['get','point_count'],19,30,25,90,32],'circle-stroke-width':3,'circle-stroke-color':'#fff'}});
    map.addLayer({id:'count',type:'symbol',source:'facilities',filter:['has','point_count'],layout:{'text-field':['get','point_count_abbreviated'],'text-font':['Noto Sans Bold'],'text-size':12},paint:{'text-color':'#fff'}});
    map.addLayer({id:'points',type:'circle',source:'facilities',filter:['!',['has','point_count']],paint:{'circle-radius':7,'circle-color':['match',['get','category'],'ubs','#10a978','hospital','#2563eb','urgencia','#f59e0b','clinica','#8b5cf6','#64748b'],'circle-stroke-color':'white','circle-stroke-width':2}});
    map.addLayer({id:'selected-point',type:'circle',source:'facilities',filter:['all',['!',['has','point_count']],['==',['get','cnes'],selectedCnes()||'']],paint:{'circle-radius':13,'circle-color':'rgba(0,0,0,0)','circle-stroke-color':'#ef4444','circle-stroke-width':4}});
    map.on('click','points',(e:any)=>{
     const feature=e.features?.[0];if(!feature)return;
     const p=feature.properties!,coordinates=(feature.geometry as any).coordinates;
     if(state.page==='overview'){pickFacility(String(p.cnes));return}
     pickFacility(String(p.cnes));
     new maplibregl.Popup({maxWidth:'330px'}).setLngLat(coordinates).setHTML(facilityPopupHTML(String(p.cnes))).addTo(map);
    });
    map.on('click','clusters',(e:any)=>{
     const f=e.features?.[0];if(!f)return;
     const source=map.getSource('facilities') as any;
     source.getClusterExpansionZoom(f.properties?.cluster_id).then((zoom:number)=>map.easeTo({center:(f.geometry as any).coordinates,zoom})).catch(console.warn);
    });
    ['points','clusters'].forEach(l=>{map.on('mouseenter',l,()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave',l,()=>map.getCanvas().style.cursor='')});
    setMapPoints();
    if(selectedFacility()?.coordinates)focusSelectedOnMap();
   }catch(error){void useFallback(error)}
  });
 }catch(error){await useFallback(error)}
}

function setMapPoints(){const features=state.page==='overview'?(state.geo?.features??[]):filtered();const map=state.map;if(!map)return;if(typeof map.__refreshPoints==='function'){map.__refreshPoints();return}const source=map.getSource?.('facilities') as any;if(source)source.setData({type:'FeatureCollection',features})}
function focusSelectedOnMap(){
 const picked=selectedFacility();
 const map=state.map;
 if(!map||!picked?.coordinates)return;
 const [lon,lat]=picked.coordinates;
 if(typeof map.setFilter==='function'){
   try{map.setFilter('selected-point',['all',['!',['has','point_count']],['==',['get','cnes'],picked.cnes]])}catch{}
 }
 if(state.page!=='map'&&state.page!=='overview')return;
 try{
  if(typeof map.easeTo==='function')map.easeTo({center:[lon,lat],zoom:state.page==='overview'?13.4:15,duration:350});
  else if(typeof map.setView==='function')map.setView([lat,lon],15);
 }catch(error){console.warn('Não foi possível centralizar a unidade',error)}
}
function initFacilityInteractions(){
 app.addEventListener('click',e=>{
  const tile=(e.target as HTMLElement).closest<HTMLElement>('[data-facility-item]');
  if(tile){pickFacility(tile.dataset.facilityItem||'');document.getElementById('facility-explorer')?.scrollIntoView({behavior:'smooth',block:'start'});}
 });
 window.addEventListener('webgis:facility-selected',()=>{
  if(state.page==='overview'||state.page==='production'){render();return}
  if(state.page==='map')focusSelectedOnMap();
  document.querySelectorAll<HTMLElement>('[data-facility-item]').forEach(el=>{
    el.classList.toggle('ring-2',el.dataset.facilityItem===selectedCnes());
    el.classList.toggle('ring-teal-500',el.dataset.facilityItem===selectedCnes());
  });
 });
 window.addEventListener('webgis:facility-open-map',()=>{
  state.page='map';state.type='all';state.search='';render();
  window.scrollTo({top:0,behavior:'smooth'});
 });
}

async function boot(){const d=await getData();state.summary=d.summary;state.geo=d.geo;state.error=d.error;await loadFacilityCatalog(d.geo);initFacilityInteractions();render()}void boot();
