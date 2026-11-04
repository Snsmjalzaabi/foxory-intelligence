import React,{useEffect,useState} from 'react';
import {FolderSync} from 'lucide-react';
import {api} from './api';
type Status={enabled:boolean;workspace:string;files?:number;last_scan?:string|null;errors?:string[]};
export function WatchStatus(){
 const [s,setS]=useState<Status|null>(null);
 useEffect(()=>{api<Status>('/watch/status').then(setS).catch(()=>setS(null));},[]);
 if(!s)return null;
 return <div className="watch-status"><h3><FolderSync size={16}/> Watched folder</h3>
  {s.enabled?<p>{s.files??0} document(s) synced into the {s.workspace} workspace{s.last_scan?` · last checked ${new Date(s.last_scan).toLocaleTimeString()}`:' · first check runs within a minute'}. Changes in the folder appear here within a minute; the folder itself is never modified.</p>
   :<p className="muted">Off. Set <code>FOXORY_WATCH_DIR</code> to a folder path in your private <code>.env</code> and rebuild to sync its documents automatically (read-only).</p>}
  {s.errors&&s.errors.length>0&&<ul className="watch-errors">{s.errors.map(e=><li key={e}>{e}</li>)}</ul>}
 </div>;
}
