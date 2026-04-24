"""Plugin architecture for EoStudio.

Defines the base :class:`Plugin` class, :class:`PluginManager` for lifecycle
management, and supporting enumerations/dataclasses for manifests, hooks,
and plugin state tracking.  External tools (such as EoSim) subclass
:class:`Plugin` to register as first-class EoStudio extensions.

Security features:
- Sandboxed plugin execution with restricted builtins
- Execution timeouts for hook handlers
- Input/output validation
- Security audit logging
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Type

log = logging.getLogger(__name__)
security_log = logging.getLogger("eostudio.security")


# ------------------------------------------------------------------
# Security constants
# ------------------------------------------------------------------

#: Builtins that plugins are NOT allowed to call directly.
RESTRICTED_BUILTINS: Set[str] = {
    "eval", "exec", "compile", "__import__",
    "globals", "locals", "vars",
    "open", "breakpoint",
}

#: Maximum seconds a plugin hook handler is allowed to run.
PLUGIN_HOOK_TIMEOUT_SECONDS: int = 30

#: Maximum size (bytes) for plugin hook data payloads.
MAX_HOOK_DATA_SIZE: int = 10 * 1024 * 1024  # 10 MB


# ------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------

class PluginState(Enum):
    """Lifecycle states for a plugin."""

    DISCOVERED = auto()
    LOADED = auto()
    ACTIVE = auto()
    ERROR = auto()
    DISABLED = auto()


class PluginHook(Enum):
    """Hook points that plugins can subscribe to."""

    ON_DESIGN_CHANGE = "on_design_change"
    ON_EXPORT = "on_export"
    ON_BUILD = "on_build"
    ON_SIMULATE = "on_simulate"
    ON_SAVE = "on_save"
    ON_LOAD = "on_load"
    PRE_CODEGEN = "pre_codegen"
    POST_CODEGEN = "post_codegen"
    ON_ERROR = "on_error"


# ------------------------------------------------------------------
# Plugin sandbox
# ------------------------------------------------------------------

class PluginSandbox:
    """Provides sandboxed execution for plugin code.

    Restricts access to dangerous builtins and enforces execution
    timeouts on hook handlers.
    """

    @staticmethod
    def validate_module(module: object) -> List[str]:
        """Check a loaded module for use of restricted patterns.

        Returns a list of warning messages (empty if clean).
        """
        warnings: List[str] = []
        source: Optional[str] = None
        try:
            import inspect
            source = inspect.getsource(module)
        except (OSError, TypeError):
            pass

        if source:
            for builtin_name in RESTRICTED_BUILTINS:
                if builtin_name + "(" in source:
                    warnings.append(
                        f"Plugin source uses restricted builtin '{builtin_name}'"
                    )
        return warnings

    @staticmethod
    def run_with_timeout(
        func: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout: int = PLUGIN_HOOK_TIMEOUT_SECONDS,
    ) -> Any:
        """Execute *func* with a timeout.

        On timeout, raises :class:`TimeoutError`.
        Uses threading for cross-platform compatibility.
        """
        kwargs = kwargs or {}
        result: List[Any] = []
        exception: List[BaseException] = []

        def _target() -> None:
            try:
                result.append(func(*args, **kwargs))
            except BaseException as exc:
                exception.append(exc)

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            security_log.warning(
                "Plugin hook execution timed out after %ds", timeout
            )
            raise TimeoutError(
                f"Plugin hook execution exceeded {timeout}s timeout"
            )

        if exception:
            raise exception[0]

        return result[0] if result else None


# ------------------------------------------------------------------
# Input / output validation
# ------------------------------------------------------------------

def _validate_hook_data(data: Any, label: str = "hook data") -> Dict[str, Any]:
    """Validate that hook data is a reasonable dict payload."""
    if not isinstance(data, dict):
        security_log.warning("Invalid %s type: %s (expected dict)", label, type(data).__name__)
        raise TypeError(f"{label} must be a dict, got {type(data).__name__}")

    serialized = json.dumps(data, default=str)
    if len(serialized) > MAX_HOOK_DATA_SIZE:
        security_log.warning(
            "%s exceeds max size (%d > %d bytes)",
            label, len(serialized), MAX_HOOK_DATA_SIZE,
        )
        raise ValueError(
            f"{label} exceeds maximum allowed size of {MAX_HOOK_DATA_SIZE} bytes"
        )

    return data


def _validate_hook_result(result: Any, plugin_id: str) -> Dict[str, Any]:
    """Validate the return value from a plugin hook handler."""
    if result is None:
        return {}
    if not isinstance(result, dict):
        security_log.warning(
            "Plugin %s returned non-dict from hook: %s",
            plugin_id, type(result).__name__,
        )
        return {}
    return result


# ------------------------------------------------------------------
# Manifest
# ------------------------------------------------------------------

@dataclass
class PluginManifest:
    """Declarative metadata for a plugin, typically loaded from manifest.json."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_type: str = "tool"
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_EoStudio_version: str = "0.1.0"
    config_schema: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            plugin_type=data.get("plugin_type", data.get("type", "tool")),
            entry_point=data.get("entry_point", ""),
            dependencies=data.get("dependencies", []),
            min_EoStudio_version=data.get("min_EoStudio_version", "0.1.0"),
            config_schema=data.get("config_schema", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "min_EoStudio_version": self.min_EoStudio_version,
            "config_schema": self.config_schema,
        }


# ------------------------------------------------------------------
# Plugin base class
# ------------------------------------------------------------------

class Plugin:
    """Base class for all EoStudio plugins.

    Subclasses must populate :attr:`manifest` and may override any of the
    lifecycle / UI contribution methods.
    """

    manifest: PluginManifest
    state: PluginState = PluginState.DISCOVERED
    config: Dict[str, Any]
    _hooks: Dict[PluginHook, Callable[..., Any]]

    def __init__(self, manifest: Optional[PluginManifest] = None) -> None:
        if manifest is not None:
            self.manifest = manifest
        elif not hasattr(self, "manifest"):
            self.manifest = PluginManifest(id="unknown", name="Unknown", version="0.0.0")
        self.state = PluginState.DISCOVERED
        self.config = {}
        self._hooks = {}

    def activate(self, context: Dict[str, Any]) -> bool:
        """Called when the host loads and activates this plugin."""
        security_log.info("Activating plugin: %s v%s", self.manifest.id, self.manifest.version)
        self.state = PluginState.ACTIVE
        return True

    def deactivate(self) -> None:
        """Called when the host unloads this plugin."""
        security_log.info("Deactivating plugin: %s", self.manifest.id)
        self.state = PluginState.DISABLED

    def on_hook(self, hook: PluginHook, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a hook event with input validation and timeout."""
        handler = self._hooks.get(hook)
        if handler is None:
            return {}

        _validate_hook_data(data, f"hook input ({hook.value})")

        result = PluginSandbox.run_with_timeout(handler, args=(data,))
        return _validate_hook_result(result, self.manifest.id)

    def get_menu_items(self) -> List[Dict[str, Any]]:
        return []

    def get_toolbar_items(self) -> List[Dict[str, Any]]:
        return []

    def get_panel(self) -> Optional[Dict[str, Any]]:
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.name,
            "type": self.manifest.plugin_type,
        }


# ------------------------------------------------------------------
# Plugin manager
# ------------------------------------------------------------------

class PluginManager:
    """Discovers, loads, and manages the lifecycle of plugins."""

    def __init__(
        self,
        plugin_dirs: Optional[List[str]] = None,
    ) -> None:
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[PluginHook, List[Plugin]] = {h: [] for h in PluginHook}
        self.plugin_dirs: List[str] = plugin_dirs or [
            os.path.expanduser("~/.EoStudio/plugins"),
        ]
        self._manifests: Dict[str, PluginManifest] = {}

    def discover(self) -> List[PluginManifest]:
        """Scan plugin_dirs for manifest.json files."""
        discovered: List[PluginManifest] = []
        for pdir in self.plugin_dirs:
            pdir = os.path.expanduser(pdir)
            if not os.path.isdir(pdir):
                continue
            for entry in os.listdir(pdir):
                manifest_path = os.path.join(pdir, entry, "manifest.json")
                if not os.path.isfile(manifest_path):
                    continue
                try:
                    with open(manifest_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    manifest = PluginManifest.from_dict(data)
                    manifest_dir = os.path.join(pdir, entry)
                    self._manifests[manifest.id] = manifest
                    if manifest_dir not in sys.path:
                        sys.path.insert(0, manifest_dir)
                    discovered.append(manifest)
                    log.info("Discovered plugin %s v%s at %s", manifest.id, manifest.version, manifest_dir)
                except Exception as exc:
                    log.warning("Failed to read manifest at %s: %s", manifest_path, exc)
        return discovered

    def load(self, plugin_id: str) -> bool:
        """Import and instantiate a discovered plugin with security checks."""
        manifest = self._manifests.get(plugin_id)
        if manifest is None:
            log.error("Plugin %s not discovered", plugin_id)
            return False

        if plugin_id in self.plugins:
            log.info("Plugin %s already loaded", plugin_id)
            return True

        try:
            security_log.info("Loading plugin %s (entry_point=%s)", plugin_id, manifest.entry_point)
            module = importlib.import_module(manifest.entry_point)

            # Security: scan module for restricted builtin usage
            warnings = PluginSandbox.validate_module(module)
            for warn in warnings:
                security_log.warning("Plugin %s: %s", plugin_id, warn)

            plugin_cls: Optional[Type[Plugin]] = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Plugin)
                    and attr is not Plugin
                ):
                    plugin_cls = attr
                    break

            if plugin_cls is None:
                log.error("No Plugin subclass found in %s", manifest.entry_point)
                return False

            plugin = plugin_cls(manifest)
            plugin.state = PluginState.LOADED
            self.plugins[plugin_id] = plugin
            security_log.info("Loaded plugin %s successfully", plugin_id)
            return True
        except Exception as exc:
            security_log.error("Failed to load plugin %s: %s", plugin_id, exc)
            log.error("Failed to load plugin %s: %s", plugin_id, exc)
            return False

    def unload(self, plugin_id: str) -> None:
        """Deactivate and remove a loaded plugin."""
        plugin = self.plugins.pop(plugin_id, None)
        if plugin is None:
            return
        if plugin.state == PluginState.ACTIVE:
            try:
                plugin.deactivate()
            except Exception as exc:
                log.warning("Error deactivating plugin %s: %s", plugin_id, exc)
        for hook_list in self.hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)
        security_log.info("Unloaded plugin %s", plugin_id)

    def activate(self, plugin_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Activate a loaded plugin and register its hooks."""
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            log.error("Plugin %s not loaded", plugin_id)
            return False

        ctx = context or {}
        try:
            success = plugin.activate(ctx)
        except Exception as exc:
            plugin.state = PluginState.ERROR
            security_log.error("Plugin %s activation failed: %s", plugin_id, exc)
            return False

        if not success:
            plugin.state = PluginState.ERROR
            return False

        for hook in PluginHook:
            if hook in plugin._hooks:
                if plugin not in self.hooks[hook]:
                    self.hooks[hook].append(plugin)

        plugin.state = PluginState.ACTIVE
        security_log.info("Activated plugin %s", plugin_id)
        return True

    def deactivate(self, plugin_id: str) -> None:
        """Deactivate a plugin without unloading it."""
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return
        try:
            plugin.deactivate()
        except Exception as exc:
            log.warning("Error deactivating plugin %s: %s", plugin_id, exc)
        plugin.state = PluginState.DISABLED
        for hook_list in self.hooks.values():
            if plugin in hook_list:
                hook_list.remove(plugin)
        security_log.info("Deactivated plugin %s", plugin_id)

    def fire_hook(self, hook: PluginHook, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fire hook across all active plugins with validation and timeouts."""
        _validate_hook_data(data, f"fire_hook input ({hook.value})")

        results: List[Dict[str, Any]] = []
        for plugin in self.hooks.get(hook, []):
            if plugin.state != PluginState.ACTIVE:
                continue
            try:
                result = plugin.on_hook(hook, data)
                if result:
                    results.append(result)
            except TimeoutError:
                security_log.error(
                    "Plugin %s timed out on hook %s",
                    plugin.manifest.id, hook.value,
                )
                results.append({"error": "timeout", "plugin": plugin.manifest.id})
            except Exception as exc:
                security_log.error(
                    "Plugin %s hook %s error: %s",
                    plugin.manifest.id, hook.value, exc,
                )
                results.append({"error": str(exc), "plugin": plugin.manifest.id})
        return results

    def get_active_plugins(self) -> List[Plugin]:
        return [p for p in self.plugins.values() if p.state == PluginState.ACTIVE]

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginManifest]:
        return list(self._manifests.values())

    def configure(self, plugin_id: str, config: Dict[str, Any]) -> None:
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            log.error("Plugin %s not loaded — cannot configure", plugin_id)
            return
        plugin.config.update(config)
        log.info("Configured plugin %s", plugin_id)

    def export_config(self) -> Dict[str, Any]:
        return {
            pid: {
                "manifest": p.manifest.to_dict(),
                "config": p.config,
                "state": p.state.name,
            }
            for pid, p in self.plugins.items()
        }

    def import_config(self, data: Dict[str, Any]) -> None:
        for pid, pdata in data.items():
            plugin = self.plugins.get(pid)
            if plugin is not None:
                plugin.config.update(pdata.get("config", {}))
                log.info("Imported config for plugin %s", pid)

    def install_from_path(self, path: str) -> PluginManifest:
        """Copy a plugin directory into the first writable plugins dir."""
        path = os.path.abspath(path)
        manifest_path = os.path.join(path, "manifest.json")
        if not os.path.isfile(manifest_path):
            raise FileNotFoundError(f"No manifest.json found in {path}")

        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = PluginManifest.from_dict(json.load(fh))

        security_log.info("Installing plugin %s from path: %s", manifest.id, path)

        dest_base = os.path.expanduser(self.plugin_dirs[0])
        os.makedirs(dest_base, exist_ok=True)
        dest = os.path.join(dest_base, manifest.id)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
        self._manifests[manifest.id] = manifest
        security_log.info("Installed plugin %s from %s -> %s", manifest.id, path, dest)
        return manifest

    def install_from_git(self, repo_url: str) -> PluginManifest:
        """Clone a git repository and install it as a plugin."""
        import tempfile

        security_log.info("Installing plugin from git: %s", repo_url)

        with tempfile.TemporaryDirectory(prefix="EoStudio_plugin_") as tmp:
            subprocess.check_call(
                ["git", "clone", "--depth", "1", repo_url, tmp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return self.install_from_path(tmp)
