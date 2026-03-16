const CACHE_NAME = "madleaf-cache-v1";  // Aggiungi versione alla cache per gestione futura

const urlsToCache = [
  "/",
  "/bericht",
  "/kunden",
  "/berichte",
  "/static/logo.png",
  "/static/manifest.json",
  "/static/service_worker.js"
];

// Evento di installazione del service worker
self.addEventListener("install", function(event){
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache){
        console.log("Cache aperta e files aggiunti");
        return cache.addAll(urlsToCache);  // Aggiungi tutti i file necessari alla cache
      })
  );
});

// Evento di fetch per gestire la cache
self.addEventListener("fetch", function(event){
  event.respondWith(
    caches.match(event.request)
      .then(function(response){
        // Se la risposta è nella cache, restituiscila
        if (response) {
          return response;
        }
        // Altrimenti fai la richiesta al server
        return fetch(event.request);
      })
  );
});

// Evento di attivazione del service worker (opzionale per aggiornare la cache)
self.addEventListener("activate", function(event) {
  const cacheWhitelist = [CACHE_NAME];

  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
