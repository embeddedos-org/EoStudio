"""Cloud sync for EoStudio — settings sync, workspace state, and secure storage."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_EOSTUDIO_DIR = Path.home() / ".eostudio"
_WORKSPACE_STATE_FILE = _EOSTUDIO_DIR / "workspace_state.json"
_SECURE_STORAGE_FILE = _EOSTUDIO_DIR / "credentials.enc.json"
_SETTINGS_CACHE_FILE = _EOSTUDIO_DIR / "settings_cache.json"


@dataclass
class SyncConfig:
    """Configuration for cloud sync."""

    endpoint: str = ""
    auth_token: str = ""
    auto_sync: bool = False
    sync_interval_seconds: int = 300


@dataclass
class WorkspaceState:
    """Serialisable snapshot of the current workspace."""

    open_files: List[str] = field(default_factory=list)
    cursor_positions: Dict[str, Dict[str, int]] = field(default_factory=dict)
    terminal_sessions: List[Dict[str, Any]] = field(default_factory=list)
    active_editor: str = ""
    window_layout: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Secure Storage
# ---------------------------------------------------------------------------


class SecureStorage:
    """Credential storage with OS keychain support (keyring) or encrypted JSON fallback."""

    _SERVICE_NAME = "eostudio"

    def __init__(self) -> None:
        self._keyring: Any = None
        self._use_keyring = False
        try:
            import keyring as _kr  # lazy import
            self._keyring = _kr
            # Probe that the backend is functional.
            _kr.get_password(self._SERVICE_NAME, "__probe__")
            self._use_keyring = True
        except Exception:
            self._use_keyring = False

    # -- public API ---------------------------------------------------------

    def store(self, key: str, value: str) -> None:
        """Store a credential."""
        if self._use_keyring:
            self._keyring.set_password(self._SERVICE_NAME, key, value)
        else:
            self._file_store(key, value)

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a credential.  Returns *None* if not found."""
        if self._use_keyring:
            return self._keyring.get_password(self._SERVICE_NAME, key)
        return self._file_retrieve(key)

    def delete(self, key: str) -> bool:
        """Delete a credential.  Returns *True* if it existed."""
        if self._use_keyring:
            try:
                self._keyring.delete_password(self._SERVICE_NAME, key)
                return True
            except Exception:
                return False
        return self._file_delete(key)

    # -- encrypted JSON fallback --------------------------------------------

    @staticmethod
    def _derive_key() -> bytes:
        """Derive a machine-local obfuscation key (NOT cryptographic security)."""
        raw = f"{os.getlogin()}-{SecureStorage._SERVICE_NAME}-local"
        return hashlib.sha256(raw.encode()).digest()

    @staticmethod
    def _xor_bytes(data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _load_store(self) -> Dict[str, str]:
        if not _SECURE_STORAGE_FILE.exists():
            return {}
        try:
            blob = json.loads(_SECURE_STORAGE_FILE.read_text(encoding="utf-8"))
            return {
                k: self._xor_bytes(base64.b64decode(v), self._derive_key()).decode()
                for k, v in blob.items()
            }
        except Exception:
            return {}

    def _save_store(self, store: Dict[str, str]) -> None:
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        key = self._derive_key()
        blob = {
            k: base64.b64encode(self._xor_bytes(v.encode(), key)).decode()
            for k, v in store.items()
        }
        _SECURE_STORAGE_FILE.write_text(json.dumps(blob, indent=2), encoding="utf-8")

    def _file_store(self, key: str, value: str) -> None:
        store = self._load_store()
        store[key] = value
        self._save_store(store)

    def _file_retrieve(self, key: str) -> Optional[str]:
        return self._load_store().get(key)

    def _file_delete(self, key: str) -> bool:
        store = self._load_store()
        if key not in store:
            return False
        del store[key]
        self._save_store(store)
        return True


# ---------------------------------------------------------------------------
# Cloud Sync
# ---------------------------------------------------------------------------


class CloudSync:
    """Settings sync and workspace state management.

    Backward-compatible with the original stub API:
        ``__init__(endpoint=""), connect(), disconnect(), is_connected(), sync()``
    """

    def __init__(self, endpoint: str = "", *, config: Optional[SyncConfig] = None) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = SyncConfig(endpoint=endpoint)
        # Expose ``.endpoint`` for backward compat.
        self.endpoint = self._config.endpoint
        self._connected = False
        self._client: Any = None  # httpx.Client, created lazily
        self._last_sync: float = 0.0
        self._secure_storage = SecureStorage()

    # -- connection lifecycle (backward compat) ----------------------------

    def connect(self) -> bool:
        """Establish a connection to the sync endpoint."""
        if not self._config.endpoint:
            self._connected = False
            return False
        try:
            client = self._get_client()
            resp = client.get(
                self._url("/health"),
                timeout=5.0,
            )
            self._connected = resp.status_code == 200
        except Exception:
            self._connected = False
        return self._connected

    def disconnect(self) -> None:
        """Close the connection."""
        self._connected = False
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        return self._connected

    def sync(self) -> bool:
        """Full round-trip sync (backward compat).

        Pushes locally-cached settings if available, then pulls remote settings
        and writes them to the local cache.  Returns *True* on success.
        """
        if not self._connected:
            return False
        try:
            local = self._read_settings_cache()
            if local:
                self.sync_settings(local)
            remote = self.fetch_settings()
            if remote:
                self._write_settings_cache(remote)
                self._last_sync = time.time()
                return True
        except Exception:
            pass
        return False

    # -- settings sync ------------------------------------------------------

    def sync_settings(self, settings: dict) -> bool:
        """Upload *settings* as JSON to the configured endpoint."""
        self._write_settings_cache(settings)  # local-first
        if not self._connected:
            return False
        try:
            client = self._get_client()
            resp = client.put(
                self._url("/settings"),
                json=settings,
                timeout=10.0,
            )
            return 200 <= resp.status_code < 300
        except Exception:
            return False

    def fetch_settings(self) -> dict:
        """Download settings from the remote endpoint.

        Falls back to the local cache when offline.
        """
        if self._connected:
            try:
                client = self._get_client()
                resp = client.get(self._url("/settings"), timeout=10.0)
                if resp.status_code == 200:
                    data: dict = resp.json()
                    self._write_settings_cache(data)
                    return data
            except Exception:
                pass
        return self._read_settings_cache()

    # -- workspace state ----------------------------------------------------

    @staticmethod
    def save_workspace_state(state: WorkspaceState) -> None:
        """Persist *state* locally to ``~/.eostudio/workspace_state.json``."""
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        _WORKSPACE_STATE_FILE.write_text(
            json.dumps(asdict(state), indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def load_workspace_state() -> WorkspaceState:
        """Load the workspace state from disk.  Returns defaults when absent."""
        if not _WORKSPACE_STATE_FILE.exists():
            return WorkspaceState()
        try:
            data = json.loads(_WORKSPACE_STATE_FILE.read_text(encoding="utf-8"))
            return WorkspaceState(**data)
        except Exception:
            return WorkspaceState()

    # -- import / export ----------------------------------------------------

    def export_settings(self, path: str) -> None:
        """Export settings + workspace state as a ``.zip`` bundle."""
        dest = Path(path)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            cached = self._read_settings_cache()
            zf.writestr("settings.json", json.dumps(cached, indent=2))
            if _WORKSPACE_STATE_FILE.exists():
                zf.write(_WORKSPACE_STATE_FILE, "workspace_state.json")

    @staticmethod
    def import_settings(path: str) -> None:
        """Import a settings bundle from a ``.zip`` and write it locally."""
        src = Path(path)
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src, "r") as zf:
            if "settings.json" in zf.namelist():
                _SETTINGS_CACHE_FILE.write_text(
                    zf.read("settings.json").decode("utf-8"),
                    encoding="utf-8",
                )
            if "workspace_state.json" in zf.namelist():
                _WORKSPACE_STATE_FILE.write_text(
                    zf.read("workspace_state.json").decode("utf-8"),
                    encoding="utf-8",
                )

    # -- secure storage pass-through ---------------------------------------

    @property
    def secure_storage(self) -> SecureStorage:
        return self._secure_storage

    # -- internals ----------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is None:
            import httpx  # lazy import

            headers: Dict[str, str] = {}
            if self._config.auth_token:
                headers["Authorization"] = f"Bearer {self._config.auth_token}"
            self._client = httpx.Client(headers=headers)
        return self._client

    def _url(self, path: str) -> str:
        base = self._config.endpoint.rstrip("/")
        return f"{base}{path}"

    # -- local settings cache -----------------------------------------------

    @staticmethod
    def _read_settings_cache() -> dict:
        if not _SETTINGS_CACHE_FILE.exists():
            return {}
        try:
            return json.loads(_SETTINGS_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _write_settings_cache(settings: dict) -> None:
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_CACHE_FILE.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8",
        )
