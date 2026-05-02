"""Terminal emulator for EoStudio IDE.

Provides PTY-based terminal sessions with ANSI parsing, command history,
cross-platform shell detection, and multi-session management.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Platform-specific imports (guarded)
_IS_WINDOWS = sys.platform == "win32"

if not _IS_WINDOWS:
    import fcntl
    import pty
    import struct
    import termios


# ---------------------------------------------------------------------------
# ANSI escape sequence parser
# ---------------------------------------------------------------------------

# Matches all ANSI escape sequences: CSI (ESC[), OSC (ESC]), and simple (ESC + char)
_ANSI_RE = re.compile(
    r"""
    (?:\x1b          # ESC character
      (?:
        \[           # CSI - Control Sequence Introducer
        [0-9;]*      # parameter bytes
        [A-Za-z]     # final byte
      |
        \]           # OSC - Operating System Command
        .*?          # payload
        (?:\x1b\\|\x07)  # ST (ESC\) or BEL
      |
        [()#][0-9A-Za-z]?  # Character set / line drawing
      |
        [A-Za-z]     # Simple two-char sequence (e.g. ESC M)
      )
    )
    """,
    re.VERBOSE,
)

# Matches CSI sequences specifically for structured parsing
_CSI_RE = re.compile(r"\x1b\[([0-9;]*)([A-Za-z])")


class AnsiParser:
    """Parses and processes ANSI escape sequences in terminal output."""

    # SGR (Select Graphic Rendition) color names
    _SGR_COLORS = {
        0: "reset", 1: "bold", 2: "dim", 3: "italic", 4: "underline",
        7: "inverse", 8: "hidden", 9: "strikethrough",
        30: "black", 31: "red", 32: "green", 33: "yellow",
        34: "blue", 35: "magenta", 36: "cyan", 37: "white",
        40: "bg_black", 41: "bg_red", 42: "bg_green", 43: "bg_yellow",
        44: "bg_blue", 45: "bg_magenta", 46: "bg_cyan", 47: "bg_white",
        90: "bright_black", 91: "bright_red", 92: "bright_green",
        93: "bright_yellow", 94: "bright_blue", 95: "bright_magenta",
        96: "bright_cyan", 97: "bright_white",
    }

    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI escape sequences from *text*."""
        return _ANSI_RE.sub("", text)

    @staticmethod
    def parse(text: str) -> List[Tuple[str, str, List[int]]]:
        """Parse *text* into segments of ``(content, seq_type, params)``.

        Each tuple contains:
        - *content*: the text chunk **before** the sequence (may be empty).
        - *seq_type*: the CSI final byte (e.g. ``'m'`` for SGR) or ``''``
          for the trailing plain-text segment.
        - *params*: list of integer parameters from the CSI sequence.
        """
        segments: List[Tuple[str, str, List[int]]] = []
        last_end = 0
        for m in _CSI_RE.finditer(text):
            plain = _ANSI_RE.sub("", text[last_end:m.start()])
            params_str = m.group(1)
            params = [int(p) for p in params_str.split(";") if p] if params_str else [0]
            segments.append((plain, m.group(2), params))
            last_end = m.end()
        # Trailing plain text
        trailing = _ANSI_RE.sub("", text[last_end:])
        if trailing or not segments:
            segments.append((trailing, "", []))
        return segments

    @classmethod
    def to_html(cls, text: str) -> str:
        """Convert ANSI-colored *text* to simple HTML ``<span>`` tags."""
        from html import escape as html_escape

        parts: List[str] = []
        open_spans = 0
        for plain, seq_type, params in cls.parse(text):
            if plain:
                parts.append(html_escape(plain))
            if seq_type == "m":
                for p in params:
                    if p == 0:
                        parts.append("</span>" * open_spans)
                        open_spans = 0
                    elif p in cls._SGR_COLORS:
                        parts.append(f'<span class="ansi-{cls._SGR_COLORS[p]}">')
                        open_spans += 1
        parts.append("</span>" * open_spans)
        return "".join(parts)


# ---------------------------------------------------------------------------
# Shell detection
# ---------------------------------------------------------------------------

def _detect_shell() -> str:
    """Return the path to the best available shell for the current platform."""
    if _IS_WINDOWS:
        # Prefer PowerShell 7+ (pwsh) > PowerShell 5 > cmd
        for candidate in ("pwsh.exe", "powershell.exe", "cmd.exe"):
            found = _which(candidate)
            if found:
                return found
        return "cmd.exe"

    # Unix: check $SHELL, then try common shells
    shell = os.environ.get("SHELL", "")
    if shell and os.path.isfile(shell):
        return shell

    for candidate in ("bash", "zsh", "fish", "sh"):
        found = _which(candidate)
        if found:
            return found
    return "/bin/sh"


def _which(name: str) -> Optional[str]:
    """Minimal which(1) implementation using PATH."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    extensions = [""]
    if _IS_WINDOWS:
        extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
    for d in path_dirs:
        for ext in extensions:
            full = os.path.join(d, name + ext)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return full
    return None


# ---------------------------------------------------------------------------
# Command history with persistence
# ---------------------------------------------------------------------------

_HISTORY_DIR = Path.home() / ".eostudio"
_HISTORY_FILE = _HISTORY_DIR / "terminal_history.json"
_MAX_HISTORY = 5000


class CommandHistory:
    """Per-session command history with JSON persistence."""

    def __init__(self, max_entries: int = _MAX_HISTORY) -> None:
        self._entries: List[str] = []
        self._max = max_entries
        self._lock = threading.Lock()
        self._load()

    # -- public API --

    def add(self, command: str) -> None:
        cmd = command.strip()
        if not cmd:
            return
        with self._lock:
            # Deduplicate consecutive
            if self._entries and self._entries[-1] == cmd:
                return
            self._entries.append(cmd)
            if len(self._entries) > self._max:
                self._entries = self._entries[-self._max:]
            self._save()

    def search(self, prefix: str) -> List[str]:
        with self._lock:
            return [e for e in self._entries if e.startswith(prefix)]

    def get_all(self) -> List[str]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._save()

    @property
    def last(self) -> Optional[str]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    # -- persistence --

    def _load(self) -> None:
        try:
            if _HISTORY_FILE.is_file():
                data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._entries = [str(e) for e in data[-self._max:]]
        except (json.JSONDecodeError, OSError):
            self._entries = []

    def _save(self) -> None:
        try:
            _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            _HISTORY_FILE.write_text(
                json.dumps(self._entries, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass  # Best-effort persistence


# ---------------------------------------------------------------------------
# Terminal session
# ---------------------------------------------------------------------------

class TerminalSession:
    """A single terminal session backed by a PTY (Unix) or piped subprocess (Windows).

    Each session owns its own shell process, output buffer, and state.
    """

    _next_id = 0
    _id_lock = threading.Lock()

    def __init__(
        self,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        rows: int = 24,
        cols: int = 80,
    ) -> None:
        with TerminalSession._id_lock:
            self.id: int = TerminalSession._next_id
            TerminalSession._next_id += 1

        self._shell = shell or _detect_shell()
        self._cwd = cwd or os.getcwd()
        self._env = {**os.environ, **(env or {})}
        self._rows = rows
        self._cols = cols

        self._output_buf: List[str] = []
        self._output_lock = threading.Lock()
        self._exit_status: Optional[int] = None
        self._alive = False

        # PTY fd (Unix) or process handles (Windows)
        self._master_fd: Optional[int] = None
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None

        self._history = CommandHistory()

        self._start()

    # -- lifecycle --

    def _start(self) -> None:
        if _IS_WINDOWS:
            self._start_windows()
        else:
            self._start_unix()

    def _start_unix(self) -> None:
        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd

        # Set initial terminal size
        self._set_pty_size(master_fd, self._rows, self._cols)

        self._process = subprocess.Popen(
            [self._shell, "-i"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=self._cwd,
            env=self._env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        os.close(slave_fd)

        self._alive = True
        self._reader_thread = threading.Thread(
            target=self._read_unix, daemon=True, name=f"TermReader-{self.id}"
        )
        self._reader_thread.start()

    def _start_windows(self) -> None:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        self._process = subprocess.Popen(
            [self._shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self._cwd,
            env=self._env,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        self._alive = True
        self._reader_thread = threading.Thread(
            target=self._read_windows, daemon=True, name=f"TermReader-{self.id}"
        )
        self._reader_thread.start()

    # -- reader threads --

    def _read_unix(self) -> None:
        try:
            while self._alive and self._master_fd is not None:
                try:
                    data = os.read(self._master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                with self._output_lock:
                    self._output_buf.append(text)
        finally:
            self._alive = False
            self._reap()

    def _read_windows(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        try:
            while self._alive:
                chunk = self._process.stdout.read(1)
                if not chunk:
                    break
                # Try to read more if available
                try:
                    avail = self._process.stdout.peek(4095)
                    if avail:
                        chunk += self._process.stdout.read(len(avail))
                except (AttributeError, OSError):
                    pass
                text = chunk.decode("utf-8", errors="replace")
                with self._output_lock:
                    self._output_buf.append(text)
        except (OSError, ValueError):
            pass
        finally:
            self._alive = False
            self._reap()

    # -- PTY helpers --

    @staticmethod
    def _set_pty_size(fd: int, rows: int, cols: int) -> None:
        if _IS_WINDOWS:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    # -- public API --

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def cwd(self) -> str:
        """Best-effort CWD tracking via /proc on Linux."""
        if self._process and not _IS_WINDOWS:
            proc_cwd = f"/proc/{self._process.pid}/cwd"
            try:
                return os.readlink(proc_cwd)
            except OSError:
                pass
        return self._cwd

    @property
    def exit_status(self) -> Optional[int]:
        return self._exit_status

    @property
    def history(self) -> CommandHistory:
        return self._history

    def send_input(self, text: str) -> None:
        """Send raw text to the shell stdin."""
        if not self._alive:
            raise RuntimeError("Session is not alive")
        data = text.encode("utf-8")
        if _IS_WINDOWS:
            assert self._process is not None and self._process.stdin is not None
            self._process.stdin.write(data)
            self._process.stdin.flush()
        else:
            assert self._master_fd is not None
            os.write(self._master_fd, data)

    def execute(self, command: str, timeout: float = 30.0) -> str:
        """Execute *command* synchronously and return its output.

        The command is sent to the running shell and output is captured until
        a sentinel marker appears or the timeout expires.
        """
        if not self._alive:
            raise RuntimeError("Session is not alive")

        self._history.add(command)

        sentinel = f"__EOSTUDIO_DONE_{id(command)}_{time.monotonic_ns()}__"
        # Drain existing output
        self.get_output()

        if _IS_WINDOWS:
            shell_base = os.path.basename(self._shell).lower()
            if "cmd" in shell_base:
                full = f"{command} & echo {sentinel}\r\n"
            else:
                full = f"{command}; echo '{sentinel}'\r\n"
        else:
            full = f"{command}; echo '{sentinel}'\n"

        self.send_input(full)

        # Wait for sentinel in output
        deadline = time.monotonic() + timeout
        collected: List[str] = []
        while time.monotonic() < deadline:
            time.sleep(0.05)
            chunk = self.get_output()
            if chunk:
                collected.append(chunk)
                joined = "".join(collected)
                if sentinel in joined:
                    result = joined.split(sentinel)[0]
                    # Remove the typed command line from output
                    lines = result.split("\n")
                    cmd_stripped = command.strip()
                    out_lines: List[str] = []
                    found_cmd = False
                    for line in lines:
                        stripped = AnsiParser.strip(line).strip()
                        if not found_cmd and (
                            cmd_stripped in stripped
                            or stripped.endswith(cmd_stripped)
                        ):
                            found_cmd = True
                            continue
                        if found_cmd:
                            out_lines.append(line)
                    return "\n".join(out_lines).strip()
            if not self._alive:
                break

        return AnsiParser.strip("".join(collected)).strip()

    def execute_async(
        self,
        command: str,
        callback: Optional[Callable[[str], None]] = None,
    ) -> threading.Thread:
        """Execute *command* asynchronously, invoking *callback* with each chunk.

        Returns the background thread so callers can join() if needed.
        """
        if not self._alive:
            raise RuntimeError("Session is not alive")

        self._history.add(command)

        def _run() -> None:
            sentinel = f"__EOSTUDIO_ASYNC_{id(command)}_{time.monotonic_ns()}__"
            self.get_output()  # drain

            if _IS_WINDOWS:
                shell_base = os.path.basename(self._shell).lower()
                if "cmd" in shell_base:
                    full = f"{command} & echo {sentinel}\r\n"
                else:
                    full = f"{command}; echo '{sentinel}'\r\n"
            else:
                full = f"{command}; echo '{sentinel}'\n"

            self.send_input(full)

            while self._alive:
                time.sleep(0.05)
                chunk = self.get_output()
                if chunk:
                    if sentinel in chunk:
                        chunk = chunk.split(sentinel)[0]
                        if chunk and callback:
                            callback(chunk)
                        break
                    if callback:
                        callback(chunk)

        t = threading.Thread(target=_run, daemon=True, name=f"AsyncExec-{self.id}")
        t.start()
        return t

    def get_output(self) -> str:
        """Return and clear accumulated output."""
        with self._output_lock:
            text = "".join(self._output_buf)
            self._output_buf.clear()
        return text

    def clear(self) -> None:
        """Clear the output buffer."""
        with self._output_lock:
            self._output_buf.clear()

    def resize(self, rows: int, cols: int) -> None:
        """Resize the terminal to *rows* x *cols*."""
        self._rows = rows
        self._cols = cols
        if self._master_fd is not None and not _IS_WINDOWS:
            self._set_pty_size(self._master_fd, rows, cols)

    def kill(self) -> None:
        """Kill the shell process and clean up resources."""
        self._alive = False
        if self._process:
            try:
                if _IS_WINDOWS:
                    self._process.terminate()
                else:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        self._cleanup_fds()
        self._reap()

    def _cleanup_fds(self) -> None:
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    def _reap(self) -> None:
        if self._process:
            try:
                self._process.wait(timeout=2)
                self._exit_status = self._process.returncode
            except subprocess.TimeoutExpired:
                try:
                    self._process.kill()
                    self._process.wait(timeout=2)
                    self._exit_status = self._process.returncode
                except (OSError, subprocess.TimeoutExpired):
                    pass

    def __del__(self) -> None:
        self.kill()


# ---------------------------------------------------------------------------
# Terminal manager
# ---------------------------------------------------------------------------

class TerminalManager:
    """Manages multiple :class:`TerminalSession` instances."""

    def __init__(self) -> None:
        self._sessions: Dict[int, TerminalSession] = {}
        self._active_id: Optional[int] = None
        self._lock = threading.Lock()

    def create_session(
        self,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        rows: int = 24,
        cols: int = 80,
    ) -> TerminalSession:
        """Create and register a new terminal session."""
        session = TerminalSession(shell=shell, cwd=cwd, env=env, rows=rows, cols=cols)
        with self._lock:
            self._sessions[session.id] = session
            if self._active_id is None:
                self._active_id = session.id
        return session

    def get_session(self, session_id: int) -> Optional[TerminalSession]:
        with self._lock:
            return self._sessions.get(session_id)

    @property
    def active_session(self) -> Optional[TerminalSession]:
        with self._lock:
            if self._active_id is not None:
                return self._sessions.get(self._active_id)
        return None

    @active_session.setter
    def active_session(self, session_id: int) -> None:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"No session with id {session_id}")
            self._active_id = session_id

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": s.id,
                    "alive": s.alive,
                    "cwd": s.cwd,
                    "exit_status": s.exit_status,
                }
                for s in self._sessions.values()
            ]

    def close_session(self, session_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.kill()
            if self._active_id == session_id:
                self._active_id = next(iter(self._sessions), None)

    def shutdown(self) -> None:
        """Kill all sessions and clean up."""
        with self._lock:
            for session in self._sessions.values():
                session.kill()
            self._sessions.clear()
            self._active_id = None


# ---------------------------------------------------------------------------
# Backward-compatible TerminalEmulator facade
# ---------------------------------------------------------------------------

class TerminalEmulator:
    """High-level terminal emulator -- backward-compatible public API.

    Wraps a :class:`TerminalManager` and delegates to the active session.
    Legacy callers can use ``execute()``, ``get_output()``, and ``clear()``
    exactly as before.
    """

    def __init__(
        self,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        rows: int = 24,
        cols: int = 80,
    ) -> None:
        self._manager = TerminalManager()
        self._default_session = self._manager.create_session(
            shell=shell, cwd=cwd, rows=rows, cols=cols,
        )

    # -- session proxies --

    @property
    def manager(self) -> TerminalManager:
        return self._manager

    @property
    def session(self) -> TerminalSession:
        s = self._manager.active_session
        if s is None:
            raise RuntimeError("No active terminal session")
        return s

    # -- backward-compatible API --

    def execute(self, command: str, timeout: float = 30.0) -> str:
        """Run *command* synchronously and return its output."""
        return self.session.execute(command, timeout=timeout)

    def get_output(self) -> str:
        """Return accumulated output from the active session."""
        return self.session.get_output()

    def clear(self) -> None:
        """Clear the active session output buffer."""
        self.session.clear()

    # -- extended API --

    def execute_async(
        self,
        command: str,
        callback: Optional[Callable[[str], None]] = None,
    ) -> threading.Thread:
        """Run *command* asynchronously with streaming *callback*."""
        return self.session.execute_async(command, callback)

    def send_input(self, text: str) -> None:
        """Send raw input to the active session PTY."""
        self.session.send_input(text)

    def resize(self, rows: int, cols: int) -> None:
        """Resize the active session terminal."""
        self.session.resize(rows, cols)

    def kill(self) -> None:
        """Kill the active session process."""
        self.session.kill()

    @property
    def cwd(self) -> str:
        return self.session.cwd

    @property
    def exit_status(self) -> Optional[int]:
        return self.session.exit_status

    @property
    def history(self) -> CommandHistory:
        return self.session.history

    @property
    def alive(self) -> bool:
        return self.session.alive

    def shutdown(self) -> None:
        """Shut down all sessions."""
        self._manager.shutdown()

    def __del__(self) -> None:
        try:
            self._manager.shutdown()
        except Exception:
            pass
