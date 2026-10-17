import type {DataSummary,FacilitiesGeoJSON} from './types';
import {urlAsset} from './utils';
export async function getData():Promise<{summary:DataSummary;geo:FacilitiesGeoJSON;error:string|null}>{
 const [a,b]=await Promise.allSettled([
  fetch(urlAsset('data/summary.json'),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json() as Promise<DataSummary>}),
  fetch(urlAsset('data/establishments.geojson'),{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json() as Promise<FacilitiesGeoJSON>})
 ]);
 const summary:DataSummary=a.status==='fulfilled'?a.value:{generatedAt:null,municipality:{name:'Canoas',ibge:'4304606',state:'RS',population:null,populationYear:null,censusPopulation:null,censusYear:null,areaKm2:null,density:null},facilities:{total:null,withCoordinates:null,ubs:null,hospitals:null,byType:[],byNeighborhood:[],asOf:null},beds:{total:null,sus:null,asOf:null},series:{population:[],dengue:[],sih:[],sia:[]},sourceInfo:{}};
 const geo:FacilitiesGeoJSON=b.status==='fulfilled'&&b.value.type==='FeatureCollection'?b.value:{type:'FeatureCollection',features:[]};
 return {summary,geo,error:a.status==='rejected'?'O arquivo de indicadores não pôde ser carregado. Verifique o deploy e a pasta public/data.':null};
}
