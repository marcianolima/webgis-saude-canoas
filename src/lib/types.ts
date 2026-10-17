export type SourceState = 'ok' | 'not_loaded' | 'error' | 'partial';
export interface SourceMeta { label:string; url:string; status:SourceState; retrievedAt:string|null; reference:string|null; records:number|null; note:string|null }
export interface DataSummary {
  generatedAt:string|null; municipality:{name:string;ibge:string;state:string;population:number|null;populationYear:number|null;censusPopulation:number|null;censusYear:number|null;areaKm2:number|null; density:number|null};
  facilities:{total:number|null;withCoordinates:number|null;ubs:number|null;hospitals:number|null;byType:{name:string;value:number}[];byNeighborhood:{name:string;value:number}[];asOf:string|null};
  beds:{total:number|null;sus:number|null;asOf:string|null};
  series:{population:{year:number;value:number}[];dengue:{year:number;value:number}[];sih:{year:number;value:number}[];sia:{year:number;value:number}[]};
  sourceInfo: Record<string,SourceMeta>;
}
export interface FacilityProps {cnes:string;name:string;type:string;category:'ubs'|'hospital'|'urgencia'|'clinica'|'outros';address:string;neighborhood:string;phone:string;hasBeds:boolean|null;sus:boolean|null; bedsTotal?:number|null;bedsSus?:number|null;bedsAsOf?:string|null }
export interface FacilityFeature {type:'Feature';id:string;geometry:{type:'Point';coordinates:[number,number]};properties:FacilityProps}
export interface FacilitiesGeoJSON {type:'FeatureCollection';features:FacilityFeature[]}
