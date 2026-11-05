import {useSyncExternalStore} from 'react';
import {api} from './api';
// Installation profile (profiles/<name>.json on the server): names, regional defaults and starter prompts.
export type Starter={title:string;summary:string;icon:'plan'|'build'|'documents'|'draft';prompt:string;action?:'documents'|null};
export type Profile={machine_name:string;edition:string;welcome_title:string;system_prompt:string;timezone:string;currency:string;currencies:string[];starters:Starter[]};
const fallback:Profile={machine_name:'this computer',edition:'Local',welcome_title:'Welcome to your local AI workspace.',system_prompt:'You are FOXORY, a private local-first assistant. Be honest about uncertainty.',timezone:'UTC',currency:'USD',currencies:['USD'],starters:[]};
let current=fallback;const listeners=new Set<()=>void>();
export function loadProfile(){return api<Profile>('/profile').then(p=>{current=p;listeners.forEach(l=>l());return p;});}
export function useProfile(){return useSyncExternalStore(cb=>{listeners.add(cb);return()=>{listeners.delete(cb);};},()=>current);}
// "Local services" for a named machine, "Local services" for the generic default.
export const named=(p:Profile)=>p.machine_name==='this computer'?'Local':p.machine_name;
export const currencyOptions=(p:Profile,value?:string)=>value&&!p.currencies.includes(value)?[...p.currencies,value]:p.currencies;
