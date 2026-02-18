const CACHE_NAME = 'taxco-cache-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

// Sincronización en segundo plano (cuando la conexión vuelva)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-diagnosticos') {
    event.waitUntil(sincronizarDiagnosticos());
  }
});

async function sincronizarDiagnosticos() {
  const pendientes = JSON.parse(localStorage.getItem('diagnosticos_pendientes')) || [];
  if (pendientes.length === 0) return;

  for (let diag of pendientes) {
    try {
      const response = await fetch('https://tusitio.com/api/recoleccion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(diag)
      });
      if (response.ok) {
        // Eliminar de pendientes
        const nuevos = pendientes.filter(d => d !== diag);
        localStorage.setItem('diagnosticos_pendientes', JSON.stringify(nuevos));
      }
    } catch (error) {
      console.error('Error en sincronización:', error);
    }
  }
}