const CACHE='options-radar-shell-v1';
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','/manifest.webmanifest']))));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{if(event.request.method!=='GET'||new URL(event.request.url).pathname.startsWith('/api/'))return;event.respondWith(fetch(event.request).catch(()=>caches.match(event.request)));});
