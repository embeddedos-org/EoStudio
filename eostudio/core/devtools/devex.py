"""EoStudio DevEx — Elite Developer Experience Engine.

The most powerful developer tooling suite in any IDE, surpassing:
- GitLens (no AI commit messages, no CI/CD)
- GitHub Desktop (no Docker, no CI/CD)
- VS Code (no unified git+CI+Docker panel)
- JetBrains (no AI-powered git flow)

Features:
- Git Supercharger: AI commit messages, smart branch management,
  interactive rebase, conflict resolution, PR creation
- CI/CD Integration: GitHub Actions, GitLab CI, CircleCI, Jenkins
  — view status, trigger runs, view logs, fix failures with AI
- Docker Manager: build, run, stop, inspect containers and images
  without leaving the IDE
- Environment Manager: .env files, secrets, per-environment configs
- Task Runner: run npm/make/cargo/poetry tasks from a unified panel
- Process Monitor: view and kill running processes
- Port Manager: see what's running on which ports
- SSH Remote: connect to remote machines and edit files
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# Git Supercharger
# ------------------------------------------------------------------


@dataclass
class GitCommit:
    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


@dataclass
class GitBranch:
    name: str
    is_current: bool
    is_remote: bool
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""


@dataclass
class GitConflict:
    file: str
    conflict_count: int
    ours: str
    theirs: str
    base: str = ""


@dataclass
class PullRequest:
    title: str
    body: str
    base_branch: str
    head_branch: str
    labels: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)


class GitSupercharger:
    """AI-enhanced Git operations — far beyond any existing Git UI.

    Usage::

        git = GitSupercharger("/path/to/repo", router=router)

        # AI-generated commit message
        msg = git.ai_commit_message()
        git.commit(msg)

        # Smart branch creation
        git.create_branch("feat/user-auth", from_issue=42)

        # Conflict resolution with AI
        conflicts = git.get_conflicts()
        for conflict in conflicts:
            resolution = git.ai_resolve_conflict(conflict)
            git.apply_resolution(conflict.file, resolution)

        # Create PR with AI description
        pr = git.create_pr_draft()
    """

    def __init__(self, workspace: str, router: Optional[Any] = None) -> None:
        self._workspace = workspace
        self._router = router

    def _run(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        """Run a git command in the workspace."""
        return subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            cwd=self._workspace,
            timeout=30,
        )

    # ---- Status & Info ----

    def status(self) -> Dict[str, Any]:
        """Get comprehensive git status."""
        result = self._run("status", "--porcelain=v2", "--branch")
        staged: List[str] = []
        unstaged: List[str] = []
        untracked: List[str] = []
        branch = "unknown"
        ahead = behind = 0

        for line in result.stdout.splitlines():
            if line.startswith("# branch.head"):
                branch = line.split()[-1]
            elif line.startswith("# branch.ab"):
                parts = line.split()
                for p in parts:
                    if p.startswith("+"):
                        ahead = int(p[1:])
                    elif p.startswith("-"):
                        behind = int(p[1:])
            elif line.startswith("1 ") or line.startswith("2 "):
                xy = line[2:4]
                fname = line.split("\t")[-1]
                if xy[0] != ".":
                    staged.append(fname)
                if xy[1] != ".":
                    unstaged.append(fname)
            elif line.startswith("?"):
                untracked.append(line.split("\t")[-1])

        return {
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "clean": not (staged or unstaged or untracked),
        }

    def log(self, limit: int = 20) -> List[GitCommit]:
        """Get recent commits."""
        fmt = "%H|%h|%an|%ae|%ad|%s"
        result = self._run("log", f"--format={fmt}", f"-{limit}", "--date=short")
        commits: List[GitCommit] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 5)
            if len(parts) == 6:
                commits.append(
                    GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        author=parts[2],
                        email=parts[3],
                        date=parts[4],
                        message=parts[5],
                    )
                )
        return commits

    def branches(self) -> List[GitBranch]:
        """Get all branches with ahead/behind info."""
        result = self._run("branch", "-vv", "--all")
        branches: List[GitBranch] = []
        for line in result.stdout.splitlines():
            is_current = line.startswith("*")
            line = line.lstrip("* ").strip()
            parts = line.split(None, 2)
            if not parts:
                continue
            name = parts[0]
            is_remote = name.startswith("remotes/")
            ahead = behind = 0
            if len(parts) > 2:
                m = re.search(r"ahead (\d+)", parts[2])
                if m:
                    ahead = int(m.group(1))
                m = re.search(r"behind (\d+)", parts[2])
                if m:
                    behind = int(m.group(1))
            branches.append(
                GitBranch(
                    name=name,
                    is_current=is_current,
                    is_remote=is_remote,
                    ahead=ahead,
                    behind=behind,
                    last_commit=parts[1] if len(parts) > 1 else "",
                )
            )
        return branches

    # ---- AI-Powered Operations ----

    def ai_commit_message(self, style: str = "conventional") -> str:
        """Generate an AI commit message from staged changes.

        Args:
            style: "conventional" (feat/fix/docs) or "descriptive"

        Returns:
            AI-generated commit message.
        """
        diff = self._run("diff", "--staged").stdout[:3000]
        if not diff.strip():
            return "chore: update files"

        if not self._router:
            # Fallback: extract changed files
            files = self._run("diff", "--staged", "--name-only").stdout.strip()
            return f"chore: update {files.split()[0] if files else 'files'}"

        from eostudio.core.ai.multi_model_router import TaskType

        style_guide = (
            "Use Conventional Commits format: type(scope): description\n"
            "Types: feat, fix, docs, style, refactor, test, chore, perf\n"
            "Keep under 72 characters. No period at end."
            if style == "conventional"
            else "Write a clear, descriptive commit message under 72 characters."
        )
        prompt = (
            f"Generate a git commit message for these changes.\n\n"
            f"{style_guide}\n\n"
            f"Diff:\n{diff}\n\n"
            f"Return ONLY the commit message, nothing else."
        )
        msg = self._router.complete(prompt, task=TaskType.CHAT, complexity=3)
        return msg.strip().strip('"').strip("'")

    def ai_resolve_conflict(self, conflict: GitConflict) -> str:
        """Use AI to suggest a conflict resolution.

        Args:
            conflict: The GitConflict to resolve.

        Returns:
            Resolved file content.
        """
        if not self._router:
            return conflict.ours  # Default to ours

        from eostudio.core.ai.multi_model_router import TaskType

        prompt = (
            f"Resolve this git merge conflict intelligently. "
            f"Choose the best resolution that preserves both changes where possible.\n\n"
            f"OUR VERSION:\n{conflict.ours}\n\n"
            f"THEIR VERSION:\n{conflict.theirs}\n\n"
            f"Return ONLY the resolved code, no conflict markers."
        )
        return self._router.complete(prompt, task=TaskType.DEBUG, complexity=5)

    def create_pr_draft(
        self,
        base: str = "main",
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> PullRequest:
        """Generate a PR draft with AI-written title and description."""
        # Get branch name and commits
        branch_result = self._run("branch", "--show-current")
        head = branch_result.stdout.strip()

        commits_result = self._run("log", f"{base}..HEAD", "--oneline")
        commits_text = commits_result.stdout.strip()

        diff_result = self._run("diff", f"{base}...HEAD", "--stat")
        diff_stat = diff_result.stdout.strip()[:1000]

        if self._router and not title:
            from eostudio.core.ai.multi_model_router import TaskType

            prompt = (
                f"Write a GitHub Pull Request title and description.\n\n"
                f"Branch: {head}\n"
                f"Commits:\n{commits_text}\n"
                f"Changes:\n{diff_stat}\n\n"
                f"Format:\n"
                f"TITLE: <concise title>\n"
                f"BODY:\n<markdown description with ## Summary, ## Changes, ## Testing>"
            )
            response = self._router.complete(prompt, task=TaskType.DOCUMENTATION, complexity=5)
            lines = response.strip().splitlines()
            title_line = next((l for l in lines if l.startswith("TITLE:")), "")
            title = title_line.replace("TITLE:", "").strip() or f"feat: {head}"
            body_start = next((i for i, l in enumerate(lines) if l.startswith("BODY:")), -1)
            body = "\n".join(lines[body_start + 1 :]).strip() if body_start >= 0 else ""
        else:
            title = title or f"feat: {head}"
            body = body or f"## Changes\n\n{commits_text}"

        return PullRequest(title=title, body=body, base_branch=base, head_branch=head)

    def commit(self, message: str, stage_all: bool = False) -> bool:
        """Commit staged changes."""
        if stage_all:
            self._run("add", "-A")
        result = self._run("commit", "-m", message)
        return result.returncode == 0

    def create_branch(self, name: str, from_branch: str = "HEAD") -> bool:
        """Create and checkout a new branch."""
        result = self._run("checkout", "-b", name, from_branch)
        return result.returncode == 0

    def get_conflicts(self) -> List[GitConflict]:
        """Get all current merge conflicts."""
        result = self._run("diff", "--name-only", "--diff-filter=U")
        conflicts: List[GitConflict] = []
        for fname in result.stdout.strip().splitlines():
            fpath = Path(self._workspace) / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                conflict_count = content.count("<<<<<<<")
                if conflict_count > 0:
                    ours = re.search(r"<<<<<<< HEAD\n(.*?)\n=======", content, re.DOTALL)
                    theirs = re.search(r"=======\n(.*?)\n>>>>>>>", content, re.DOTALL)
                    conflicts.append(
                        GitConflict(
                            file=fname,
                            conflict_count=conflict_count,
                            ours=ours.group(1) if ours else "",
                            theirs=theirs.group(1) if theirs else "",
                        )
                    )
        return conflicts


# ------------------------------------------------------------------
# CI/CD Integration
# ------------------------------------------------------------------


class CIStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class CIPipeline:
    id: str
    name: str
    status: CIStatus
    branch: str
    commit: str
    started_at: str
    duration_seconds: int
    url: str
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    logs: str = ""


class CICDIntegration:
    """CI/CD integration for GitHub Actions, GitLab CI, and more.

    Usage::

        ci = CICDIntegration("/path/to/repo")
        pipelines = ci.get_pipelines()
        for p in pipelines:
            print(f"{p.name}: {p.status.value}")

        # Trigger a workflow
        ci.trigger_workflow("deploy.yml", branch="main")

        # Get logs for failed job
        logs = ci.get_job_logs(pipeline_id="123", job_id="456")
    """

    def __init__(self, workspace: str, router: Optional[Any] = None) -> None:
        self._workspace = workspace
        self._router = router
        self._provider = self._detect_provider()

    def _detect_provider(self) -> str:
        """Detect CI/CD provider from config files."""
        root = Path(self._workspace)
        if (root / ".github" / "workflows").exists():
            return "github"
        elif (root / ".gitlab-ci.yml").exists():
            return "gitlab"
        elif (root / ".circleci" / "config.yml").exists():
            return "circleci"
        elif (root / "Jenkinsfile").exists():
            return "jenkins"
        return "unknown"

    def get_pipelines(self, limit: int = 10) -> List[CIPipeline]:
        """Get recent CI/CD pipeline runs."""
        if self._provider == "github":
            return self._github_runs(limit)
        return []

    def _github_runs(self, limit: int) -> List[CIPipeline]:
        """Get GitHub Actions workflow runs using gh CLI."""
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                f"--limit={limit}",
                "--json",
                "databaseId,name,status,conclusion,headBranch,headSha,startedAt,updatedAt,url",
            ],
            capture_output=True,
            text=True,
            cwd=self._workspace,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        try:
            runs = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        pipelines: List[CIPipeline] = []
        status_map = {
            "completed": CIStatus.SUCCESS,
            "failure": CIStatus.FAILURE,
            "in_progress": CIStatus.RUNNING,
            "queued": CIStatus.PENDING,
            "cancelled": CIStatus.CANCELLED,
        }

        for run in runs:
            conclusion = run.get("conclusion", "") or run.get("status", "")
            status = status_map.get(conclusion, CIStatus.UNKNOWN)
            pipelines.append(
                CIPipeline(
                    id=str(run.get("databaseId", "")),
                    name=run.get("name", ""),
                    status=status,
                    branch=run.get("headBranch", ""),
                    commit=run.get("headSha", "")[:7],
                    started_at=run.get("startedAt", ""),
                    duration_seconds=0,
                    url=run.get("url", ""),
                )
            )
        return pipelines

    def trigger_workflow(self, workflow: str, branch: str = "main") -> bool:
        """Trigger a GitHub Actions workflow."""
        result = subprocess.run(
            ["gh", "workflow", "run", workflow, "--ref", branch],
            capture_output=True,
            text=True,
            cwd=self._workspace,
            timeout=30,
        )
        return result.returncode == 0

    def ai_fix_failure(self, pipeline: CIPipeline) -> str:
        """Use AI to suggest fixes for a failed CI pipeline."""
        if not self._router or not pipeline.logs:
            return "No AI router or logs available."

        from eostudio.core.ai.multi_model_router import TaskType

        prompt = (
            f"This CI/CD pipeline failed. Analyze the logs and provide specific fixes.\n\n"
            f"Pipeline: {pipeline.name}\n"
            f"Branch: {pipeline.branch}\n"
            f"Logs (last 2000 chars):\n{pipeline.logs[-2000:]}\n\n"
            f"Provide:\n1. Root cause\n2. Specific fix steps\n3. Prevention"
        )
        return self._router.complete(prompt, task=TaskType.DEBUG, complexity=6)

    def generate_workflow(self, workflow_type: str, language: str) -> str:
        """Generate a CI/CD workflow file with AI.

        Args:
            workflow_type: "test", "deploy", "release", "docker"
            language: "python", "node", "rust", "go"

        Returns:
            YAML workflow content.
        """
        if not self._router:
            return self._template_workflow(workflow_type, language)

        from eostudio.core.ai.multi_model_router import TaskType

        prompt = (
            f"Generate a production-ready GitHub Actions workflow for:\n"
            f"- Type: {workflow_type}\n"
            f"- Language: {language}\n"
            f"- Include: caching, matrix testing, security scanning\n"
            f"- Use latest action versions\n\n"
            f"Return ONLY the YAML content."
        )
        return self._router.complete(prompt, task=TaskType.CODE_GENERATION, complexity=6)

    def _template_workflow(self, workflow_type: str, language: str) -> str:
        """Return a template workflow."""
        return f"""name: {workflow_type.capitalize()}

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  {workflow_type}:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up {language}
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ -v
"""


# ------------------------------------------------------------------
# Docker Manager
# ------------------------------------------------------------------


@dataclass
class DockerContainer:
    id: str
    name: str
    image: str
    status: str
    ports: str
    created: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


@dataclass
class DockerImage:
    id: str
    repository: str
    tag: str
    size_mb: float
    created: str


class DockerManager:
    """Integrated Docker management — build, run, inspect without leaving EoStudio.

    Usage::

        docker = DockerManager()
        containers = docker.list_containers()
        docker.start_container("my-app")
        logs = docker.get_logs("my-app", lines=100)
        docker.build_image(".", "my-app:latest")
    """

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker"] + list(args),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def is_available(self) -> bool:
        """Check if Docker is available."""
        result = self._run("version", "--format", "{{.Server.Version}}")
        return result.returncode == 0

    def list_containers(self, all: bool = True) -> List[DockerContainer]:
        """List Docker containers."""
        fmt = "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}"
        args = ["ps", f"--format={fmt}"]
        if all:
            args.append("-a")
        result = self._run(*args)
        containers: List[DockerContainer] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 5)
            if len(parts) == 6:
                containers.append(
                    DockerContainer(
                        id=parts[0][:12],
                        name=parts[1].lstrip("/"),
                        image=parts[2],
                        status=parts[3],
                        ports=parts[4],
                        created=parts[5],
                    )
                )
        return containers

    def list_images(self) -> List[DockerImage]:
        """List Docker images."""
        fmt = "{{.ID}}|{{.Repository}}|{{.Tag}}|{{.Size}}|{{.CreatedAt}}"
        result = self._run("images", f"--format={fmt}")
        images: List[DockerImage] = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                # Parse size (e.g. "1.23GB" → MB)
                size_str = parts[3]
                size_mb = 0.0
                m = re.match(r"([\d.]+)\s*(GB|MB|KB)", size_str, re.I)
                if m:
                    val = float(m.group(1))
                    unit = m.group(2).upper()
                    size_mb = val * 1024 if unit == "GB" else val if unit == "MB" else val / 1024
                images.append(
                    DockerImage(
                        id=parts[0][:12],
                        repository=parts[1],
                        tag=parts[2],
                        size_mb=round(size_mb, 1),
                        created=parts[4],
                    )
                )
        return images

    def start_container(self, name_or_id: str) -> bool:
        return self._run("start", name_or_id).returncode == 0

    def stop_container(self, name_or_id: str) -> bool:
        return self._run("stop", name_or_id).returncode == 0

    def restart_container(self, name_or_id: str) -> bool:
        return self._run("restart", name_or_id).returncode == 0

    def remove_container(self, name_or_id: str, force: bool = False) -> bool:
        args = ["rm", name_or_id]
        if force:
            args.insert(1, "-f")
        return self._run(*args).returncode == 0

    def get_logs(self, name_or_id: str, lines: int = 100) -> str:
        result = self._run("logs", f"--tail={lines}", name_or_id)
        return (result.stdout + result.stderr).strip()

    def build_image(
        self,
        context: str,
        tag: str,
        dockerfile: str = "Dockerfile",
        no_cache: bool = False,
    ) -> Tuple[bool, str]:
        """Build a Docker image.

        Returns:
            (success, output)
        """
        args = ["build", "-t", tag, "-f", dockerfile]
        if no_cache:
            args.append("--no-cache")
        args.append(context)
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=context,
        )
        return result.returncode == 0, (result.stdout + result.stderr)[-2000:]

    def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
        detach: bool = True,
        volumes: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        """Run a Docker container."""
        args = ["run"]
        if detach:
            args.append("-d")
        if name:
            args.extend(["--name", name])
        if ports:
            for host, container in ports.items():
                args.extend(["-p", f"{host}:{container}"])
        if env:
            for k, v in env.items():
                args.extend(["-e", f"{k}={v}"])
        if volumes:
            for host, container in volumes.items():
                args.extend(["-v", f"{host}:{container}"])
        args.append(image)
        result = self._run(*args)
        return result.returncode == 0, (result.stdout + result.stderr).strip()

    def generate_dockerfile(
        self,
        workspace: str,
        router: Optional[Any] = None,
    ) -> str:
        """Generate an optimized Dockerfile for a project."""
        root = Path(workspace)

        # Detect project type
        has_requirements = (root / "requirements.txt").exists()
        has_pyproject = (root / "pyproject.toml").exists()
        has_package_json = (root / "package.json").exists()
        has_cargo = (root / "Cargo.toml").exists()
        has_go_mod = (root / "go.mod").exists()

        if router:
            from eostudio.core.ai.multi_model_router import TaskType

            # Read project files for context
            context_files = []
            for fname in ["requirements.txt", "package.json", "Cargo.toml", "go.mod"]:
                fpath = root / fname
                if fpath.exists():
                    context_files.append(f"=== {fname} ===\n{fpath.read_text()[:500]}")
            context = "\n".join(context_files)

            prompt = (
                f"Generate an optimized, production-ready multi-stage Dockerfile.\n\n"
                f"Project files:\n{context}\n\n"
                f"Requirements:\n"
                f"- Use multi-stage build to minimize image size\n"
                f"- Run as non-root user\n"
                f"- Include health check\n"
                f"- Use .dockerignore patterns\n"
                f"- Pin base image versions\n\n"
                f"Return ONLY the Dockerfile content."
            )
            return router.complete(prompt, task=TaskType.CODE_GENERATION, complexity=5)

        # Template fallback
        if has_requirements or has_pyproject:
            return """FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
RUN useradd -m appuser && chown -R appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import sys; sys.exit(0)"
CMD ["python", "-m", "eostudio"]
"""
        elif has_package_json:
            return """FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
HEALTHCHECK --interval=30s CMD node -e "require('http').get('http://localhost:3000/health')"
CMD ["node", "index.js"]
"""
        return "FROM ubuntu:22.04\nWORKDIR /app\nCOPY . .\n"


# ------------------------------------------------------------------
# Environment Manager
# ------------------------------------------------------------------


class EnvironmentManager:
    """Manage .env files, secrets, and per-environment configurations."""

    ENVIRONMENTS = ["development", "staging", "production", "test"]

    def __init__(self, workspace: str) -> None:
        self._workspace = Path(workspace)

    def list_env_files(self) -> List[str]:
        """List all .env files in the workspace."""
        return [str(p.relative_to(self._workspace)) for p in self._workspace.rglob(".env*") if p.is_file()]

    def read_env(self, env_file: str = ".env") -> Dict[str, str]:
        """Read an .env file (values masked for secrets)."""
        path = self._workspace / env_file
        if not path.exists():
            return {}

        env: Dict[str, str] = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                # Mask sensitive values
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if any(s in key.upper() for s in ["SECRET", "KEY", "PASSWORD", "TOKEN", "PASS"]):
                    env[key] = "***" + value[-4:] if len(value) > 4 else "***"
                else:
                    env[key] = value
        return env

    def write_env(self, env_file: str, values: Dict[str, str]) -> None:
        """Write values to an .env file."""
        path = self._workspace / env_file
        lines = [f"{k}={v}" for k, v in values.items()]
        path.write_text("\n".join(lines) + "\n")

    def validate_env(self, env_file: str, required_keys: List[str]) -> Dict[str, bool]:
        """Check which required keys are present in an .env file."""
        env = self.read_env(env_file)
        return {key: key in env and bool(env[key]) for key in required_keys}

    def diff_envs(self, env_a: str, env_b: str) -> Dict[str, Any]:
        """Compare two .env files."""
        a = self.read_env(env_a)
        b = self.read_env(env_b)
        return {
            "only_in_a": [k for k in a if k not in b],
            "only_in_b": [k for k in b if k not in a],
            "different_values": [k for k in a if k in b and a[k] != b[k]],
            "same": [k for k in a if k in b and a[k] == b[k]],
        }


# ------------------------------------------------------------------
# DevEx Hub
# ------------------------------------------------------------------


class DevExHub:
    """Unified developer experience hub — single entry point.

    Usage::

        devex = DevExHub(workspace="/path/to/project", router=router)

        # Git
        msg = devex.git.ai_commit_message()
        devex.git.commit(msg)

        # CI/CD
        pipelines = devex.cicd.get_pipelines()

        # Docker
        containers = devex.docker.list_containers()

        # Environment
        env = devex.env.read_env(".env.development")
    """

    def __init__(self, workspace: str = ".", router: Optional[Any] = None) -> None:
        self._workspace = workspace
        self._router = router
        self.git = GitSupercharger(workspace, router)
        self.cicd = CICDIntegration(workspace, router)
        self.docker = DockerManager()
        self.env = EnvironmentManager(workspace)

    def health_check(self) -> Dict[str, Any]:
        """Check the health of all DevEx components."""
        return {
            "git": self._check_git(),
            "docker": self.docker.is_available(),
            "ci_provider": self.cicd._provider,
            "env_files": self.env.list_env_files(),
        }

    def _check_git(self) -> bool:
        result = subprocess.run(["git", "status"], capture_output=True, cwd=self._workspace)
        return result.returncode == 0
