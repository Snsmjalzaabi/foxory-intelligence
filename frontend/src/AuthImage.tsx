import React,{useEffect,useState} from 'react';
import {imageDataUrl} from './api';
// Loads an uploaded image with the current workspace's credentials (a plain <img src> would not send them).
export function AuthImage({id,alt,className}:{id:string;alt:string;className?:string}){
 const [src,setSrc]=useState('');
 useEffect(()=>{let active=true;imageDataUrl(id).then(url=>{if(active)setSrc(url);}).catch(()=>{});return()=>{active=false;};},[id]);
 return src?<img className={className} src={src} alt={alt}/>:<span className={className} role="img" aria-label={alt}/>;
}
