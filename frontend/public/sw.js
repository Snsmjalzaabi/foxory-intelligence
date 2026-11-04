// FOXORY app-shell cache. API requests are never cached, so private data stays on the server.
const SHELL='foxory-shell-v1';
self.addEventListener('install',event=>{event.waitUntil(caches.open(SHELL).then(cache=>cache.addAll(['/','/manifest.webmanifest','/icons/icon-192.png'])));self.skipWaiting();});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==SHELL).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/'))return;
 // Pages: network first so updates appear immediately; the cached shell is only an offline fallback.
 if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(()=>caches.match('/')));return;}
 // Build assets have content-hashed names, so a cached copy is always the right one.
 if(url.pathname.startsWith('/assets/')||url.pathname.startsWith('/icons/')){
  event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(SHELL).then(c=>c.put(event.request,copy));}return response;})));
 }
});
