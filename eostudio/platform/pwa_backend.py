"""
EoStudio PWA Backend — Progressive Web App display backend.

Phase 3: Cross-Platform Universal Support.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.platform.display_backend import (
    DisplayBackend,
    EventType,
    InputEvent,
    WindowConfig,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class PWAIcon:
    """A single icon entry for the PWA manifest."""

    src: str
    sizes: str  # e.g. "192x192"
    type: str = "image/png"
    purpose: str = "any maskable"

    def to_dict(self) -> dict:
        return {
            "src": self.src,
            "sizes": self.sizes,
            "type": self.type,
            "purpose": self.purpose,
        }


@dataclass
class PWAConfig:
    """Configuration for the Progressive Web App manifest and service worker."""

    app_name: str = "EoStudio"
    short_name: str = "EoStudio"
    theme_color: str = "#1a1a2e"
    background_color: str = "#0f0f1a"
    display: str = "standalone"  # fullscreen | standalone | minimal-ui | browser
    start_url: str = "/"
    scope: str = "/"
    orientation: str = "any"
    icons: List[PWAIcon] = field(default_factory=lambda: [
        PWAIcon(src="/icons/icon-192.png", sizes="192x192"),
        PWAIcon(src="/icons/icon-512.png", sizes="512x512"),
    ])
    categories: List[str] = field(default_factory=lambda: ["development", "productivity"])
    description: str = "EoStudio — the universal code editor"
    cache_name: str = "eostudio-v1"
    precache_urls: List[str] = field(default_factory=lambda: [
        "/",
        "/index.html",
        "/app.js",
        "/app.css",
    ])
    offline_fallback: str = "/offline.html"


# ---------------------------------------------------------------------------
# Manifest & Service Worker generators
# ---------------------------------------------------------------------------

def generate_manifest(config: Optional[PWAConfig] = None) -> dict:
    """Generate a W3C Web App Manifest dict from *config*."""
    cfg = config or PWAConfig()
    return {
        "name": cfg.app_name,
        "short_name": cfg.short_name,
        "start_url": cfg.start_url,
        "scope": cfg.scope,
        "display": cfg.display,
        "orientation": cfg.orientation,
        "theme_color": cfg.theme_color,
        "background_color": cfg.background_color,
        "description": cfg.description,
        "categories": cfg.categories,
        "icons": [icon.to_dict() for icon in cfg.icons],
    }


def generate_service_worker(config: Optional[PWAConfig] = None) -> str:
    """Generate a service-worker JavaScript source string."""
    cfg = config or PWAConfig()
    precache = json.dumps(cfg.precache_urls, indent=2)
    return f"""\
// EoStudio Service Worker — auto-generated
const CACHE_NAME = "{cfg.cache_name}";
const PRECACHE_URLS = {precache};

// Install: precache core assets
self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
}});

// Activate: clean old caches
self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
}});

// Fetch: cache-first, falling back to network, then offline page
self.addEventListener("fetch", (event) => {{
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cached) => {{
      if (cached) return cached;

      return fetch(event.request)
        .then((response) => {{
          if (!response || response.status !== 200 || response.type !== "basic") {{
            return response;
          }}
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        }})
        .catch(() => caches.match("{cfg.offline_fallback}"));
    }})
  );
}});
"""


def generate_registration_script() -> str:
    """Generate the JS snippet that registers the service worker."""
    return """\
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then((reg) => console.log("SW registered:", reg.scope))
      .catch((err) => console.error("SW registration failed:", err));
  });
}
"""


# ---------------------------------------------------------------------------
# PWABackend
# ---------------------------------------------------------------------------

class PWABackend(DisplayBackend):
    """Display backend that serves the UI as a Progressive Web App.

    In practice the Python process runs an HTTP server that delivers the
    PWA shell (manifest, service worker, HTML/JS/CSS).  The actual
    rendering happens in the user's browser.
    """

    def __init__(self, pwa_config: Optional[PWAConfig] = None) -> None:
        self._config = pwa_config or PWAConfig()
        self._running = False
        self._events: List[InputEvent] = []

    # -- DisplayBackend interface -------------------------------------------

    def initialize(self) -> bool:
        """Prepare the PWA assets (manifest, service worker)."""
        self._manifest = generate_manifest(self._config)
        self._sw_source = generate_service_worker(self._config)
        self._reg_script = generate_registration_script()
        self._running = True
        return True

    def create_window(self, config: WindowConfig) -> bool:
        """In PWA mode, 'creating a window' means starting the HTTP server."""
        # The HTTP server would be started here in a real implementation.
        return self._running

    def destroy_window(self) -> None:
        """Stop serving."""
        self._running = False

    def poll_events(self) -> List[InputEvent]:
        """Return and clear buffered input events received via WebSocket/SSE."""
        events = list(self._events)
        self._events.clear()
        return events

    def render(self, scene: Any) -> None:
        """Push a scene update to connected browser clients."""
        # In a real implementation this would broadcast via WebSocket.
        pass

    def shutdown(self) -> None:
        """Tear down the PWA backend."""
        self._running = False

    # -- PWA-specific API ---------------------------------------------------

    def get_manifest(self) -> dict:
        """Return the generated Web App Manifest."""
        return generate_manifest(self._config)

    def get_manifest_json(self) -> str:
        """Return the manifest as a JSON string."""
        return json.dumps(self.get_manifest(), indent=2)

    def get_service_worker(self) -> str:
        """Return the generated service-worker source."""
        return generate_service_worker(self._config)

    def get_registration_script(self) -> str:
        """Return the SW registration JS snippet."""
        return generate_registration_script()

    def inject_event(self, event: InputEvent) -> None:
        """Buffer an input event (called by the WebSocket handler)."""
        self._events.append(event)

    @property
    def is_running(self) -> bool:
        return self._running
