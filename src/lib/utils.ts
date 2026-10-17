export const nf=(n:number|null|undefined)=>typeof n==='number'&&Number.isFinite(n)?new Intl.NumberFormat('pt-BR').format(n):'—';
export const dec=(n:number|null|undefined,d=1)=>typeof n==='number'&&Number.isFinite(n)?new Intl.NumberFormat('pt-BR',{maximumFractionDigits:d}).format(n):'—';
export const safe=(s:unknown)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]??c));
export const fmtDate=(s:string|null|undefined)=>s?new Date(s).toLocaleDateString('pt-BR',{timeZone:'UTC'}):'Não informado';
export const urlAsset=(path:string)=>new URL(path,document.baseURI).toString();
export function dlCsv(rows:Record<string,string|number|null>[],name:string){if(!rows.length)return;const keys=Object.keys(rows[0]);const cell=(x:unknown)=>'"'+String(x??'').replace(/"/g,'""')+'"';const csv='\ufeff'+keys.join(';')+'\n'+rows.map(r=>keys.map(k=>cell(r[k])).join(';')).join('\n');const href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=href;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(href),3000)}
