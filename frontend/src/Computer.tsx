import React,{useEffect,useRef,useState} from 'react';
import {api,download,artifactBlob,type Row,type Model} from './api';
type Profile='python'|'javascript'|'typescript'|'browser';
const profiles:Profile[]=['python','javascript','typescript','browser'];
const labels:Record<Profile,string>={python:'Python',javascript:'JavaScript',typescript:'TypeScript',browser:'Offline browser'};
function Screenshot({path,onError}:{path:string;onError:(error:unknown)=>void}){
 const [url,setUrl]=useState('');
 useEffect(()=>{let active=true,objectUrl='';artifactBlob(path).then(blob=>{
  if(!active)return;objectUrl=URL.createObjectURL(blob);setUrl(objectUrl);
 }).catch(e=>{if(active)onError(e);});return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl);};},[path]);
 return url?<img src={url} alt="Validated isolated browser screenshot" style={{maxWidth:'100%',height:'auto'}}/>:<p>Loading authorized screenshot…</p>;
}
export function Computer({models,selectedModel,onError,role}:{models:Model[];selectedModel:string;role:string;onError:(error:unknown)=>void}){
 const [cap,setCap]=useState<any>(null),[agents,setAgents]=useState<Row[]>([]),[jobs,setJobs]=useState<Row[]>([]),[approvals,setApprovals]=useState<Row[]>([]);
 const [profile,setProfile]=useState<Profile>('python'),[agent,setAgent]=useState(''),[objective,setObjective]=useState('Create a small Python application, run unittest tests, then package the matching source.');
 const [source,setSource]=useState(''),[entry,setEntry]=useState('test_app.py'),[actions,setActions]=useState('[{"action":"navigate","target":"/"},{"action":"inspect"},{"action":"screenshot"}]');
 const [selected,setSelected]=useState(''),[busy,setBusy]=useState(false),[live,setLive]=useState<any>(null),[creationModel,setCreationModel]=useState(selectedModel);
 const refreshing=useRef(false);
 useEffect(()=>{if(!creationModel&&models.length)setCreationModel(selectedModel||models[0].name);},[models,selectedModel]);
 const refresh=async()=>{if(refreshing.current)return;refreshing.current=true;try{const d=await api('/computer/overview');setAgents(d.agents);setJobs(d.jobs);setApprovals(d.approvals);}finally{refreshing.current=false;}};
 useEffect(()=>{api('/computer/capabilities').then(setCap).catch(onError);refresh().catch(onError);const timer=setInterval(()=>refresh().catch(onError),3000);return()=>clearInterval(timer);},[]);
 const job=jobs.find(j=>j.id===selected);
 useEffect(()=>{if(!job||!['queued','running','paused','cancelled'].includes(job.data.status)){setLive(null);return;}let active=true,polling=false;const poll=async()=>{
  if(polling)return;polling=true;try{const d=await api('/computer/jobs/'+job.id+'/execution');if(active)setLive(d);}catch(e){if(active)onError(e);}finally{polling=false;}
 };poll();const timer=setInterval(poll,3000);return()=>{active=false;clearInterval(timer);};},[job?.id,job?.data.status]);
 const act=async(action:()=>Promise<unknown>)=>{setBusy(true);try{await action();await refresh();}catch(e){onError(e);}finally{setBusy(false);}};
 const enabled=cap?.profiles?.[profile]?.enabled??(profile==='python'&&cap?.enabled);
 const blockers=cap?.profiles?.[profile]?.blockers??cap?.blockers??[];
 const pending=approvals.filter(a=>a.data.status==='pending'&&a.data.context.job_id===selected);
 const authorized=agents.filter(a=>a.data.config?.tools?.includes('sandbox.'+profile)||a.data.tools?.includes('sandbox.'+profile));
 const chooseProfile=(value:Profile)=>{setProfile(value);setAgent('');setEntry(value==='javascript'?'test_app.js':value==='typescript'?'test_app.ts':'test_app.py');};
 const retry=()=>{const previous=job?.data.computer_request;if(!previous)return;setProfile(previous.profile||'python');setAgent(previous.agent_id);setObjective(previous.objective);setSource(previous.source?JSON.stringify(previous.source.files,null,2):'');setEntry(previous.source?.entrypoint||'');setActions(JSON.stringify(previous.source?.actions||[],null,2));};
 return <div className="workforce">
  <section className="panel"><h2>Computer execution</h2>
   <p role="status">{profile==='python'&&enabled?'Python single-process sandbox available':enabled?labels[profile]+' isolated worker available':labels[profile]+' execution disabled'}</p>
   <label>Execution profile<select value={profile} onChange={e=>chooseProfile(e.target.value as Profile)}>{profiles.map(p=><option key={p} value={p}>{labels[p]}</option>)}</select></label>
   {blockers.map((b:string)=><p key={b}>{b}</p>)}
   <p>Execution requires a separately configured and verified manager. Each run and source package requires administrator approval. Generated output is untrusted.</p>
   <p>{profile==='python'?'Python has no network, subprocesses, threads or package installation.':profile==='browser'?'Browser actions run against supplied offline website files. External navigation, submissions and public browsing are blocked.':'Dependency-free Node execution only. No network or package installation. TypeScript uses type stripping, without semantic type checking.'}</p>
   {(cap?.profiles?.[profile]?.limits||(profile==='python'&&cap?.limits))&&<pre>{JSON.stringify(cap?.profiles?.[profile]?.limits||cap.limits,null,2)}</pre>}
   <button disabled={busy} onClick={()=>act(async()=>setCap(await api('/computer/capabilities')))}>Refresh availability</button>
   <label>Developer model<select value={creationModel} onChange={e=>setCreationModel(e.target.value)}><option value="">Choose a local model</option>{models.map(m=><option key={m.name}>{m.name}</option>)}</select></label>
   <button disabled={busy||!creationModel||role==='viewer'} onClick={()=>act(async()=>{
    const row=await api<Row>('/agents',{method:'POST',body:JSON.stringify({name:'Restricted '+labels[profile]+' developer',config:{role:profile==='browser'?'Browser Agent':'Coding Agent',purpose:'Perform approved isolated tasks. Inspect real tool failures before packaging; never claim success from model text.',model:creationModel,tools:profile==='browser'?['sandbox.browser']:['sandbox.'+profile,'source.package'],permissions:profile==='browser'?['sandbox.browser']:['sandbox.execute','documents.write'],max_steps:6,max_retries:0}})});setAgent(row.id);
   })}>Create restricted {labels[profile]} agent</button>
  </section>
  <form className="panel" onSubmit={e=>{e.preventDefault();act(async()=>{
   let supplied;if(source.trim())supplied={title:labels[profile]+' project',files:JSON.parse(source),...(profile==='browser'?{actions:JSON.parse(actions)}:{entrypoint:entry})};
   const row=await api<Row>('/computer/tasks',{method:'POST',body:JSON.stringify({agent_id:agent,objective,idempotency_key:crypto.randomUUID(),...(profile!=='python'?{profile}:{}),...(supplied?{source:supplied}:{})})});setSelected(row.id);
  });}}>
   <h2>Submit a task</h2>
   <label>Execution agent<select value={agent} required onChange={e=>setAgent(e.target.value)}><option value="">Choose an explicitly authorized agent</option>{(authorized.length?authorized:agents.filter(a=>a.id===agent)).map(a=><option value={a.id} key={a.id}>{a.title}</option>)}</select></label>
   <label>Computer task objective<textarea required value={objective} onChange={e=>setObjective(e.target.value)}/></label>
   <details><summary>Optional reviewed {labels[profile]} source</summary><p>Supply a JSON object mapping relative filenames to source text. Offline websites require index.html. Leave blank for model planning.</p>
    <label>Source files JSON<textarea value={source} onChange={e=>setSource(e.target.value)} placeholder={'{"test_app.py":"import unittest\n..."}'}/></label>
    {profile==='browser'?<label>Browser actions JSON<textarea value={actions} onChange={e=>setActions(e.target.value)}/></label>:<label>{labels[profile]} entrypoint<input value={entry} onChange={e=>setEntry(e.target.value)}/></label>}
   </details><button className="primary" disabled={busy||!agent||!enabled||role==='viewer'}>Plan task</button>
  </form>
  <div className="job-grid"><section>{jobs.map(j=><button className="job-item" key={j.id} onClick={()=>setSelected(j.id)}>{j.title} · {j.data.status}</button>)}</section>
   {job&&<article className="panel"><h2>{job.title}</h2><p role="status">{job.data.status} · {job.data.stage}</p>{job.data.error&&<p className="error">{job.data.error}</p>}
    <div className="panel-actions">{(['queued','running'].includes(job.data.status)?['pause','cancel']:job.data.status==='paused'?['resume','cancel']:job.data.status==='awaiting_approval'?['cancel']:[]).map(action=><button key={action} disabled={busy} onClick={()=>act(()=>api('/jobs/'+job.id+'/'+action,{method:'POST'}))}>{action} task</button>)}
     {['failed','cancelled'].includes(job.data.status)&&job.data.computer_request&&<button disabled={busy} onClick={retry}>Review and retry as a new task</button>}
     <button onClick={()=>download('/jobs/'+job.id+'/export','computer-report.md').catch(onError)}>Download execution report</button>
    </div><p>Pausing an active run cancels that invocation. Resume never silently reruns cancelled code. Retry creates a fresh task and requires new approvals.</p>
    <h3>Execution plan</h3><ol>{job.data.plan?.map((s:any,i:number)=><li key={i}>{s.title} · {s.tool||'Model analysis'}</li>)}</ol>
    <h3>Timeline</h3><ol>{job.data.timeline?.map((t:any,i:number)=><li key={i}>{t.at} · {t.event} {t.tool||''}</li>)}</ol>
    {live&&<section><h3>Live manager output · {live.status}</h3><pre className="document-preview">{live.stdout}{live.stderr}</pre></section>}
    {pending.map(a=><section className="notice" key={a.id}><h3>Approval required</h3><p>Expires {a.data.expires_at}. Review the exact source and actions. Generated code and website content may be malicious.</p><details><summary>Immutable execution context</summary><pre className="document-preview">{JSON.stringify(a.data.context,null,2)}</pre></details>{['approve','reject'].map(decision=><button key={decision} disabled={busy||role!=='admin'} onClick={()=>act(()=>api('/approvals/'+a.id+'/'+decision,{method:'POST'}))}>{decision} computer action</button>)}</section>)}
    {job.data.outputs?.map((o:any)=><section key={o.index}><h3>Step {o.index+1} · {o.tool||'Model analysis'} · {o.result.status||'recorded'}</h3>
     {o.tool?.startsWith('sandbox.')?<><p>Exit code {o.result.exit_code??'unavailable'} · {o.result.warning}</p><pre className="document-preview">{o.result.stdout}{o.result.stderr}{o.result.error}</pre>{Object.keys(o.result.artifacts||{}).map(name=>{
      const path='/computer/jobs/'+job.id+'/artifacts/'+o.index+'/'+name;
      return <div key={name}>{/^screenshot-[12]\.png$/.test(name)&&<Screenshot path={path} onError={onError}/>}<button onClick={()=>download(path,name).catch(onError)}>Download {name}</button></div>;
     })}</>:<pre className="document-preview">{JSON.stringify(o.result,null,2)}</pre>}
     {o.tool==='source.package'&&o.result.record_id&&<button onClick={()=>download('/artifacts/'+o.result.record_id+'/export?format=zip',(job.data.computer_request?.profile||'python')+'-project.zip').catch(onError)}>Download project ZIP</button>}
    </section>)}<p>{job.data.result}</p>
   </article>}
  </div>
 </div>;
}
