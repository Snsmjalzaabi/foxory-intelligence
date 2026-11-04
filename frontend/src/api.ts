export type Row = {id:string;kind:string;title:string;data:Record<string,any>;created_at:string;updated_at:string};
export type Model = {name:string;size:number;details?:{parameter_size?:string;quantization_level?:string};capabilities?:string[]|null;capability_status?:'reported'|'unknown';completion_supported?:boolean|null;embedding_supported?:boolean|null};
let csrf='';
let workspace=sessionStorage.getItem('foxory-workspace')||'';
export function setSessionScope(id:string,value:string){workspace=id;csrf=value;if(id)sessionStorage.setItem('foxory-workspace',id);else sessionStorage.removeItem('foxory-workspace');}
function authHeaders(){const h:Record<string,string>={};if(token)h.Authorization=`Bearer ${token}`;if(workspace)h['X-Workspace-ID']=workspace;if(csrf)h['X-CSRF-Token']=csrf;return h;}
let token = sessionStorage.getItem('foxory-token') || '';
export function setToken(value:string){token=value;if(value)sessionStorage.setItem('foxory-token',value);else sessionStorage.removeItem('foxory-token');}
function errorText(body:string){
 try{const detail=JSON.parse(body).detail;if(typeof detail==='string')return detail;if(Array.isArray(detail))return detail.map((d:any)=>d?.msg||JSON.stringify(d)).join('; ');}catch{/* plain response */}
 return body;
}
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const headers = new Headers(options.headers);Object.entries(authHeaders()).forEach(([k,v])=>headers.set(k,v));
 if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const r = await fetch('/api'+path,{...options,headers});
 if(!r.ok)throw new Error(`${r.status}: ${errorText(await r.text())}`);
 if(r.status===204)return undefined as T;
 return r.json();
}
export async function download(path:string,name:string){
 const r=await fetch('/api'+path,{headers:authHeaders()});if(!r.ok){let detail=await r.text();try{detail=JSON.parse(detail).detail||detail;}catch{}throw new Error(`${r.status}: ${typeof detail==='string'?detail.slice(0,1200):'Download failed'}`);}
 const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export async function stream(path:string,body:unknown,signal:AbortSignal,onEvent:(type:string,data:any)=>void){
 const r=await fetch('/api'+path,{method:'POST',headers:{...authHeaders(),'Content-Type':'application/json'},body:JSON.stringify(body),signal});
 if(!r.ok)throw new Error(errorText(await r.text()));
 const reader=r.body!.getReader();const decoder=new TextDecoder();let buffer='';
 while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let boundary;
 while((boundary=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const lines=block.split('\n');const type=lines.find(x=>x.startsWith('event: '))?.slice(7);const data=lines.filter(x=>x.startsWith('data: ')).map(x=>x.slice(6)).join('\n');if(type&&data)onEvent(type,JSON.parse(data));}}
}
export async function pullModel(model:string,onProgress:(line:string)=>void){
 const r=await fetch('/api/models/pull',{method:'POST',headers:{...authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({model,confirmation:model})});if(!r.ok)throw new Error(await r.text());
 const reader=r.body!.getReader(),decoder=new TextDecoder();let buffer='';while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let i;while((i=buffer.indexOf('\n'))>=0){const line=JSON.parse(buffer.slice(0,i));buffer=buffer.slice(i+1);if(line.error)throw new Error(line.error);onProgress(line.status+(line.total?` · ${Math.round((line.completed||0)/line.total*100)}%`:''));}}
}
const images=new Map<string,Promise<string>>();
export function imageDataUrl(id:string){
 if(!images.has(id))images.set(id,fetch('/api/images/'+encodeURIComponent(id),{headers:authHeaders()}).then(r=>{if(!r.ok)throw new Error('Image unavailable');return r.blob();}).then(blob=>new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=reject;reader.readAsDataURL(blob);})).catch(e=>{images.delete(id);throw e;}));
 return images.get(id)!;
}
export async function artifactBlob(path:string):Promise<Blob>{
 const response=await fetch('/api'+path,{headers:authHeaders()});
 if(!response.ok)throw new Error('Artifact preview authorization or validation failed');
 return response.blob();
}
