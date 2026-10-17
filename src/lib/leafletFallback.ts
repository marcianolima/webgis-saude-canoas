/** Mapa de contingência para navegadores sem WebGL ou com erro ao obter tiles/glyphs. */
import type {FacilityFeature} from './types';
import {facilityPopupHTML} from './facilityExplorer';

declare global { interface Window { L?: any } }

let scriptPromise: Promise<void>|null=null;
function appendCss(href:string){
 if(document.querySelector('link[data-webgis-leaflet]'))return;
 const el=document.createElement('link');el.rel='stylesheet';el.href=href;el.dataset.webgisLeaflet='true';document.head.appendChild(el);
}
function load(url:string):Promise<void>{return new Promise((resolve,reject)=>{
 const el=document.createElement('script');el.src=url;el.async=true;el.crossOrigin='anonymous';
 el.onload=()=>resolve();el.onerror=()=>reject(new Error('Falha ao carregar biblioteca de mapa alternativo'));
 document.head.appendChild(el);
});}
async function ensureLeaflet(){
 if(window.L)return;
 if(!scriptPromise)scriptPromise=(async()=>{
  appendCss('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css');
  try{await load('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js')}
  catch{await load('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js')}
 })().catch(err=>{scriptPromise=null;throw err});
 await scriptPromise;
 if(!window.L)throw new Error('Biblioteca Leaflet indisponível');
}
export async function leafletFallback(
 target:HTMLElement,
 points:()=>FacilityFeature[],
 isCurrent:()=>boolean,
 notice:(text:string)=>void,
 onSelect?:(cnes:string)=>unknown
):Promise<any>{
 await ensureLeaflet();
 if(!isCurrent())return null;
 const L=window.L!;
 target.replaceChildren();
 const map=L.map(target,{zoomControl:true,scrollWheelZoom:false,preferCanvas:true}).setView([-29.918,-51.182],11);
 const tiles=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  maxZoom:19,attribution:'© OpenStreetMap contributors'
 });
 let errors=0;
 tiles.on('tileerror',()=>{if(++errors===4)notice('Não foi possível baixar o mapa-base. Verifique acesso a tile.openstreetmap.org.')});
 tiles.addTo(map);
 const pointsLayer=L.layerGroup().addTo(map);
 const canvas=L.canvas({padding:0.5});
 const refresh=()=>{
  pointsLayer.clearLayers();
  for(const f of points()){
   const [lon,lat]=f.geometry.coordinates;
   const color=({ubs:'#10a978',hospital:'#2563eb',urgencia:'#f59e0b',clinica:'#8b5cf6',outros:'#64748b'} as Record<string,string>)[f.properties.category]||'#64748b';
   const p=f.properties;
   const popup=facilityPopupHTML(p.cnes);
   L.circleMarker([lat,lon],{radius:6,color:'#ffffff',weight:2,fillColor:color,fillOpacity:.9,renderer:canvas}).bindPopup(popup).on('click',()=>onSelect?.(p.cnes)).addTo(pointsLayer);
  }
 };
 (map as any).__refreshPoints=refresh;
 refresh();
 setTimeout(()=>{if(isCurrent())map.invalidateSize()},100);
 return map;
}
