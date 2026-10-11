"""Drive ebuild through its real CLI; never duplicate its build logic.

EoStudio is a graphical IDE over ebuild — §15 of the platform design says it
"invokes eBuild APIs/CLI; it does not duplicate build logic". This module is
the single place that knows ebuild's command line. It translates a
:class:`BuildConfig` into a real ``ebuild`` argv and executes it.

Real ebuild CLI contract (verified against ``ebuild/cli/commands.py`` on the
ebuild master branch; there is no top-level ``--platform`` and no top-level
``--config`` — board selection is the separate ``ebuild configure --board``
step):

- ``ebuild build [--config PATH] [--build-dir DIR] [--backend NAME]``
  ``[--board BOARD] [--hardware FILE] [-j N]``
- ``ebuild test [--config PATH] [--build-dir DIR] [--filter STR]``
  ``[--runner NAME] [runner_args...]``
- ``ebuild clean [--build-dir DIR]``
- ``ebuild monitor [--port DEV] [--baud N]``
- ``ebuild configure --board BOARD [--hardware FILE] [--build-dir DIR]``

Anything that cannot be translated — a config for another build system, a
command string that does not start with a real ``ebuild <verb>``, or a flag
ebuild does not define — raises :class:`EbuildBackendError`. Fail-closed: the
caller gets an exception, never a silently substituted or guessed command.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eostudio.core.devtools.build_system import BuildConfig, BuildResult, BuildSystem


class EbuildBackendError(RuntimeError):
    """A BuildConfig cannot be translated into a real ebuild invocation.

    Raised fail-closed instead of guessing, substituting, or falling back to
    duplicated build logic.
    """


# Executable names this backend accepts as "the ebuild tool".
_EBUILD_EXECUTABLES = ("ebuild", "ebuild.exe")

# Real flags per verb: flag -> True when the flag takes a value.
_BUILD_FLAGS = {
    "--config": True,
    "--build-dir": True,
    "--backend": True,
    "--board": True,
    "--hardware": True,
    "-j": True,
    "--jobs": True,
    "-v": False,
    "--verbose": False,
}
_TEST_FLAGS = {
    "--config": True,
    "--build-dir": True,
    "--filter": True,
    "--runner": True,
}
_CLEAN_FLAGS = {
    "--build-dir": True,
}
_MONITOR_FLAGS = {
    "--port": True,
    "--baud": True,
}

# Lifecycle action -> (BuildConfig field, ebuild verb, real flags,
#                     takes --config, takes --build-dir).
_ACTIONS: Dict[str, Tuple[str, str, Dict[str, bool], bool, bool]] = {
    "build": ("build_command", "build", _BUILD_FLAGS, True, True),
    "test": ("test_command", "test", _TEST_FLAGS, True, True),
    "clean": ("clean_command", "clean", _CLEAN_FLAGS, False, True),
    "run": ("run_command", "monitor", _MONITOR_FLAGS, False, False),
}


def _elapsed_ms(start_ns: int) -> int:
    return (time.monotonic_ns() - start_ns) // 1_000_000


class EbuildBackend:
    """Translate :class:`BuildConfig` into real ``ebuild`` argv and run it."""

    def __init__(
        self,
        workspace: str | Path = ".",
        executable: str = "ebuild",
        timeout_s: int = 600,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.executable = executable
        self.timeout_s = timeout_s

    # ------------------------------------------------------------------
    # Validation (fail-closed)
    # ------------------------------------------------------------------

    def _require_ebuild_config(self, config: BuildConfig) -> None:
        if config.system is not BuildSystem.EBUILD:
            raise EbuildBackendError(
                f"EbuildBackend only drives ebuild configs, got {config.system!r}; "
                "refusing to translate another build system's commands into ebuild argv"
            )

    def _extras_from_command(self, command: str, action: str) -> Tuple[List[str], List[str]]:
        """Validate a command string; return (extra argv tokens, used flag names).

        The string must be ``ebuild <verb>`` with the verb matching the
        lifecycle action, followed only by flags ebuild really defines.
        """
        _, verb, allowed, _, _ = _ACTIONS[action]
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise EbuildBackendError(f"invalid ebuild {action} command {command!r}: cannot parse it: {exc}") from exc
        if not tokens or tokens[0] not in _EBUILD_EXECUTABLES:
            raise EbuildBackendError(
                f"invalid ebuild {action} command {command!r}: expected it to start with 'ebuild {verb}'"
            )
        if len(tokens) < 2 or tokens[1] != verb:
            got = tokens[1] if len(tokens) > 1 else "<nothing>"
            raise EbuildBackendError(
                f"invalid ebuild {action} command {command!r}: "
                f"expected 'ebuild {verb} [...]', found {got!r} — "
                "ebuild has no such invocation and this backend will not guess one"
            )
        extras: List[str] = []
        used: List[str] = []
        i = 2
        while i < len(tokens):
            token = tokens[i]
            name = token.split("=", 1)[0]
            if name not in allowed:
                raise EbuildBackendError(
                    f"invalid ebuild {action} command {command!r}: "
                    f"unknown flag {token!r} — ebuild's '{verb}' does not define it; "
                    "refusing to pass it through"
                )
            if allowed[name]:
                if "=" in token:
                    extras.append(token)
                else:
                    if i + 1 >= len(tokens):
                        raise EbuildBackendError(
                            f"invalid ebuild {action} command {command!r}: flag {token!r} needs a value"
                        )
                    extras.extend([token, tokens[i + 1]])
                    i += 1
                used.append(name)
            else:
                if "=" in token:
                    raise EbuildBackendError(
                        f"invalid ebuild {action} command {command!r}: flag {name!r} takes no value"
                    )
                extras.append(token)
                used.append(name)
            i += 1
        return extras, used

    def _assemble(
        self,
        action: str,
        extras: List[str],
        used: List[str],
        extra_flags: Optional[List[str]] = None,
    ) -> List[str]:
        """Build the final argv: executable, verb, extras, then explicit defaults."""
        _, verb, _, want_config, want_build_dir = _ACTIONS[action]
        argv = [self.executable, verb]
        argv.extend(extras)
        if extra_flags:
            argv.extend(extra_flags)
        if want_config and "--config" not in used:
            argv += ["--config", str(self.workspace / "build.yaml")]
        if want_build_dir and "--build-dir" not in used:
            argv += ["--build-dir", str(self.workspace / "_build")]
        return argv

    def _translate(self, action: str, config: BuildConfig) -> Tuple[List[str], List[str]]:
        """Validate the config's command for one lifecycle action."""
        self._require_ebuild_config(config)
        field = _ACTIONS[action][0]
        return self._extras_from_command(getattr(config, field), action)

    # ------------------------------------------------------------------
    # argv builders (pure; unit-test the exact argv here)
    # ------------------------------------------------------------------

    def build_argv(
        self,
        config: BuildConfig,
        *,
        board: Optional[str] = None,
        jobs: Optional[int] = None,
    ) -> List[str]:
        """``ebuild build`` argv for a config. Board selection stays explicit."""
        extras, used = self._translate("build", config)
        # The command string is the more specific configuration: keyword
        # arguments only fill flags the string did not already set.
        extra_flags: List[str] = []
        if board is not None and "--board" not in used:
            extra_flags += ["--board", str(board)]
        if jobs is not None and "-j" not in used and "--jobs" not in used:
            extra_flags += ["-j", str(jobs)]
        return self._assemble("build", extras, used, extra_flags)

    def test_argv(self, config: BuildConfig, *, filter: Optional[str] = None) -> List[str]:
        extras, used = self._translate("test", config)
        extra_flags = ["--filter", filter] if filter is not None and "--filter" not in used else []
        return self._assemble("test", extras, used, extra_flags)

    def clean_argv(self, config: BuildConfig) -> List[str]:
        extras, used = self._translate("clean", config)
        return self._assemble("clean", extras, used)

    def run_argv(
        self,
        config: BuildConfig,
        *,
        port: Optional[str] = None,
        baud: Optional[int] = None,
    ) -> List[str]:
        """``ebuild monitor`` argv for a config (the "run" lifecycle action)."""
        extras, used = self._translate("run", config)
        extra_flags: List[str] = []
        if port is not None and "--port" not in used:
            extra_flags += ["--port", str(port)]
        if baud is not None and "--baud" not in used:
            extra_flags += ["--baud", str(baud)]
        return self._assemble("run", extras, used, extra_flags)

    def configure_argv(self, board: str, *, hardware: Optional[str] = None) -> List[str]:
        """``ebuild configure --board`` — the real board-selection step."""
        if not board:
            raise EbuildBackendError("ebuild configure requires a board name")
        argv = [self.executable, "configure", "--board", str(board)]
        if hardware is not None:
            argv += ["--hardware", str(hardware)]
        argv += ["--build-dir", str(self.workspace / "_build")]
        return argv

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------

    def _summarize(self, proc: "subprocess.CompletedProcess[str]", start_ns: int) -> BuildResult:
        combined = proc.stdout + proc.stderr
        errors: List[str] = []
        warnings: List[str] = []
        for line in combined.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if "error" in lower:
                errors.append(stripped)
            elif "warning" in lower or "warn" in lower:
                warnings.append(stripped)

        artifacts: List[str] = []
        for adir in ("dist", "build", "target", "out", "bin"):
            artifact_path = self.workspace / adir
            if artifact_path.is_dir():
                for item in artifact_path.iterdir():
                    if item.is_file():
                        artifacts.append(str(item.relative_to(self.workspace)))

        return BuildResult(
            success=proc.returncode == 0,
            output=combined,
            errors=errors if proc.returncode != 0 else [],
            warnings=warnings,
            duration_ms=_elapsed_ms(start_ns),
            artifacts=artifacts,
        )

    def _execute(
        self,
        argv: List[str],
        *,
        env: Optional[Dict[str, str]] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        """Run an argv list directly — no shell, so nothing can be smuggled in."""
        start = time.monotonic_ns()
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        if env_extra:
            run_env.update(env_extra)
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                cwd=str(self.workspace),
                env=run_env,
            )
        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                output="",
                errors=[f"ebuild timed out after {self.timeout_s} seconds"],
                duration_ms=_elapsed_ms(start),
            )
        except FileNotFoundError as exc:
            return BuildResult(
                success=False,
                output="",
                errors=[f"ebuild executable not found: {exc}"],
                duration_ms=_elapsed_ms(start),
            )
        except OSError as exc:
            return BuildResult(
                success=False,
                output="",
                errors=[f"failed to run ebuild: {exc}"],
                duration_ms=_elapsed_ms(start),
            )
        return self._summarize(proc, start)

    def build(
        self,
        config: BuildConfig,
        *,
        target: Optional[str] = None,
        board: Optional[str] = None,
        jobs: Optional[int] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        if target is not None:
            raise EbuildBackendError(
                f"ebuild build takes no target argument (got {target!r}); "
                "express build variants in build.yaml instead of appending a target"
            )
        return self._execute(
            self.build_argv(config, board=board, jobs=jobs),
            env=dict(config.env),
            env_extra=env_extra,
        )

    def test(
        self,
        config: BuildConfig,
        *,
        target: Optional[str] = None,
        filter: Optional[str] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        argv = self.test_argv(config, filter=filter)
        if target is not None:
            # ebuild test accepts positional runner args; this preserves the
            # old `ebuild test <target>` shape as a real invocation.
            argv.append(target)
        return self._execute(argv, env=dict(config.env), env_extra=env_extra)

    def clean(self, config: BuildConfig, *, env_extra: Optional[Dict[str, str]] = None) -> BuildResult:
        return self._execute(self.clean_argv(config), env=dict(config.env), env_extra=env_extra)

    def run(
        self,
        config: BuildConfig,
        *,
        target: Optional[str] = None,
        port: Optional[str] = None,
        baud: Optional[int] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        if target is not None:
            raise EbuildBackendError(f"ebuild monitor takes no target argument (got {target!r})")
        return self._execute(
            self.run_argv(config, port=port, baud=baud),
            env=dict(config.env),
            env_extra=env_extra,
        )

    def configure(
        self,
        board: str,
        *,
        hardware: Optional[str] = None,
        env_extra: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        return self._execute(self.configure_argv(board, hardware=hardware), env_extra=env_extra)

    def execute(self, command: str, config: BuildConfig, *, env_extra: Optional[Dict[str, str]] = None) -> BuildResult:
        """Route a lifecycle command string through the backend.

        Used by :meth:`BuildSystemManager.run_task`, which only holds the
        command strings from :meth:`BuildSystemManager.get_tasks`. The string
        must still name a real ebuild lifecycle verb; anything else fails
        closed instead of being shelled out.
        """
        self._require_ebuild_config(config)
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise EbuildBackendError(f"cannot route {command!r} through ebuild: {exc}") from exc
        if not tokens or tokens[0] not in _EBUILD_EXECUTABLES or len(tokens) < 2:
            raise EbuildBackendError(f"cannot route {command!r} through ebuild: not an ebuild invocation")
        verb_to_action = {verb: action for action, (_, verb, _, _, _) in _ACTIONS.items()}
        action = verb_to_action.get(tokens[1])
        if action is None:
            raise EbuildBackendError(
                f"cannot route {command!r} through ebuild: "
                f"{tokens[1]!r} is not an EoStudio build lifecycle verb "
                f"(want one of {sorted(verb_to_action)})"
            )
        extras, used = self._extras_from_command(command, action)
        return self._execute(self._assemble(action, extras, used), env=dict(config.env), env_extra=env_extra)
