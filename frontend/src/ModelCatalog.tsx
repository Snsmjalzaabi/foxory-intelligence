import React,{useEffect,useState} from 'react';
import {Download,Check,Trash2} from 'lucide-react';
import {api} from './api';
type Recommended={name:string;family:string;strengths:string[];download_bytes:number;context_length:number;memory_bytes:number;fits:boolean|null;license:string;license_url:string;open_license:boolean;summary:string;installed:boolean;starter:boolean};
type Catalog={available:boolean;memory_budget_bytes:number|null;models:Recommended[];note:string};
const gb=(bytes:number)=>(bytes/1e9).toFixed(bytes<1e9?2:1)+' GB';
const context=(tokens:number)=>tokens>=1024?Math.round(tokens/1024)+'K':String(tokens);
export function ModelCatalog({installedKey,canInstall,busy,onInstall,onUninstall,onError}:{installedKey:string;canInstall:boolean;busy:boolean;onInstall:(name:string)=>void;onUninstall:(name:string)=>void;onError:(error:unknown)=>void}){
 const [data,setData]=useState<Catalog|null>(null),[filter,setFilter]=useState<'starter'|'all'>('starter');
 useEffect(()=>{api<Catalog>('/models/recommended').then(setData).catch(onError);},[installedKey]);
 if(!data)return <p>Loading recommended models…</p>;
 const shown=data.models.filter(m=>filter==='all'||m.starter);
 return <div className="model-catalog">
  <div className="panel-actions"><h3>Recommended local models</h3><div role="group" aria-label="Recommended model filter"><button aria-pressed={filter==='starter'} onClick={()=>setFilter('starter')}>Starter set for this PC</button><button aria-pressed={filter==='all'} onClick={()=>setFilter('all')}>All {data.models.length}</button></div></div>
  <p className="muted">{data.memory_budget_bytes?`About ${gb(data.memory_budget_bytes)} of model memory available on this PC.`:'Hardware not measured yet, so the starter set uses the smallest models. Connect the local controller for a fit check.'} Small, free models that run fully on this computer.</p>
  {!data.available&&<p role="alert">Ollama is not reachable, so installed models cannot be shown.</p>}
  <ul className="model-catalog-list">{shown.map(m=><li key={m.name}>
   <div><strong>{m.name}</strong> <small>{m.family} · {m.strengths.join(', ')}</small><p>{m.summary}</p>
    <small>{gb(m.download_bytes)} download · ~{gb(m.memory_bytes)} memory · {context(m.context_length)} context · <a href={m.license_url} target="_blank" rel="noreferrer noopener">{m.license}</a>{m.open_license?'':' (custom terms)'}{m.fits===false?' · may not fit this PC':''}</small></div>
   {m.installed?<span className="model-installed"><Check size={15}/>Installed{canInstall&&<button disabled={busy} aria-label={'Uninstall '+m.name} onClick={()=>onUninstall(m.name)}><Trash2 size={15}/>Uninstall</button>}</span>:canInstall&&<button disabled={busy} aria-label={'Download '+m.name} onClick={()=>onInstall(m.name)}><Download size={15}/>Download</button>}
  </li>)}</ul>
  <p className="muted"><small>{data.note}</small></p>
 </div>;
}
