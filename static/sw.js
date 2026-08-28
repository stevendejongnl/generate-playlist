const CACHE_NAME = "playlist-generator-shell-v1";

const SHELL_PATHS = ["/", "/base-list", "/blacklist", "/targets", "/generate", "/cover-image", "/skips", "/profile"];

function isCacheable(url) {
  if (url.origin !== self.location.origin) return false;
  if (SHELL_PATHS.includes(url.pathname)) return true;
  if (url.pathname.startsWith("/static/")) return true;
  return false;
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!isCacheable(url)) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request))
  );
});
