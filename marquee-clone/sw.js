/* ===========================================================================
   Touchline service worker.
   The whole app is a static shell plus one 6 MB database, so it precaches
   everything on install and then runs fully offline. Bump CACHE when you
   regenerate players.json — old caches are dropped on activate.
   =========================================================================== */
const CACHE = "touchline-v3";

const SHELL = [
  "./",
  "app.html",
  "index.html",
  "style.css",
  "data.js",
  "engine.js",
  "app.js",
  "players.json",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/maskable-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // addAll is atomic — one bad URL loses the whole install, so add
    // individually and let the shell come up even if an extra asset is missing
    await Promise.all(SHELL.map(u => c.add(u).catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;   // fonts etc. — let them fail openly

  // players.json is big and immutable between builds: cache-first.
  // Everything else is stale-while-revalidate so updates land on next launch.
  e.respondWith((async () => {
    const cached = await caches.match(request, { ignoreSearch: true });
    if (cached && url.pathname.endsWith("players.json")) return cached;

    const network = fetch(request).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(request, copy)).catch(() => {});
      }
      return res;
    }).catch(() => null);

    if (cached) { network; return cached; }
    const res = await network;
    if (res) return res;
    // offline and never cached: fall back to the app shell for navigations
    if (request.mode === "navigate") {
      const shell = await caches.match("app.html");
      if (shell) return shell;
    }
    return new Response("Offline and not cached.", { status: 503 });
  })());
});
