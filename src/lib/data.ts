import type {DataSummary,FacilitiesGeoJSON} from './types';
import {urlAsset} from './utils';

const emptySummary: DataSummary = {
 generatedAt:null,
 municipality:{name:'Canoas',ibge:'4304606',state:'RS',population:null,populationYear:null,censusPopulation:null,censusYear:null,areaKm2:null,density:null},
 facilities:{total:null,withCoordinates:null,ubs:null,hospitals:null,byType:[],byNeighborhood:[],asOf:null},
 beds:{total:null,sus:null,asOf:null},
 series:{population:[],dengue:[],sih:[],sia:[]},sourceInfo:{}
};
const emptyGeo:FacilitiesGeoJSON={type:'FeatureCollection',features:[]};
const isRecord=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);

function validSummary(x:unknown):x is DataSummary {
 if(!isRecord(x)||!isRecord(x.municipality)||!isRecord(x.facilities)||!isRecord(x.beds)||!isRecord(x.series)||!isRecord(x.sourceInfo))return false;
 const municipality=x.municipality, facilities=x.facilities, series=x.series;
 if(municipality.ibge!=='4304606'||!Array.isArray(facilities.byType)||!Array.isArray(facilities.byNeighborhood))return false;
 return ['population','dengue','sih','sia'].every(key=>Array.isArray(series[key]));
}
function validGeo(x:unknown):x is FacilitiesGeoJSON{
 if(!isRecord(x)||x.type!=='FeatureCollection'||!Array.isArray(x.features))return false;
 return x.features.every((f:unknown)=>isRecord(f)&&f.type==='Feature'&&isRecord(f.geometry)&&f.geometry.type==='Point'&&Array.isArray(f.geometry.coordinates)&&f.geometry.coordinates.length===2&&f.geometry.coordinates.every((v:unknown)=>typeof v==='number'&&Number.isFinite(v))&&isRecord(f.properties));
}
export async function getData():Promise<{summary:DataSummary;geo:FacilitiesGeoJSON;error:string|null}>{
 const [a,b]=await Promise.allSettled([
  fetch(urlAsset('data/summary.json'),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json() as Promise<unknown>}),
  fetch(urlAsset('data/establishments.geojson'),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json() as Promise<unknown>})
 ]);
 const summary=a.status==='fulfilled'&&validSummary(a.value)?a.value:emptySummary;
 const geo=b.status==='fulfilled'&&validGeo(b.value)?b.value:emptyGeo;
 const errors:string[]=[];
 if(summary===emptySummary)errors.push('Não foi possível carregar/validar os indicadores. Verifique public/data/summary.json e o deploy.');
 if(geo===emptyGeo)errors.push('Estabelecimentos sem dados geográficos válidos. O mapa permanece disponível para navegação.');
 return {summary,geo,error:errors.length?errors.join(' '):null};
}
