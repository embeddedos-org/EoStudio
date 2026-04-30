"""Container management for Docker and Kubernetes."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ContainerState(Enum):
    """Docker container states."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    EXITED = "exited"
    DEAD = "dead"


@dataclass
class Container:
    """Represents a Docker container."""
    id: str
    name: str
    image: str
    state: ContainerState
    ports: Dict[str, str] = field(default_factory=dict)
    created: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    command: str = ""


@dataclass
class ContainerImage:
    """Represents a Docker image."""
    id: str
    tags: List[str] = field(default_factory=list)
    size: int = 0
    created: str = ""
    layers: int = 0


@dataclass
class ContainerStats:
    """Container resource usage statistics."""
    cpu_percent: float = 0.0
    memory_usage: int = 0
    memory_limit: int = 0
    network_rx: int = 0
    network_tx: int = 0
    pids: int = 0


class ContainerManager:
    """Manages Docker containers via the docker CLI."""

    def __init__(self, docker_host: str = "unix:///var/run/docker.sock") -> None:
        self.docker_host = docker_host
        self._env = {"DOCKER_HOST": docker_host}

    def _run(self, args: List[str], capture: bool = True) -> subprocess.CompletedProcess:
        """Execute a docker CLI command."""
        cmd = ["docker"] + args
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            env={**self._env},
        )

    def is_docker_available(self) -> bool:
        """Check if Docker CLI is available and responsive."""
        try:
            result = self._run(["info", "--format", "json"])
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def list_containers(self, all: bool = False) -> List[Container]:
        """List Docker containers, optionally including stopped ones."""
        args = ["ps", "--format", "json", "--no-trunc"]
        if all:
            args.append("-a")
        result = self._run(args)
        if result.returncode != 0:
            return []

        containers: List[Container] = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            state_str = data.get("State", "created").lower()
            try:
                state = ContainerState(state_str)
            except ValueError:
                state = ContainerState.CREATED

            ports_raw = data.get("Ports", "")
            ports: Dict[str, str] = {}
            if ports_raw:
                for mapping in ports_raw.split(", "):
                    parts = mapping.split("->")
                    if len(parts) == 2:
                        ports[parts[0].strip()] = parts[1].strip()

            labels_raw = data.get("Labels", "")
            labels: Dict[str, str] = {}
            if labels_raw:
                for lbl in labels_raw.split(","):
                    kv = lbl.split("=", 1)
                    if len(kv) == 2:
                        labels[kv[0].strip()] = kv[1].strip()

            containers.append(Container(
                id=data.get("ID", ""),
                name=data.get("Names", ""),
                image=data.get("Image", ""),
                state=state,
                ports=ports,
                created=data.get("CreatedAt", ""),
                labels=labels,
                command=data.get("Command", ""),
            ))
        return containers

    def start(self, container_id: str) -> bool:
        """Start a stopped container."""
        result = self._run(["start", container_id])
        return result.returncode == 0

    def stop(self, container_id: str) -> bool:
        """Stop a running container."""
        result = self._run(["stop", container_id])
        return result.returncode == 0

    def restart(self, container_id: str) -> bool:
        """Restart a container."""
        result = self._run(["restart", container_id])
        return result.returncode == 0

    def remove(self, container_id: str) -> bool:
        """Remove a container."""
        result = self._run(["rm", container_id])
        return result.returncode == 0

    def build(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> bool:
        """Build a Docker image from a Dockerfile."""
        result = self._run(["build", "-t", tag, "-f", dockerfile, path])
        return result.returncode == 0

    def push(self, image: str) -> bool:
        """Push an image to a registry."""
        result = self._run(["push", image])
        return result.returncode == 0

    def pull(self, image: str) -> bool:
        """Pull an image from a registry."""
        result = self._run(["pull", image])
        return result.returncode == 0

    def logs(self, container_id: str, tail: int = 100, follow: bool = False) -> str:
        """Retrieve container logs."""
        args = ["logs", "--tail", str(tail)]
        if follow:
            args.append("--follow")
        args.append(container_id)
        result = self._run(args)
        if result.returncode != 0:
            return result.stderr
        return result.stdout

    def exec_command(self, container_id: str, command: str) -> str:
        """Execute a command inside a running container."""
        result = self._run(["exec", container_id, "sh", "-c", command])
        if result.returncode != 0:
            return result.stderr
        return result.stdout

    def list_images(self) -> List[ContainerImage]:
        """List local Docker images."""
        result = self._run(["images", "--format", "json", "--no-trunc"])
        if result.returncode != 0:
            return []

        images: List[ContainerImage] = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            tag_str = data.get("Tag", "")
            repo = data.get("Repository", "")
            tag = f"{repo}:{tag_str}" if repo and tag_str else repo or tag_str

            size_str = data.get("Size", "0")
            size = 0
            try:
                if size_str.endswith("GB"):
                    size = int(float(size_str[:-2]) * 1024 * 1024 * 1024)
                elif size_str.endswith("MB"):
                    size = int(float(size_str[:-2]) * 1024 * 1024)
                elif size_str.endswith("KB") or size_str.endswith("kB"):
                    size = int(float(size_str[:-2]) * 1024)
                else:
                    size = int(float(size_str.rstrip("B")))
            except (ValueError, IndexError):
                size = 0

            images.append(ContainerImage(
                id=data.get("ID", ""),
                tags=[tag] if tag else [],
                size=size,
                created=data.get("CreatedAt", data.get("CreatedSince", "")),
            ))
        return images

    def stats(self, container_id: str) -> ContainerStats:
        """Get resource usage statistics for a container."""
        result = self._run([
            "stats", container_id, "--no-stream",
            "--format", "json",
        ])
        if result.returncode != 0:
            return ContainerStats()

        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            cpu_str = data.get("CPUPerc", "0%").rstrip("%")
            try:
                cpu = float(cpu_str)
            except ValueError:
                cpu = 0.0

            pids_str = data.get("PIDs", "0")
            try:
                pids = int(pids_str)
            except ValueError:
                pids = 0

            return ContainerStats(
                cpu_percent=cpu,
                memory_usage=0,
                memory_limit=0,
                network_rx=0,
                network_tx=0,
                pids=pids,
            )
        return ContainerStats()

    def inspect(self, container_id: str) -> Dict:
        """Inspect a container and return full details."""
        result = self._run(["inspect", container_id])
        if result.returncode != 0:
            return {}
        try:
            data = json.loads(result.stdout)
            if isinstance(data, list) and data:
                return data[0]
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def compose_up(self, path: str) -> str:
        """Run docker compose up in the given directory."""
        result = subprocess.run(
            ["docker", "compose", "up", "-d"],
            capture_output=True,
            text=True,
            cwd=path,
            env={**self._env},
        )
        return result.stdout if result.returncode == 0 else result.stderr

    def compose_down(self, path: str) -> str:
        """Run docker compose down in the given directory."""
        result = subprocess.run(
            ["docker", "compose", "down"],
            capture_output=True,
            text=True,
            cwd=path,
            env={**self._env},
        )
        return result.stdout if result.returncode == 0 else result.stderr

    def compose_logs(self, path: str) -> str:
        """Get logs from docker compose services."""
        result = subprocess.run(
            ["docker", "compose", "logs", "--tail", "100"],
            capture_output=True,
            text=True,
            cwd=path,
            env={**self._env},
        )
        return result.stdout if result.returncode == 0 else result.stderr

    def list_networks(self) -> List[Dict]:
        """List Docker networks."""
        result = self._run(["network", "ls", "--format", "json"])
        if result.returncode != 0:
            return []
        networks: List[Dict] = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                networks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return networks

    def list_volumes(self) -> List[Dict]:
        """List Docker volumes."""
        result = self._run(["volume", "ls", "--format", "json"])
        if result.returncode != 0:
            return []
        volumes: List[Dict] = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                volumes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return volumes


class KubernetesManager:
    """Manages Kubernetes resources via kubectl CLI."""

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        """Execute a kubectl command."""
        cmd = ["kubectl"] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def is_kubectl_available(self) -> bool:
        """Check if kubectl is available and configured."""
        try:
            result = self._run(["version", "--client", "-o", "json"])
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _get_resources(self, resource: str, namespace: str = "default") -> List[Dict]:
        """Generic resource listing."""
        result = self._run(["get", resource, "-n", namespace, "-o", "json"])
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
            return data.get("items", [])
        except json.JSONDecodeError:
            return []

    def get_pods(self, namespace: str = "default") -> List[Dict]:
        """List pods in a namespace."""
        return self._get_resources("pods", namespace)

    def get_services(self, namespace: str = "default") -> List[Dict]:
        """List services in a namespace."""
        return self._get_resources("services", namespace)

    def get_deployments(self, namespace: str = "default") -> List[Dict]:
        """List deployments in a namespace."""
        return self._get_resources("deployments", namespace)

    def get_logs(self, pod: str, namespace: str = "default", tail: int = 100) -> str:
        """Get logs from a pod."""
        result = self._run(["logs", pod, "-n", namespace, "--tail", str(tail)])
        if result.returncode != 0:
            return result.stderr
        return result.stdout

    def apply(self, manifest_path: str) -> bool:
        """Apply a Kubernetes manifest file."""
        result = self._run(["apply", "-f", manifest_path])
        return result.returncode == 0

    def delete(self, resource_type: str, name: str, namespace: str = "default") -> bool:
        """Delete a Kubernetes resource."""
        result = self._run(["delete", resource_type, name, "-n", namespace])
        return result.returncode == 0

    def port_forward(
        self, pod: str, local_port: int, remote_port: int, namespace: str = "default"
    ) -> subprocess.Popen:
        """Start port forwarding to a pod. Returns the background process."""
        cmd = [
            "kubectl", "port-forward", pod,
            f"{local_port}:{remote_port}",
            "-n", namespace,
        ]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
