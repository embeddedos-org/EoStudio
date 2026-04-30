"""Extension manager for EoStudio — install, activate, and manage extensions."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EOSTUDIO_DIR = Path.home() / ".eostudio"
_EXTENSIONS_DIR = _EOSTUDIO_DIR / "extensions"
_REGISTRY_CACHE_FILE = _EOSTUDIO_DIR / "registry_cache.json"
_DEFAULT_REGISTRY_URL = "https://marketplace.eostudio.dev/api/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def semver_compare(v1: str, v2: str) -> int:
    """Compare two semver strings.  Returns -1, 0, or 1.

    Handles ``major.minor.patch`` and tolerates missing segments
    (e.g. ``"1.2"`` is treated as ``"1.2.0"``).
    """

    def _parts(v: str) -> List[int]:
        segments = v.lstrip("vV").split(".")
        out: List[int] = []
        for s in segments[:3]:
            # Strip pre-release suffix for comparison purposes.
            numeric = ""
            for ch in s:
                if ch.isdigit():
                    numeric += ch
                else:
                    break
            out.append(int(numeric) if numeric else 0)
        while len(out) < 3:
            out.append(0)
        return out

    p1, p2 = _parts(v1), _parts(v2)
    for a, b in zip(p1, p2):
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class ExtensionState(str, Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ExtensionManifest:
    """Metadata describing an extension package."""

    id: str = ""
    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    activation_events: List[str] = field(default_factory=list)
    contributes: Dict[str, Any] = field(default_factory=dict)
    min_eostudio_version: str = "0.0.0"
    repository: str = ""


@dataclass
class Extension:
    """Runtime representation of a managed extension."""

    manifest: ExtensionManifest = field(default_factory=ExtensionManifest)
    state: str = ExtensionState.INSTALLED.value
    path: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Extension Registry (marketplace client)
# ---------------------------------------------------------------------------

class ExtensionRegistry:
    """HTTP client for the extension marketplace."""

    def __init__(self, registry_url: str = _DEFAULT_REGISTRY_URL) -> None:
        self._registry_url = registry_url.rstrip("/")

    # -- public API ----------------------------------------------------------

    def search(self, query: str) -> List[ExtensionManifest]:
        """Search the marketplace for extensions matching *query*."""
        data = self._api_get(f"/search?q={query}")
        if not isinstance(data, list):
            return []
        return [self._manifest_from_dict(item) for item in data]

    def get_manifest(self, ext_id: str, version: str | None = None) -> Optional[ExtensionManifest]:
        """Fetch the manifest for a specific extension."""
        url = f"/extensions/{ext_id}"
        if version:
            url += f"/{version}"
        data = self._api_get(url)
        if not data:
            return None
        return self._manifest_from_dict(data)

    def get_latest_version(self, ext_id: str) -> Optional[str]:
        """Return the latest published version string."""
        manifest = self.get_manifest(ext_id)
        return manifest.version if manifest else None

    def download(self, ext_id: str, version: str, dest_dir: Path) -> bool:
        """Download and extract an extension package into *dest_dir*."""
        url = f"{self._registry_url}/extensions/{ext_id}/{version}/download"
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=30) as resp:
                dest_dir.mkdir(parents=True, exist_ok=True)
                pkg_path = dest_dir / "package.json"
                pkg_path.write_bytes(resp.read())
            return True
        except Exception:
            return False

    # -- internals -----------------------------------------------------------

    def _api_get(self, path: str) -> Any:
        url = f"{self._registry_url}{path}"
        try:
            req = Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _manifest_from_dict(d: dict) -> ExtensionManifest:
        known_fields = {f for f in ExtensionManifest.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return ExtensionManifest(**filtered)


# ---------------------------------------------------------------------------
# Extension Manager
# ---------------------------------------------------------------------------

class ExtensionManager:
    """Manage the full lifecycle of EoStudio extensions.

    Backward-compatible with the original stub API:
        ``__init__(), install(name), uninstall(name), list_installed()``
    """

    def __init__(self, *, registry_url: str = _DEFAULT_REGISTRY_URL) -> None:
        self._extensions: Dict[str, Extension] = {}
        self._registry = ExtensionRegistry(registry_url)
        self._extensions_dir = _EXTENSIONS_DIR
        self._extensions_dir.mkdir(parents=True, exist_ok=True)
        self._load_installed()

    # -- backward compat (original stub API) ---------------------------------

    def install(self, name: str, version: str | None = None) -> bool:
        """Install an extension by *name*.

        If the extension is already installed at the requested (or latest)
        version the call is a no-op and returns *True*.
        """
        if name in self._extensions and version is None:
            return True

        manifest = self._registry.get_manifest(name, version)
        if manifest is None:
            # Offline / registry unavailable — create a minimal local entry so
            # callers that do not depend on marketplace still work.
            manifest = ExtensionManifest(id=name, name=name, version=version or "0.0.0")

        # Resolve and install dependencies first.
        for dep in self.resolve_dependencies(manifest):
            if dep not in self._extensions:
                self.install(dep)

        target = version or manifest.version
        ext_dir = self._extensions_dir / name / target
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Write the manifest locally.
        manifest_path = ext_dir / "manifest.json"
        manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")

        # Attempt download (tolerate failure for offline-first).
        self._registry.download(name, target, ext_dir)

        ext = Extension(
            manifest=manifest,
            state=ExtensionState.INSTALLED.value,
            path=str(ext_dir),
        )
        self._extensions[name] = ext
        self._persist_state()
        return True

    def uninstall(self, name: str) -> bool:
        """Remove an extension.  Returns *True* if it was present."""
        ext = self._extensions.pop(name, None)
        if ext is None:
            return False
        ext_root = self._extensions_dir / name
        if ext_root.exists():
            shutil.rmtree(ext_root, ignore_errors=True)
        self._persist_state()
        return True

    def list_installed(self) -> List[str]:
        """Return the names of all installed extensions (backward compat)."""
        return list(self._extensions.keys())

    # -- extended API --------------------------------------------------------

    def get_installed(self) -> List[Extension]:
        """Return full :class:`Extension` objects for every installed extension."""
        return list(self._extensions.values())

    def get_extension(self, name: str) -> Extension:
        """Get an installed extension by name.  Raises ``KeyError`` if missing."""
        return self._extensions[name]

    def enable(self, name: str) -> None:
        """Mark an installed extension as active (will load on next activation)."""
        ext = self._extensions[name]
        ext.state = ExtensionState.INSTALLED.value
        self._persist_state()

    def disable(self, name: str) -> None:
        """Disable an installed extension."""
        ext = self._extensions[name]
        ext.state = ExtensionState.DISABLED.value
        self._persist_state()

    def activate(self, name: str) -> None:
        """Activate an extension (execute its entry point)."""
        ext = self._extensions[name]
        if ext.state == ExtensionState.DISABLED.value:
            raise RuntimeError(f"Extension '{name}' is disabled; enable it first")
        try:
            entry = ext.manifest.entry_point
            if entry:
                ext_path = Path(ext.path)
                module_file = ext_path / entry
                if module_file.exists():
                    # Load via importlib to avoid polluting sys.modules naming.
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(
                        f"eostudio.ext.{name}", str(module_file)
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)  # type: ignore[union-attr]
            ext.state = ExtensionState.ACTIVE.value
        except Exception:
            ext.state = ExtensionState.ERROR.value
        self._persist_state()

    def deactivate(self, name: str) -> None:
        """Deactivate a running extension."""
        ext = self._extensions[name]
        ext.state = ExtensionState.INSTALLED.value
        self._persist_state()

    def search(self, query: str) -> List[ExtensionManifest]:
        """Search the marketplace for extensions."""
        return self._registry.search(query)

    def update(self, name: str | None = None) -> List[str]:
        """Update one or all extensions.  Returns names that were updated."""
        targets = [name] if name else list(self._extensions.keys())
        updated: List[str] = []
        for ext_name in targets:
            if ext_name not in self._extensions:
                continue
            ext = self._extensions[ext_name]
            latest = self._registry.get_latest_version(ext_name)
            if latest and semver_compare(latest, ext.manifest.version) > 0:
                self.install(ext_name, latest)
                updated.append(ext_name)
        return updated

    def resolve_dependencies(self, manifest: ExtensionManifest) -> List[str]:
        """Return a flat, ordered list of dependency extension IDs."""
        resolved: List[str] = []
        seen: set[str] = set()

        def _walk(deps: List[str]) -> None:
            for dep in deps:
                if dep in seen:
                    continue
                seen.add(dep)
                dep_manifest = self._registry.get_manifest(dep)
                if dep_manifest:
                    _walk(dep_manifest.dependencies)
                resolved.append(dep)

        _walk(manifest.dependencies)
        return resolved

    # -- persistence ---------------------------------------------------------

    def _state_file(self) -> Path:
        return _EOSTUDIO_DIR / "extensions_state.json"

    def _persist_state(self) -> None:
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        for name, ext in self._extensions.items():
            data[name] = {
                "manifest": asdict(ext.manifest),
                "state": ext.state,
                "path": ext.path,
                "config": ext.config,
            }
        self._state_file().write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_installed(self) -> None:
        sf = self._state_file()
        if not sf.exists():
            return
        try:
            raw = json.loads(sf.read_text(encoding="utf-8"))
            for name, blob in raw.items():
                manifest_data = blob.get("manifest", {})
                known = {f for f in ExtensionManifest.__dataclass_fields__}
                manifest = ExtensionManifest(**{k: v for k, v in manifest_data.items() if k in known})
                self._extensions[name] = Extension(
                    manifest=manifest,
                    state=blob.get("state", ExtensionState.INSTALLED.value),
                    path=blob.get("path", ""),
                    config=blob.get("config", {}),
                )
        except Exception:
            pass
