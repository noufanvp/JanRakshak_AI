/**
 * JanRakshak AI — Service Worker
 * Strategy: Cache-First for static assets, Network-First for API/dynamic routes.
 * Provides offline capability and "Add to Homescreen" installability.
 */

const SW_VERSION = "janrakshak-v1.0.0";

// ---------------------------------------------------------------------------
// Cache configuration
// ---------------------------------------------------------------------------
const STATIC_CACHE = `${SW_VERSION}-static`;
const DYNAMIC_CACHE = `${SW_VERSION}-dynamic`;

/** Assets to pre-cache on install (app shell) */
const APP_SHELL = [
  "/",
  "/report/",
  "/reports/",
  "/emergency/",
  "/static/css/custom.css",
  "/static/js/app.js",
  "/static/js/report.js",
  "/static/js/dashboard.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/pwa/offline/",  // Offline fallback page
];

/** URL patterns that should always go to the network */
const NETWORK_ONLY_PATTERNS = [
  /\/api\//,          // All API endpoints (report submission, assistant)
  /\/admin\//,        // Django admin
];

// ---------------------------------------------------------------------------
// Install: pre-cache the app shell
// ---------------------------------------------------------------------------
self.addEventListener("install", (event) => {
  console.log(`[SW] Installing ${SW_VERSION}`);
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => {
        console.log("[SW] Pre-caching app shell");
        // Use individual adds so one failure doesn't block everything
        return Promise.allSettled(APP_SHELL.map((url) => cache.add(url)));
      })
      .then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate: purge old cache versions
// ---------------------------------------------------------------------------
self.addEventListener("activate", (event) => {
  console.log(`[SW] Activating ${SW_VERSION}`);
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map((key) => {
            console.log(`[SW] Deleting old cache: ${key}`);
            return caches.delete(key);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch: routing strategy
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only intercept same-origin GET requests
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return; // Pass through non-GET and cross-origin requests unchanged
  }

  // Network-only for API routes (always fresh data)
  const isNetworkOnly = NETWORK_ONLY_PATTERNS.some((pattern) =>
    pattern.test(url.pathname)
  );
  if (isNetworkOnly) {
    event.respondWith(fetch(request));
    return;
  }

  // Cache-First for static assets
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Network-First with dynamic cache fallback for HTML pages
  event.respondWith(networkFirstWithFallback(request));
});

// ---------------------------------------------------------------------------
// Strategy helpers
// ---------------------------------------------------------------------------

/**
 * Cache-First: serve from cache, update cache in background.
 */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    // No cache hit and no network — return empty 504
    return new Response("Resource unavailable offline", { status: 504 });
  }
}

/**
 * Network-First: try network, fall back to cache, then offline page.
 */
async function networkFirstWithFallback(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;

    // Final fallback: serve the offline page
    const offlinePage = await caches.match("/pwa/offline/");
    return (
      offlinePage ||
      new Response(
        "<h1>You are offline</h1><p>Please check your connection and try again.</p>",
        { headers: { "Content-Type": "text/html" } }
      )
    );
  }
}

// ---------------------------------------------------------------------------
// Background Sync: queue offline reports for resubmission when back online
// ---------------------------------------------------------------------------
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-offline-reports") {
    console.log("[SW] Background sync: processing queued reports");
    event.waitUntil(syncOfflineReports());
  }
});

async function syncOfflineReports() {
  // Retrieve queued reports from IndexedDB (populated by report.js)
  // This is a stub — full IndexedDB integration should be added in report.js
  console.log("[SW] Offline report sync complete (stub)");
}
