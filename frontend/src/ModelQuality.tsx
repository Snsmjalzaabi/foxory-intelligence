import React,{useEffect,useState} from 'react';
import {Gauge} from 'lucide-react';
import {api} from './api';
type Result={categories:Record<string,number>;passed:number;total:number;seconds:number;measured_at:string};
type Data={results:Record<string,Result>;status:{running:boolean;model:string|null;done:number;total:number;error:string|null};cases:number};
const CATEGORIES=['chat','reasoning','coding','writing'];
export function ModelQuality({canRun,onError}:{canRun:boolean;onError:(error:unknown)=>void}){
 const [data,setData]=useState<Data|null>(null);
 const load=()=>api<Data>('/models/quality').then(setData).catch(onError);
 useEffect(()=>{load();},[]);
 useEffect(()=>{if(!data?.status.running)return;const t=setInterval(load,3000);return()=>clearInterval(t);},[data?.status.running]);
 if(!data)return null;
 const rows=Object.entries(data.results).sort((a,b)=>b[1].passed-a[1].passed);
 const start=()=>api('/models/quality',{method:'POST'}).then(load).catch(onError);
 return <div className="model-quality"><div className="panel-actions"><h3><Gauge size={16}/> Model quality on this PC</h3>{canRun&&<button disabled={data.status.running} onClick={start}>{data.status.running?`Checking ${data.status.model||''} (${data.status.done}/${data.status.total})`:'Check installed models'}</button>}</div>
  <p className="muted">{data.cases} short questions with checkable answers (chat, reasoning, coding, writing). Auto mode prefers models that score well for each kind of request. Takes about a minute per model.</p>
  {data.status.error&&<p role="alert">The last check stopped early ({data.status.error}).</p>}
  {rows.length>0&&<div className="table-scroll"><table><thead><tr><th>Model</th>{CATEGORIES.map(c=><th key={c}>{c}</th>)}<th>Score</th><th>Time</th></tr></thead>
   <tbody>{rows.map(([name,r])=><tr key={name}><td>{name}</td>{CATEGORIES.map(c=><td key={c}>{c in r.categories?Math.round(r.categories[c]*100)+'%':'–'}</td>)}<td>{r.passed}/{r.total}</td><td>{r.seconds}s</td></tr>)}</tbody></table></div>}
 </div>;
}
