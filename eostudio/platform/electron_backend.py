"""
EoStudio Electron Backend — Electron/Node.js display backend.

Phase 3: Cross-Platform Universal Support.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.platform.display_backend import (
    DisplayBackend,
    EventType,
    InputEvent,
    WindowConfig,
)


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ElectronConfig:
    """Configuration for the Electron runtime."""

    node_path: str = "node"
    electron_path: str = "electron"
    dev_mode: bool = True
    auto_update_url: str = ""


@dataclass
class NativeMenuConfig:
    """Configuration for native application menus."""

    label: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"label": self.label, "items": self.items}


@dataclass
class SystemTrayConfig:
    """Configuration for the system tray icon and menu."""

    icon_path: str = ""
    tooltip: str = ""
    menu_items: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "iconPath": self.icon_path,
            "tooltip": self.tooltip,
            "menuItems": self.menu_items,
        }


@dataclass
class NotificationConfig:
    """Configuration for native desktop notifications."""

    title: str = ""
    body: str = ""
    icon: str = ""
    silent: bool = False
    urgency: str = "normal"  # low | normal | critical

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "icon": self.icon,
            "silent": self.silent,
            "urgency": self.urgency,
        }


@dataclass
class AutoUpdateConfig:
    """Configuration for Electron auto-update (electron-updater)."""

    feed_url: str = ""
    channel: str = "latest"
    auto_download: bool = True
    auto_install_on_quit: bool = True

    def to_dict(self) -> dict:
        return {
            "feedUrl": self.feed_url,
            "channel": self.channel,
            "autoDownload": self.auto_download,
            "autoInstallOnAppQuit": self.auto_install_on_quit,
        }


# ---------------------------------------------------------------------------
# ElectronBridge — IPC protocol between Python ↔ Node.js/Electron
# ---------------------------------------------------------------------------

class ElectronBridge:
    """Manages the IPC channel between the Python core and the Electron renderer."""

    def __init__(self, config: ElectronConfig) -> None:
        self._config = config
        self._process: Optional[subprocess.Popen] = None

    def start(self) -> bool:
        """Launch the Electron process."""
        try:
            env = os.environ.copy()
            env["EOSTUDIO_IPC"] = "1"
            self._process = subprocess.Popen(
                [self._config.electron_path, "."],
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except FileNotFoundError:
            return False

    def stop(self) -> None:
        """Terminate the Electron process."""
        if self._process is not None:
            self._process.terminate()
            self._process = None

    def send(self, channel: str, data: Any) -> None:
        """Send a JSON message to the Electron renderer via stdin IPC."""
        if self._process and self._process.stdin:
            msg = json.dumps({"channel": channel, "data": data}) + "\n"
            self._process.stdin.write(msg.encode())
            self._process.stdin.flush()

    def receive(self) -> Optional[dict]:
        """Read a single JSON message from the Electron renderer via stdout."""
        if self._process and self._process.stdout:
            line = self._process.stdout.readline()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return None
        return None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None


# ---------------------------------------------------------------------------
# ElectronBackend
# ---------------------------------------------------------------------------

class ElectronBackend(DisplayBackend):
    """Display backend that renders the UI via an Electron shell."""

    def __init__(self, electron_config: Optional[ElectronConfig] = None) -> None:
        self._config = electron_config or ElectronConfig()
        self._bridge = ElectronBridge(self._config)
        self._menus: List[NativeMenuConfig] = []
        self._tray: Optional[SystemTrayConfig] = None
        self._auto_update: Optional[AutoUpdateConfig] = None

    # -- DisplayBackend interface -------------------------------------------

    def initialize(self) -> bool:
        """Start the Electron process and establish IPC."""
        return self._bridge.start()

    def create_window(self, config: WindowConfig) -> bool:
        """Ask Electron to create a BrowserWindow."""
        self._bridge.send("create-window", {
            "title": config.title,
            "width": config.width,
            "height": config.height,
        })
        return True

    def destroy_window(self) -> None:
        """Close the Electron window."""
        self._bridge.send("close-window", {})

    def poll_events(self) -> List[InputEvent]:
        """Read pending input events from Electron."""
        events: List[InputEvent] = []
        msg = self._bridge.receive()
        while msg is not None:
            if msg.get("channel") == "input-event":
                data = msg.get("data", {})
                events.append(InputEvent(
                    type=EventType(data.get("type", "unknown")),
                    data=data,
                ))
            msg = self._bridge.receive()
        return events

    def render(self, scene: Any) -> None:
        """Send a scene payload to Electron for rendering."""
        self._bridge.send("render", scene)

    def shutdown(self) -> None:
        """Shut down the Electron process."""
        self._bridge.stop()

    # -- Electron-specific features -----------------------------------------

    def set_menu(self, menus: List[NativeMenuConfig]) -> None:
        """Configure native application menus."""
        self._menus = menus
        self._bridge.send("set-menu", [m.to_dict() for m in menus])

    def set_tray(self, tray: SystemTrayConfig) -> None:
        """Configure the system tray."""
        self._tray = tray
        self._bridge.send("set-tray", tray.to_dict())

    def show_notification(self, notification: NotificationConfig) -> None:
        """Show a native desktop notification."""
        self._bridge.send("notification", notification.to_dict())

    def configure_auto_update(self, config: AutoUpdateConfig) -> None:
        """Configure Electron auto-update settings."""
        self._auto_update = config
        self._bridge.send("auto-update", config.to_dict())

    def check_for_updates(self) -> None:
        """Trigger an update check."""
        self._bridge.send("check-updates", {})

    def get_electron_version(self) -> Optional[str]:
        """Query the running Electron version."""
        self._bridge.send("get-version", {})
        resp = self._bridge.receive()
        if resp and resp.get("channel") == "version":
            return resp.get("data", {}).get("electron")
        return None
