"""
EoStudio Remote Development — SSH, WSL, Container, and DevContainer support.

Phase 3: Cross-Platform Universal Support.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums & Config
# ---------------------------------------------------------------------------

class RemoteType(Enum):
    """Supported remote development connection types."""

    SSH = auto()
    WSL = auto()
    CONTAINER = auto()
    DEVCONTAINER = auto()


@dataclass
class RemoteConfig:
    """Configuration for a remote connection."""

    type: RemoteType
    host: str = ""
    port: int = 22
    username: str = ""
    key_path: str = ""
    password: str = ""
    container_id: str = ""
    wsl_distro: str = "Ubuntu"


@dataclass
class DevContainerConfig:
    """Represents a ``.devcontainer/devcontainer.json`` configuration."""

    name: str = ""
    image: str = ""
    build_dockerfile: str = ""
    forward_ports: List[int] = field(default_factory=list)
    post_create_command: str = ""
    extensions: List[str] = field(default_factory=list)
    settings: Dict[str, object] = field(default_factory=dict)
    remote_user: str = "vscode"

    def to_dict(self) -> dict:
        """Serialise to a dict suitable for JSON output."""
        cfg: dict = {"name": self.name}
        if self.image:
            cfg["image"] = self.image
        if self.build_dockerfile:
            cfg["build"] = {"dockerfile": self.build_dockerfile}
        if self.forward_ports:
            cfg["forwardPorts"] = self.forward_ports
        if self.post_create_command:
            cfg["postCreateCommand"] = self.post_create_command
        if self.extensions:
            cfg["customizations"] = {"vscode": {"extensions": self.extensions}}
        if self.settings:
            cfg.setdefault("customizations", {}).setdefault("vscode", {})["settings"] = self.settings
        if self.remote_user:
            cfg["remoteUser"] = self.remote_user
        return cfg


# ---------------------------------------------------------------------------
# RemoteConnection
# ---------------------------------------------------------------------------

class RemoteConnection:
    """Manage a single remote development connection."""

    def __init__(self, config: RemoteConfig) -> None:
        self._config = config
        self._connected = False
        self._process: Optional[subprocess.Popen] = None

    # -- connection lifecycle -----------------------------------------------

    def connect(self) -> bool:
        """Establish the connection.  Returns *True* on success."""
        if self._connected:
            return True

        try:
            if self._config.type == RemoteType.SSH:
                return self._connect_ssh()
            elif self._config.type == RemoteType.WSL:
                return self._connect_wsl()
            elif self._config.type in (RemoteType.CONTAINER, RemoteType.DEVCONTAINER):
                return self._connect_container()
        except Exception:
            self._connected = False
            return False
        return False

    def disconnect(self) -> None:
        """Close the connection."""
        if self._process is not None:
            self._process.terminate()
            self._process = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # -- remote operations --------------------------------------------------

    def execute(self, command: str) -> str:
        """Run *command* on the remote and return stdout."""
        if not self._connected:
            raise RuntimeError("Not connected")

        if self._config.type == RemoteType.SSH:
            result = subprocess.run(
                self._ssh_base_cmd() + [command],
                capture_output=True, text=True, check=False,
            )
            return result.stdout

        if self._config.type == RemoteType.WSL:
            result = subprocess.run(
                ["wsl", "-d", self._config.wsl_distro, "--", "bash", "-c", command],
                capture_output=True, text=True, check=False,
            )
            return result.stdout

        if self._config.type in (RemoteType.CONTAINER, RemoteType.DEVCONTAINER):
            result = subprocess.run(
                ["docker", "exec", self._config.container_id, "bash", "-c", command],
                capture_output=True, text=True, check=False,
            )
            return result.stdout

        return ""

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a file from *local_path* to *remote_path*."""
        if not self._connected:
            return False

        if self._config.type == RemoteType.SSH:
            scp_target = f"{self._config.username}@{self._config.host}:{remote_path}"
            cmd: list[str] = ["scp"]
            if self._config.key_path:
                cmd += ["-i", self._config.key_path]
            cmd += ["-P", str(self._config.port), local_path, scp_target]
            return subprocess.run(cmd, capture_output=True, check=False).returncode == 0

        if self._config.type == RemoteType.WSL:
            win_path = local_path.replace("\\", "/")
            return subprocess.run(
                ["wsl", "-d", self._config.wsl_distro, "--", "cp", f"/mnt/{win_path}", remote_path],
                capture_output=True, check=False,
            ).returncode == 0

        if self._config.type in (RemoteType.CONTAINER, RemoteType.DEVCONTAINER):
            return subprocess.run(
                ["docker", "cp", local_path, f"{self._config.container_id}:{remote_path}"],
                capture_output=True, check=False,
            ).returncode == 0

        return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from *remote_path* to *local_path*."""
        if not self._connected:
            return False

        if self._config.type == RemoteType.SSH:
            scp_source = f"{self._config.username}@{self._config.host}:{remote_path}"
            cmd: list[str] = ["scp"]
            if self._config.key_path:
                cmd += ["-i", self._config.key_path]
            cmd += ["-P", str(self._config.port), scp_source, local_path]
            return subprocess.run(cmd, capture_output=True, check=False).returncode == 0

        if self._config.type == RemoteType.WSL:
            return subprocess.run(
                ["wsl", "-d", self._config.wsl_distro, "--", "cp", remote_path, f"/mnt/{local_path}"],
                capture_output=True, check=False,
            ).returncode == 0

        if self._config.type in (RemoteType.CONTAINER, RemoteType.DEVCONTAINER):
            return subprocess.run(
                ["docker", "cp", f"{self._config.container_id}:{remote_path}", local_path],
                capture_output=True, check=False,
            ).returncode == 0

        return False

    def list_files(self, remote_path: str) -> List[str]:
        """List files in *remote_path*."""
        output = self.execute(f"ls -1 {remote_path}")
        return [line for line in output.splitlines() if line.strip()]

    def read_file(self, remote_path: str) -> str:
        """Read the contents of a remote file."""
        return self.execute(f"cat {remote_path}")

    def write_file(self, remote_path: str, content: str) -> bool:
        """Write *content* to a remote file."""
        safe = content.replace("'", "'\\''")
        result = self.execute(f"printf '%s' '{safe}' > {remote_path}")
        return True  # best-effort; execute raises on disconnect

    def forward_port(self, local_port: int, remote_port: int) -> bool:
        """Set up SSH port forwarding (``-L``)."""
        if self._config.type != RemoteType.SSH or not self._connected:
            return False

        cmd = self._ssh_base_cmd(extra_flags=[
            "-N", "-L", f"{local_port}:localhost:{remote_port}",
        ])
        try:
            self._process = subprocess.Popen(cmd)
            return True
        except Exception:
            return False

    def sync(self, local_dir: str, remote_dir: str) -> bool:
        """Synchronise *local_dir* to *remote_dir* via rsync over SSH."""
        if not self._connected or not shutil.which("rsync"):
            return False

        if self._config.type == RemoteType.SSH:
            ssh_cmd = f"ssh -p {self._config.port}"
            if self._config.key_path:
                ssh_cmd += f" -i {self._config.key_path}"
            target = f"{self._config.username}@{self._config.host}:{remote_dir}"
            return subprocess.run(
                ["rsync", "-avz", "-e", ssh_cmd, local_dir + "/", target + "/"],
                capture_output=True, check=False,
            ).returncode == 0

        return False

    # -- private helpers ----------------------------------------------------

    def _ssh_base_cmd(self, extra_flags: Optional[List[str]] = None) -> list[str]:
        cmd: list[str] = ["ssh"]
        if self._config.key_path:
            cmd += ["-i", self._config.key_path]
        cmd += ["-p", str(self._config.port)]
        if extra_flags:
            cmd += extra_flags
        cmd.append(f"{self._config.username}@{self._config.host}")
        return cmd

    def _connect_ssh(self) -> bool:
        result = subprocess.run(
            self._ssh_base_cmd() + ["echo", "ok"],
            capture_output=True, text=True, check=False,
        )
        self._connected = result.returncode == 0
        return self._connected

    def _connect_wsl(self) -> bool:
        result = subprocess.run(
            ["wsl", "-d", self._config.wsl_distro, "--", "echo", "ok"],
            capture_output=True, text=True, check=False,
        )
        self._connected = result.returncode == 0
        return self._connected

    def _connect_container(self) -> bool:
        result = subprocess.run(
            ["docker", "exec", self._config.container_id, "echo", "ok"],
            capture_output=True, text=True, check=False,
        )
        self._connected = result.returncode == 0
        return self._connected


# ---------------------------------------------------------------------------
# RemoteManager
# ---------------------------------------------------------------------------

class RemoteManager:
    """Manage multiple named remote connections."""

    def __init__(self) -> None:
        self._connections: Dict[str, RemoteConnection] = {}

    def add(self, name: str, config: RemoteConfig) -> RemoteConnection:
        conn = RemoteConnection(config)
        self._connections[name] = conn
        return conn

    def get(self, name: str) -> Optional[RemoteConnection]:
        return self._connections.get(name)

    def remove(self, name: str) -> None:
        conn = self._connections.pop(name, None)
        if conn is not None:
            conn.disconnect()

    def list_connections(self) -> List[str]:
        return list(self._connections.keys())

    def disconnect_all(self) -> None:
        for conn in self._connections.values():
            conn.disconnect()
