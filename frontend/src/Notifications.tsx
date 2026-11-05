import React,{useEffect,useRef,useState} from 'react';
import {Bell} from 'lucide-react';
import {api} from './api';
type Item={id:string;title:string;status:string;origin:string;at:string;summary:string};
const LABEL:Record<string,string>={completed:'Finished',failed:'Failed',awaiting_approval:'Needs approval',cancelled:'Cancelled'};
const read=(key:string)=>{try{return new Set<string>(JSON.parse(localStorage.getItem(key)||'[]'));}catch{return new Set<string>();}};
const desktopSupported=typeof window!=='undefined'&&'Notification' in window;

export function Notifications({scope,onOpen}:{scope:string;onOpen:(id:string)=>void}){
 const key='foxory-notifications-seen:'+scope;
 const [items,setItems]=useState<Item[]>([]),[seen,setSeen]=useState(()=>read(key)),[open,setOpen]=useState(false);
 const [desktop,setDesktop]=useState(desktopSupported&&Notification.permission==='granted');
 const known=useRef<Set<string>|null>(null);
 useEffect(()=>{setSeen(read(key));known.current=null;},[key]);
 useEffect(()=>{
  let active=true;
  const poll=()=>api<{items:Item[]}>('/notifications').then(d=>{
   if(!active)return;setItems(d.items);
   // Desktop notifications only for items that arrive while the app is open, not the backlog.
   if(known.current&&desktop)d.items.filter(i=>!known.current!.has(i.id)).forEach(i=>new Notification('FOXORY: '+(LABEL[i.status]||i.status),{body:i.title,tag:i.id}));
   known.current=new Set(d.items.map(i=>i.id));
  }).catch(()=>{});
  poll();const timer=setInterval(poll,30000);return()=>{active=false;clearInterval(timer);};
 },[key,desktop]);
 const unread=items.filter(i=>!seen.has(i.id)).length;
 const markAll=()=>{const next=new Set([...seen,...items.map(i=>i.id)]);setSeen(next);try{localStorage.setItem(key,JSON.stringify([...next].slice(-200)));}catch{/* per-browser convenience only */}};
 const enableDesktop=async()=>{if(desktopSupported)setDesktop(await Notification.requestPermission()==='granted');};
 return <div className="notifications">
  <button aria-label={unread?`Notifications, ${unread} unread`:'Notifications'} aria-expanded={open} onClick={()=>{setOpen(!open);if(!open)markAll();}}><Bell size={17}/>{unread>0&&<span className="notification-count">{unread}</span>}</button>
  {open&&<div className="notification-panel" role="dialog" aria-label="Notifications">
   <div className="panel-actions"><strong>Task updates</strong>{desktopSupported&&!desktop&&<button onClick={enableDesktop}>Enable desktop notifications</button>}</div>
   {items.length?<ul>{items.map(i=><li key={i.id}><button onClick={()=>{setOpen(false);onOpen(i.id);}}><span className={'notification-status '+i.status}>{LABEL[i.status]||i.status}</span> {i.title}<small>{i.origin==='task'?'':i.origin==='schedule'?'Scheduled · ':'Automation · '}{new Date(i.at).toLocaleString()}</small>{i.summary&&<small>{i.summary}</small>}</button></li>)}</ul>:<p className="muted">No task updates in the last seven days.</p>}
  </div>}
 </div>;
}
