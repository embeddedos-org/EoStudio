"""Universal build system integration for EoStudio devtools."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional


class BuildSystem(Enum):
    """Supported build systems."""

    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    PIP = "pip"
    POETRY = "poetry"
    UV = "uv"
    CARGO = "cargo"
    GO = "go"
    GRADLE = "gradle"
    MAVEN = "maven"
    CMAKE = "cmake"
    MAKE = "make"
    DOTNET = "dotnet"
    SWIFT = "swift"
    BUCK = "buck"
    BAZEL = "bazel"


@dataclass
class BuildConfig:
    """Configuration for a build system."""

    system: BuildSystem
    build_command: str
    test_command: str
    clean_command: str
    run_command: str
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class BuildResult:
    """Result of a build operation."""

    success: bool
    output: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: int = 0
    artifacts: List[str] = field(default_factory=list)


@dataclass
class BuildDiagnostic:
    """A single build diagnostic (error/warning)."""

    file: str
    line: int
    column: int
    message: str
    severity: str


@dataclass
class BuildTask:
    """A named build task."""

    name: str
    command: str
    description: str
    group: str  # build, test, clean, run


# Detection config: (marker file/dir, BuildSystem)
_DETECTION_ORDER: List[tuple] = [
    ("pnpm-lock.yaml", BuildSystem.PNPM),
    ("yarn.lock", BuildSystem.YARN),
    ("package-lock.json", BuildSystem.NPM),
    ("package.json", BuildSystem.NPM),
    ("Cargo.toml", BuildSystem.CARGO),
    ("go.mod", BuildSystem.GO),
    ("pyproject.toml", None),  # special: poetry vs uv vs pip
    ("setup.py", BuildSystem.PIP),
    ("requirements.txt", BuildSystem.PIP),
    ("build.gradle", BuildSystem.GRADLE),
    ("build.gradle.kts", BuildSystem.GRADLE),
    ("pom.xml", BuildSystem.MAVEN),
    ("CMakeLists.txt", BuildSystem.CMAKE),
    ("Makefile", BuildSystem.MAKE),
    ("*.csproj", BuildSystem.DOTNET),
    ("Package.swift", BuildSystem.SWIFT),
    ("BUCK", BuildSystem.BUCK),
    (".buckconfig", BuildSystem.BUCK),
    ("BUILD", BuildSystem.BAZEL),
    ("WORKSPACE", BuildSystem.BAZEL),
    ("BUILD.bazel", BuildSystem.BAZEL),
    ("WORKSPACE.bazel", BuildSystem.BAZEL),
]

_DEFAULT_CONFIGS: Dict[BuildSystem, BuildConfig] = {
    BuildSystem.NPM: BuildConfig(
        system=BuildSystem.NPM,
        build_command="npm run build",
        test_command="npm test",
        clean_command="rm -rf node_modules dist build",
        run_command="npm start",
    ),
    BuildSystem.YARN: BuildConfig(
        system=BuildSystem.YARN,
        build_command="yarn build",
        test_command="yarn test",
        clean_command="rm -rf node_modules dist build",
        run_command="yarn start",
    ),
    BuildSystem.PNPM: BuildConfig(
        system=BuildSystem.PNPM,
        build_command="pnpm build",
        test_command="pnpm test",
        clean_command="rm -rf node_modules dist build",
        run_command="pnpm start",
    ),
    BuildSystem.PIP: BuildConfig(
        system=BuildSystem.PIP,
        build_command="python -m build",
        test_command="python -m pytest",
        clean_command="rm -rf build dist *.egg-info __pycache__",
        run_command="python -m main",
    ),
    BuildSystem.POETRY: BuildConfig(
        system=BuildSystem.POETRY,
        build_command="poetry build",
        test_command="poetry run pytest",
        clean_command="rm -rf dist",
        run_command="poetry run python -m main",
    ),
    BuildSystem.UV: BuildConfig(
        system=BuildSystem.UV,
        build_command="uv build",
        test_command="uv run pytest",
        clean_command="rm -rf dist",
        run_command="uv run python -m main",
    ),
    BuildSystem.CARGO: BuildConfig(
        system=BuildSystem.CARGO,
        build_command="cargo build",
        test_command="cargo test",
        clean_command="cargo clean",
        run_command="cargo run",
    ),
    BuildSystem.GO: BuildConfig(
        system=BuildSystem.GO,
        build_command="go build ./...",
        test_command="go test ./...",
        clean_command="go clean",
        run_command="go run .",
    ),
    BuildSystem.GRADLE: BuildConfig(
        system=BuildSystem.GRADLE,
        build_command="./gradlew build",
        test_command="./gradlew test",
        clean_command="./gradlew clean",
        run_command="./gradlew run",
    ),
    BuildSystem.MAVEN: BuildConfig(
        system=BuildSystem.MAVEN,
        build_command="mvn package",
        test_command="mvn test",
        clean_command="mvn clean",
        run_command="mvn exec:java",
    ),
    BuildSystem.CMAKE: BuildConfig(
        system=BuildSystem.CMAKE,
        build_command="cmake --build build",
        test_command="ctest --test-dir build",
        clean_command="rm -rf build",
        run_command="./build/main",
    ),
    BuildSystem.MAKE: BuildConfig(
        system=BuildSystem.MAKE,
        build_command="make",
        test_command="make test",
        clean_command="make clean",
        run_command="make run",
    ),
    BuildSystem.DOTNET: BuildConfig(
        system=BuildSystem.DOTNET,
        build_command="dotnet build",
        test_command="dotnet test",
        clean_command="dotnet clean",
        run_command="dotnet run",
    ),
    BuildSystem.SWIFT: BuildConfig(
        system=BuildSystem.SWIFT,
        build_command="swift build",
        test_command="swift test",
        clean_command="swift package clean",
        run_command="swift run",
    ),
    BuildSystem.BUCK: BuildConfig(
        system=BuildSystem.BUCK,
        build_command="buck build //...",
        test_command="buck test //...",
        clean_command="buck clean",
        run_command="buck run //:main",
    ),
    BuildSystem.BAZEL: BuildConfig(
        system=BuildSystem.BAZEL,
        build_command="bazel build //...",
        test_command="bazel test //...",
        clean_command="bazel clean",
        run_command="bazel run //:main",
    ),
}

# Patterns for parsing build errors from common compilers/tools
_ERROR_PATTERNS = [
    # GCC / Clang: file.c:10:5: error: message
    re.compile(r"^(?P<file>[^:\s]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>error|warning|note):\s*(?P<msg>.+)$"),
    # Python: File "file.py", line 10
    re.compile(r'^  File "(?P<file>[^"]+)", line (?P<line>\d+)'),
    # Rust: error[E0308]: file.rs:10:5
    re.compile(r"^(?P<sev>error|warning)\[.*\]:\s*(?P<msg>.+)$"),
    # TypeScript / ESLint: file.ts(10,5): error TS1234: message
    re.compile(r"^(?P<file>[^(\s]+)\((?P<line>\d+),(?P<col>\d+)\):\s*(?P<sev>error|warning)\s+\w+:\s*(?P<msg>.+)$"),
    # Java / Gradle: file.java:10: error: message
    re.compile(r"^(?P<file>[^:\s]+\.java):(?P<line>\d+):\s*(?P<sev>error|warning):\s*(?P<msg>.+)$"),
    # Go: file.go:10:5: message
    re.compile(r"^(?P<file>[^:\s]+\.go):(?P<line>\d+):(?P<col>\d+):\s*(?P<msg>.+)$"),
    # .NET: file.cs(10,5): error CS1234: message
    re.compile(r"^(?P<file>[^(\s]+\.cs)\((?P<line>\d+),(?P<col>\d+)\):\s*(?P<sev>error|warning)\s+\w+:\s*(?P<msg>.+)$"),
]


class BuildSystemManager:
    """Manages build system detection and operations."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self._detected: Optional[BuildSystem] = None

    def detect(self) -> BuildSystem:
        """Auto-detect the build system from config files in the workspace."""
        if self._detected is not None:
            return self._detected

        for marker, system in _DETECTION_ORDER:
            if "*" in marker:
                # Glob pattern (e.g., *.csproj)
                if list(self.workspace_path.glob(marker)):
                    self._detected = system
                    return system
            elif (self.workspace_path / marker).exists():
                if system is not None:
                    self._detected = system
                    return system
                # Special case: pyproject.toml — check for poetry or uv
                if marker == "pyproject.toml":
                    self._detected = self._detect_python_build_system()
                    return self._detected

        # Fallback: if Makefile-like files exist
        if (self.workspace_path / "GNUmakefile").exists():
            self._detected = BuildSystem.MAKE
            return self._detected

        self._detected = BuildSystem.MAKE
        return self._detected

    def _detect_python_build_system(self) -> BuildSystem:
        """Determine which Python build tool to use from pyproject.toml."""
        pyproject = self.workspace_path / "pyproject.toml"
        try:
            content = pyproject.read_text(errors="replace")
            if "[tool.poetry]" in content:
                return BuildSystem.POETRY
            if "[tool.uv]" in content or "uv.lock" in os.listdir(self.workspace_path):
                return BuildSystem.UV
        except OSError:
            pass
        return BuildSystem.PIP

    def get_config(self) -> BuildConfig:
        """Get build configuration for the detected build system."""
        system = self.detect()
        config = _DEFAULT_CONFIGS.get(system)
        if config is None:
            return BuildConfig(
                system=system,
                build_command="make",
                test_command="make test",
                clean_command="make clean",
                run_command="make run",
            )
        return BuildConfig(
            system=config.system,
            build_command=config.build_command,
            test_command=config.test_command,
            clean_command=config.clean_command,
            run_command=config.run_command,
            env=dict(config.env),
        )

    def _run(self, command: str, env_extra: Optional[Dict[str, str]] = None) -> BuildResult:
        """Execute a build command and capture the result."""
        start = time.monotonic_ns()
        env = os.environ.copy()
        config = self.get_config()
        env.update(config.env)
        if env_extra:
            env.update(env_extra)

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.workspace_path),
                env=env,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic_ns() - start) // 1_000_000
            return BuildResult(
                success=False,
                output="",
                errors=["Build timed out after 600 seconds"],
                duration_ms=elapsed,
            )
        except FileNotFoundError as e:
            elapsed = (time.monotonic_ns() - start) // 1_000_000
            return BuildResult(
                success=False,
                output="",
                errors=[f"Command not found: {e}"],
                duration_ms=elapsed,
            )

        elapsed = (time.monotonic_ns() - start) // 1_000_000
        combined = proc.stdout + proc.stderr
        errors: List[str] = []
        warnings: List[str] = []

        for output_line in combined.splitlines():
            lower = output_line.lower()
            if "error" in lower:
                errors.append(output_line.strip())
            elif "warning" in lower or "warn" in lower:
                warnings.append(output_line.strip())

        # Detect artifacts
        artifacts: List[str] = []
        artifact_dirs = ["dist", "build", "target", "out", "bin"]
        for adir in artifact_dirs:
            artifact_path = self.workspace_path / adir
            if artifact_path.exists() and artifact_path.is_dir():
                for item in artifact_path.iterdir():
                    if item.is_file():
                        artifacts.append(str(item.relative_to(self.workspace_path)))

        return BuildResult(
            success=proc.returncode == 0,
            output=combined,
            errors=errors if proc.returncode != 0 else [],
            warnings=warnings,
            duration_ms=elapsed,
            artifacts=artifacts,
        )

    def build(self, target: Optional[str] = None) -> BuildResult:
        """Run the build command."""
        config = self.get_config()
        cmd = config.build_command
        if target:
            cmd = f"{cmd} {target}"
        return self._run(cmd)

    def test(self, target: Optional[str] = None) -> BuildResult:
        """Run tests."""
        config = self.get_config()
        cmd = config.test_command
        if target:
            cmd = f"{cmd} {target}"
        return self._run(cmd)

    def clean(self) -> BuildResult:
        """Clean build artifacts."""
        config = self.get_config()
        return self._run(config.clean_command)

    def run(self, target: Optional[str] = None) -> BuildResult:
        """Run the project."""
        config = self.get_config()
        cmd = config.run_command
        if target:
            cmd = f"{cmd} {target}"
        return self._run(cmd)

    def install_deps(self) -> BuildResult:
        """Install project dependencies."""
        system = self.detect()
        install_commands = {
            BuildSystem.NPM: "npm install",
            BuildSystem.YARN: "yarn install",
            BuildSystem.PNPM: "pnpm install",
            BuildSystem.PIP: "pip install -r requirements.txt",
            BuildSystem.POETRY: "poetry install",
            BuildSystem.UV: "uv sync",
            BuildSystem.CARGO: "cargo fetch",
            BuildSystem.GO: "go mod download",
            BuildSystem.GRADLE: "./gradlew dependencies",
            BuildSystem.MAVEN: "mvn dependency:resolve",
            BuildSystem.DOTNET: "dotnet restore",
            BuildSystem.SWIFT: "swift package resolve",
        }
        cmd = install_commands.get(system, "echo 'No install command for this build system'")
        return self._run(cmd)

    def get_tasks(self) -> List[BuildTask]:
        """Get available tasks from build configuration files."""
        tasks: List[BuildTask] = []
        system = self.detect()

        # Always add standard lifecycle tasks
        config = self.get_config()
        tasks.extend([
            BuildTask(name="build", command=config.build_command, description="Build the project", group="build"),
            BuildTask(name="test", command=config.test_command, description="Run tests", group="test"),
            BuildTask(name="clean", command=config.clean_command, description="Clean artifacts", group="clean"),
            BuildTask(name="run", command=config.run_command, description="Run the project", group="run"),
        ])

        # Add system-specific tasks
        if system in (BuildSystem.NPM, BuildSystem.YARN, BuildSystem.PNPM):
            for name, script_cmd in self.get_scripts_from_package_json().items():
                prefix = {BuildSystem.NPM: "npm run", BuildSystem.YARN: "yarn", BuildSystem.PNPM: "pnpm"}[system]
                group = "test" if "test" in name else "build" if "build" in name else "run"
                tasks.append(BuildTask(
                    name=name,
                    command=f"{prefix} {name}",
                    description=f"npm script: {script_cmd}",
                    group=group,
                ))

        if system == BuildSystem.MAKE:
            for target_name in self.get_targets_from_makefile():
                group = "test" if "test" in target_name else "clean" if "clean" in target_name else "build"
                tasks.append(BuildTask(
                    name=target_name,
                    command=f"make {target_name}",
                    description=f"Makefile target: {target_name}",
                    group=group,
                ))

        return tasks

    def run_task(self, task_name: str) -> BuildResult:
        """Run a specific named task."""
        for t in self.get_tasks():
            if t.name == task_name:
                return self._run(t.command)
        return BuildResult(
            success=False,
            output="",
            errors=[f"Task '{task_name}' not found"],
        )

    def parse_errors(self, output: str) -> List[BuildDiagnostic]:
        """Parse build output into structured diagnostics."""
        diagnostics: List[BuildDiagnostic] = []
        seen = set()

        for output_line in output.splitlines():
            stripped = output_line.strip()
            if not stripped:
                continue
            for pattern in _ERROR_PATTERNS:
                match = pattern.match(stripped)
                if match:
                    groups = match.groupdict()
                    file_path = groups.get("file", "")
                    line_num = int(groups.get("line", 0))
                    col = int(groups.get("col", 0))
                    msg = groups.get("msg", stripped)
                    severity = groups.get("sev", "error")

                    key = (file_path, line_num, col, msg)
                    if key not in seen:
                        seen.add(key)
                        diagnostics.append(BuildDiagnostic(
                            file=file_path,
                            line=line_num,
                            column=col,
                            message=msg,
                            severity=severity,
                        ))
                    break

        return diagnostics

    def watch(self, callback: Callable) -> None:
        """Watch for file changes and trigger rebuilds.

        This uses a simple polling approach. For production use,
        consider using watchdog or inotify-based watchers.
        """
        import hashlib

        file_hashes: Dict[str, str] = {}

        def _hash_file(path: Path) -> str:
            try:
                return hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                return ""

        # Build initial snapshot
        watch_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".h"}
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "target"}]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix in watch_extensions:
                    file_hashes[str(fpath)] = _hash_file(fpath)

        try:
            while True:
                time.sleep(1)
                changed = False
                for root, dirs, files in os.walk(self.workspace_path):
                    dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "target"}]
                    for fname in files:
                        fpath = Path(root) / fname
                        if fpath.suffix not in watch_extensions:
                            continue
                        key = str(fpath)
                        new_hash = _hash_file(fpath)
                        old_hash = file_hashes.get(key)
                        if old_hash != new_hash:
                            file_hashes[key] = new_hash
                            changed = True

                if changed:
                    result = self.build()
                    callback(result)
        except KeyboardInterrupt:
            pass

    def get_scripts_from_package_json(self) -> Dict[str, str]:
        """Parse and return npm scripts from package.json."""
        pkg_path = self.workspace_path / "package.json"
        if not pkg_path.exists():
            return {}
        try:
            data = json.loads(pkg_path.read_text(errors="replace"))
            scripts = data.get("scripts", {})
            return {k: v for k, v in scripts.items() if isinstance(v, str)}
        except (json.JSONDecodeError, OSError):
            return {}

    def get_targets_from_makefile(self) -> List[str]:
        """Parse and return targets from a Makefile."""
        targets: List[str] = []
        makefile_names = ["Makefile", "makefile", "GNUmakefile"]

        for mf_name in makefile_names:
            mf_path = self.workspace_path / mf_name
            if not mf_path.exists():
                continue
            try:
                content = mf_path.read_text(errors="replace")
                # Match lines like "target_name:" at the start of a line, excluding special targets
                for match in re.finditer(r"^([a-zA-Z_][a-zA-Z0-9_.-]*):\s*", content, re.MULTILINE):
                    target = match.group(1)
                    if not target.startswith("."):
                        targets.append(target)
            except OSError:
                continue
            break  # only parse the first found makefile

        return targets
