"""
EoStudio Configuration Manager.

Hierarchical configuration system with schema validation, secrets management,
environment variable overrides, and change notifications.

Scope resolution order (highest priority first):
    FOLDER -> WORKSPACE -> USER -> SYSTEM -> DEFAULT
"""
from __future__ import annotations

import base64
import copy
import enum
import hashlib
import json
import logging
import os
import platform
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class ConfigScope(enum.IntEnum):
    """Configuration scopes ordered from lowest to highest priority."""

    DEFAULT = 0
    SYSTEM = 1
    USER = 2
    WORKSPACE = 3
    FOLDER = 4


@dataclass
class ConfigSchema:
    """Schema definition for a configuration key."""

    key: str
    type: Type
    default: Any
    description: str = ""
    enum_values: Optional[List[Any]] = None
    deprecated: bool = False


# ---------------------------------------------------------------------------
# Built-in default schemas
# ---------------------------------------------------------------------------

_BUILTIN_SCHEMAS: List[ConfigSchema] = [
    ConfigSchema("editor.fontSize", int, 14, "Font size in pixels for the editor."),
    ConfigSchema("editor.tabSize", int, 4, "Number of spaces per tab."),
    ConfigSchema("editor.insertSpaces", bool, True, "Insert spaces when pressing Tab."),
    ConfigSchema(
        "editor.theme",
        str,
        "dark",
        "Color theme for the editor.",
        enum_values=["dark", "light", "high-contrast"],
    ),
    ConfigSchema(
        "editor.wordWrap", str, "off", "Word wrap mode.",
        enum_values=["off", "on", "wordWrapColumn", "bounded"],
    ),
    ConfigSchema(
        "editor.lineNumbers", str, "on", "Line number rendering.",
        enum_values=["off", "on", "relative"],
    ),
    ConfigSchema("editor.minimap.enabled", bool, True, "Show minimap."),
    ConfigSchema("editor.formatOnSave", bool, False, "Format the file on save."),
    ConfigSchema(
        "editor.autoSave", str, "off", "Auto-save mode.",
        enum_values=["off", "afterDelay", "onFocusChange"],
    ),
    ConfigSchema("editor.autoSaveDelay", int, 1000, "Auto-save delay in milliseconds."),
    ConfigSchema(
        "editor.renderWhitespace", str, "selection", "Whitespace rendering.",
        enum_values=["none", "boundary", "selection", "all"],
    ),
    ConfigSchema("terminal.shell", str, "", "Path to the default terminal shell."),
    ConfigSchema("terminal.fontSize", int, 13, "Font size for the integrated terminal."),
    ConfigSchema(
        "terminal.cursorStyle", str, "block", "Terminal cursor style.",
        enum_values=["block", "underline", "line"],
    ),
    ConfigSchema("files.encoding", str, "utf-8", "Default file encoding."),
    ConfigSchema("files.autoGuessEncoding", bool, False, "Auto-detect file encoding."),
    ConfigSchema(
        "files.trimTrailingWhitespace", bool, False,
        "Trim trailing whitespace on save.",
    ),
    ConfigSchema(
        "files.insertFinalNewline", bool, False,
        "Insert a final newline at end of file on save.",
    ),
    ConfigSchema("files.exclude", dict, {}, "Glob patterns for files to exclude."),
    ConfigSchema("search.exclude", dict, {}, "Glob patterns for search exclusion."),
    ConfigSchema("workbench.sideBar.visible", bool, True, "Show the side bar."),
    ConfigSchema("workbench.statusBar.visible", bool, True, "Show the status bar."),
    ConfigSchema("window.title", str, "EoStudio", "Window title template."),
    ConfigSchema("debug.console.fontSize", int, 13, "Font size for the debug console."),
    ConfigSchema("telemetry.enabled", bool, True, "Enable telemetry."),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge *override* into a copy of *base*."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _read_json(path: Path) -> Dict:
    """Read a JSON file, returning an empty dict on any failure."""
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read config %s: %s", path, exc)
    return {}


def _write_json(path: Path, data: Dict) -> None:
    """Atomically write *data* as pretty-printed JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(data, indent=4, sort_keys=True) + "\n", encoding="utf-8"
        )
        tmp.replace(path)
    except OSError as exc:
        logger.error("Failed to write config %s: %s", path, exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _env_key(config_key: str) -> str:
    """Convert a dotted config key to an EOSTUDIO_ environment variable name.

    Example: ``editor.fontSize`` -> ``EOSTUDIO_EDITOR_FONTSIZE``
    """
    return "EOSTUDIO_" + config_key.replace(".", "_").upper()


def _coerce_env(value_str: str, target_type: Type) -> Any:
    """Best-effort coercion of an env-var string to *target_type*."""
    if target_type is bool:
        return value_str.lower() in ("1", "true", "yes")
    if target_type is int:
        return int(value_str)
    if target_type is float:
        return float(value_str)
    if target_type is dict or target_type is list:
        return json.loads(value_str)
    return value_str


# ---------------------------------------------------------------------------
# SecretsManager
# ---------------------------------------------------------------------------


class SecretsManager:
    """Secure credential storage.

    Attempts to use the OS keychain via the optional ``keyring`` package.
    Falls back to an XOR-obfuscated JSON file at ``~/.eostudio/secrets.json``
    when ``keyring`` is unavailable.

    Note: The file-based fallback provides obfuscation, not strong encryption.
    Install ``keyring`` (``pip install keyring``) for production use.
    """

    _SERVICE = "eostudio"

    def __init__(self) -> None:
        self._keyring = self._try_import_keyring()
        self._fallback_path = Path.home() / ".eostudio" / "secrets.json"
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by *key*. Returns ``None`` if not found."""
        if self._keyring is not None:
            try:
                return self._keyring.get_password(self._SERVICE, key)
            except Exception as exc:
                logger.warning("Keyring get failed for %r: %s", key, exc)
        return self._fallback_get(key)

    def set_secret(self, key: str, value: str) -> None:
        """Store a secret."""
        if self._keyring is not None:
            try:
                self._keyring.set_password(self._SERVICE, key, value)
                return
            except Exception as exc:
                logger.warning("Keyring set failed for %r: %s", key, exc)
        self._fallback_set(key, value)

    def delete_secret(self, key: str) -> None:
        """Delete a secret."""
        if self._keyring is not None:
            try:
                self._keyring.delete_password(self._SERVICE, key)
                return
            except Exception as exc:
                logger.warning("Keyring delete failed for %r: %s", key, exc)
        self._fallback_delete(key)

    def list_secrets(self) -> List[str]:
        """List stored secret keys (file-based backend only)."""
        store = self._load_fallback()
        return list(store.keys())

    # -- keyring import -----------------------------------------------------

    @staticmethod
    def _try_import_keyring():
        try:
            import keyring  # type: ignore[import-untyped]
            return keyring
        except ImportError:
            return None

    # -- file-based fallback ------------------------------------------------

    def _derive_key(self) -> bytes:
        """Derive a machine-local obfuscation key."""
        seed = (
            f"{platform.node()}-"
            f"{os.getlogin() if hasattr(os, 'getlogin') else 'user'}-"
            f"eostudio"
        )
        return hashlib.sha256(seed.encode()).digest()

    def _xor_bytes(self, data: bytes) -> bytes:
        key = self._derive_key()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _load_fallback(self) -> Dict[str, str]:
        with self._lock:
            if not self._fallback_path.is_file():
                return {}
            try:
                raw = self._fallback_path.read_bytes()
                decrypted = self._xor_bytes(base64.b64decode(raw))
                return json.loads(decrypted.decode("utf-8"))
            except Exception as exc:
                logger.warning("Failed to read secrets file: %s", exc)
                return {}

    def _save_fallback(self, store: Dict[str, str]) -> None:
        with self._lock:
            self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(store, sort_keys=True).encode("utf-8")
            encoded = base64.b64encode(self._xor_bytes(payload))
            tmp = self._fallback_path.with_suffix(".tmp")
            try:
                tmp.write_bytes(encoded)
                tmp.replace(self._fallback_path)
            except OSError as exc:
                logger.error("Failed to write secrets: %s", exc)
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                raise

    def _fallback_get(self, key: str) -> Optional[str]:
        return self._load_fallback().get(key)

    def _fallback_set(self, key: str, value: str) -> None:
        store = self._load_fallback()
        store[key] = value
        self._save_fallback(store)

    def _fallback_delete(self, key: str) -> None:
        store = self._load_fallback()
        if key in store:
            del store[key]
            self._save_fallback(store)


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------


class ConfigManager:
    """Hierarchical configuration manager for EoStudio.

    Resolution order (highest priority wins)::

        env vars -> FOLDER -> WORKSPACE -> USER -> SYSTEM -> DEFAULT

    Usage::

        cfg = ConfigManager()
        cfg.set_workspace_path("/path/to/project")
        font = cfg.get("editor.fontSize")          # 14 (default)
        cfg.set("editor.fontSize", 16)              # persisted in USER scope
        cfg.on_change("editor.fontSize", lambda k, v: print(k, v))
    """

    def __init__(self, workspace_path: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._schemas: Dict[str, ConfigSchema] = {}
        self._listeners: Dict[str, List[Callable]] = {}
        self._workspace_path: Optional[Path] = (
            Path(workspace_path) if workspace_path else None
        )
        self._folder_paths: List[Path] = []

        # Scope -> in-memory cache (loaded lazily on first access)
        self._caches: Dict[ConfigScope, Optional[Dict]] = {
            ConfigScope.DEFAULT: None,
            ConfigScope.SYSTEM: None,
            ConfigScope.USER: None,
            ConfigScope.WORKSPACE: None,
            ConfigScope.FOLDER: None,
        }

        # Register built-in schemas
        for schema in _BUILTIN_SCHEMAS:
            self.register_schema(schema)

    # -- scope file paths ---------------------------------------------------

    @staticmethod
    def _system_config_path() -> Path:
        if platform.system() == "Windows":
            base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
            return Path(base) / "eostudio" / "settings.json"
        return Path("/etc/eostudio/settings.json")

    @staticmethod
    def _user_config_path() -> Path:
        return Path.home() / ".eostudio" / "settings.json"

    def _workspace_config_path(self) -> Optional[Path]:
        if self._workspace_path:
            return self._workspace_path / ".eostudio" / "settings.json"
        return None

    def _folder_config_paths(self) -> List[Path]:
        return [p / ".eostudio" / "settings.json" for p in self._folder_paths]

    def _path_for_scope(self, scope: ConfigScope) -> Optional[Path]:
        if scope == ConfigScope.SYSTEM:
            return self._system_config_path()
        if scope == ConfigScope.USER:
            return self._user_config_path()
        if scope == ConfigScope.WORKSPACE:
            return self._workspace_config_path()
        return None  # DEFAULT and FOLDER handled separately

    # -- loading / caching --------------------------------------------------

    def _load_scope(self, scope: ConfigScope) -> Dict:
        if scope == ConfigScope.DEFAULT:
            return {s.key: s.default for s in self._schemas.values()}
        if scope == ConfigScope.FOLDER:
            merged: Dict = {}
            for p in self._folder_config_paths():
                merged = _deep_merge(merged, _read_json(p))
            return merged
        path = self._path_for_scope(scope)
        return _read_json(path) if path else {}

    def _get_scope_data(self, scope: ConfigScope) -> Dict:
        with self._lock:
            if self._caches[scope] is None:
                self._caches[scope] = self._load_scope(scope)
            return self._caches[scope]  # type: ignore[return-value]

    def _invalidate(self, scope: ConfigScope) -> None:
        with self._lock:
            self._caches[scope] = None

    def _invalidate_all(self) -> None:
        with self._lock:
            for scope in ConfigScope:
                self._caches[scope] = None

    def reload(self) -> None:
        """Force reload of all config scopes from disk."""
        self._invalidate_all()

    # -- public API: workspace / folder paths --------------------------------

    def set_workspace_path(self, path: str) -> None:
        """Set the workspace root directory."""
        self._workspace_path = Path(path)
        self._invalidate(ConfigScope.WORKSPACE)

    def add_folder_path(self, path: str) -> None:
        """Add a folder root for multi-root workspace support."""
        p = Path(path)
        if p not in self._folder_paths:
            self._folder_paths.append(p)
            self._invalidate(ConfigScope.FOLDER)

    def remove_folder_path(self, path: str) -> None:
        """Remove a folder root."""
        p = Path(path)
        if p in self._folder_paths:
            self._folder_paths.remove(p)
            self._invalidate(ConfigScope.FOLDER)

    # -- schema management --------------------------------------------------

    def register_schema(self, schema: ConfigSchema) -> None:
        """Register (or update) a configuration schema."""
        with self._lock:
            self._schemas[schema.key] = schema
            self._invalidate(ConfigScope.DEFAULT)

    def get_schema(self, key: str) -> Optional[ConfigSchema]:
        """Return the schema for *key*, or ``None`` if unregistered."""
        return self._schemas.get(key)

    def validate(self, key: str, value: Any) -> bool:
        """Validate *value* against the schema registered for *key*.

        Returns ``True`` if valid or if no schema is registered.
        """
        schema = self._schemas.get(key)
        if schema is None:
            return True
        if not isinstance(value, schema.type):
            return False
        if schema.enum_values is not None and value not in schema.enum_values:
            return False
        return True

    # -- environment variable overrides -------------------------------------

    def _env_override(self, key: str) -> Optional[Any]:
        """Check for an ``EOSTUDIO_*`` environment variable override."""
        env_name = _env_key(key)
        raw = os.environ.get(env_name)
        if raw is None:
            return None
        schema = self._schemas.get(key)
        target_type = schema.type if schema else str
        try:
            return _coerce_env(raw, target_type)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Bad env override %s=%r: %s", env_name, raw, exc)
            return None

    # -- core get / set / delete --------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get the effective value for *key*.

        Resolution: env var -> folder -> workspace -> user -> system ->
        defaults -> *default*.
        """
        schema = self._schemas.get(key)
        if schema and schema.deprecated:
            logger.warning("Config key %r is deprecated.", key)

        # Env override wins
        env = self._env_override(key)
        if env is not None:
            return env

        # Walk scopes from highest to lowest priority
        for scope in reversed(ConfigScope):
            data = self._get_scope_data(scope)
            if key in data:
                return data[key]
        return default

    def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.USER,
    ) -> None:
        """Persist *value* for *key* in the given *scope*.

        Raises ``ValueError`` if the value fails schema validation or if
        attempting to write to the DEFAULT scope.
        """
        if scope == ConfigScope.DEFAULT:
            raise ValueError(
                "Cannot write to DEFAULT scope; register a schema instead."
            )

        if not self.validate(key, value):
            schema = self._schemas.get(key)
            raise ValueError(
                f"Invalid value {value!r} for {key!r}. "
                f"Expected type={schema.type.__name__}, "  # type: ignore[union-attr]
                f"enum_values={schema.enum_values}"  # type: ignore[union-attr]
            )

        old_value = self.get(key)

        if scope == ConfigScope.FOLDER:
            if not self._folder_paths:
                raise ValueError(
                    "No folder paths configured. Call add_folder_path() first."
                )
            path = self._folder_paths[0] / ".eostudio" / "settings.json"
        else:
            path = self._path_for_scope(scope)
            if path is None:
                raise ValueError(
                    f"No config path available for scope {scope.name}."
                )

        data = _read_json(path)
        data[key] = value
        _write_json(path, data)
        self._invalidate(scope)

        new_value = self.get(key)
        if new_value != old_value:
            self._fire_listeners(key, new_value)

    def delete(self, key: str, scope: ConfigScope = ConfigScope.USER) -> None:
        """Remove *key* from the given *scope*."""
        if scope == ConfigScope.DEFAULT:
            raise ValueError("Cannot delete from DEFAULT scope.")

        old_value = self.get(key)

        if scope == ConfigScope.FOLDER:
            for folder in self._folder_paths:
                p = folder / ".eostudio" / "settings.json"
                data = _read_json(p)
                if key in data:
                    del data[key]
                    _write_json(p, data)
        else:
            path = self._path_for_scope(scope)
            if path is None:
                return
            data = _read_json(path)
            if key in data:
                del data[key]
                _write_json(path, data)

        self._invalidate(scope)

        new_value = self.get(key)
        if new_value != old_value:
            self._fire_listeners(key, new_value)

    # -- bulk queries -------------------------------------------------------

    def get_all(self) -> Dict:
        """Return the fully merged configuration (all scopes + env overrides)."""
        merged: Dict = {}
        for scope in ConfigScope:
            merged = _deep_merge(merged, self._get_scope_data(scope))

        # Apply env overrides on top
        for key in list(merged.keys()) + [s.key for s in self._schemas.values()]:
            env = self._env_override(key)
            if env is not None:
                merged[key] = env
        return merged

    def get_scope(self, scope: ConfigScope) -> Dict:
        """Return the raw configuration for a single *scope*."""
        return copy.deepcopy(self._get_scope_data(scope))

    def list_keys(self, scope: Optional[ConfigScope] = None) -> List[str]:
        """List all known keys.

        If *scope* is given, only keys in that scope are returned.
        Otherwise returns the union across all scopes plus registered schemas.
        """
        if scope is not None:
            return sorted(self._get_scope_data(scope).keys())
        keys: set[str] = set()
        for s in ConfigScope:
            keys.update(self._get_scope_data(s).keys())
        keys.update(self._schemas.keys())
        return sorted(keys)

    # -- reset --------------------------------------------------------------

    def reset(
        self,
        key: Optional[str] = None,
        scope: ConfigScope = ConfigScope.USER,
    ) -> None:
        """Reset *key* (or all keys) in *scope* to defaults.

        If *key* is ``None``, the entire scope file is cleared.
        """
        if key is None:
            if scope == ConfigScope.DEFAULT:
                raise ValueError("Cannot reset DEFAULT scope.")
            if scope == ConfigScope.FOLDER:
                for folder in self._folder_paths:
                    p = folder / ".eostudio" / "settings.json"
                    if p.is_file():
                        _write_json(p, {})
            else:
                path = self._path_for_scope(scope)
                if path and path.is_file():
                    _write_json(path, {})
            self._invalidate(scope)
        else:
            self.delete(key, scope)

    # -- import / export ----------------------------------------------------

    def export_config(self, scope: ConfigScope, path: str) -> None:
        """Export the configuration for *scope* to a JSON file at *path*."""
        data = self.get_scope(scope)
        _write_json(Path(path), data)

    def import_config(
        self, path: str, scope: ConfigScope = ConfigScope.USER
    ) -> None:
        """Import configuration from a JSON file into *scope*.

        Existing keys in *scope* are merged (imported values win).
        """
        if scope == ConfigScope.DEFAULT:
            raise ValueError("Cannot import into DEFAULT scope.")
        incoming = _read_json(Path(path))
        if not incoming:
            return

        target = self._path_for_scope(scope)
        if scope == ConfigScope.FOLDER:
            if not self._folder_paths:
                raise ValueError("No folder paths configured.")
            target = self._folder_paths[0] / ".eostudio" / "settings.json"
        if target is None:
            raise ValueError(f"No config path for scope {scope.name}.")

        existing = _read_json(target)
        merged = _deep_merge(existing, incoming)
        _write_json(target, merged)
        self._invalidate(scope)

    # -- change listeners ---------------------------------------------------

    def on_change(self, key: str, callback: Callable) -> Callable:
        """Register *callback* to be invoked when *key* changes.

        Callback signature: ``callback(key: str, new_value: Any)``.
        Returns *callback* for use as a decorator.
        """
        with self._lock:
            self._listeners.setdefault(key, []).append(callback)
        return callback

    def remove_listener(self, key: str, callback: Callable) -> None:
        """Remove a previously registered change listener."""
        with self._lock:
            cbs = self._listeners.get(key, [])
            if callback in cbs:
                cbs.remove(callback)

    def _fire_listeners(self, key: str, new_value: Any) -> None:
        with self._lock:
            callbacks = list(self._listeners.get(key, []))
        for cb in callbacks:
            try:
                cb(key, new_value)
            except Exception:
                logger.exception(
                    "Error in config change listener for %r", key
                )
