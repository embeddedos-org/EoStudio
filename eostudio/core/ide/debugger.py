from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DAPMessage:
    """A Debug Adapter Protocol message (request, response, or event)."""

    seq: int
    type: str  # "request" | "response" | "event"
    command: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    request_seq: Optional[int] = None
    success: Optional[bool] = None
    message: Optional[str] = None
    body: Optional[Dict[str, Any]] = None
    event: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"seq": self.seq, "type": self.type}
        if self.command is not None:
            d["command"] = self.command
        if self.arguments is not None:
            d["arguments"] = self.arguments
        if self.request_seq is not None:
            d["request_seq"] = self.request_seq
        if self.success is not None:
            d["success"] = self.success
        if self.message is not None:
            d["message"] = self.message
        if self.body is not None:
            d["body"] = self.body
        if self.event is not None:
            d["event"] = self.event
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DAPMessage:
        return cls(
            seq=d.get("seq", 0),
            type=d.get("type", ""),
            command=d.get("command"),
            arguments=d.get("arguments"),
            request_seq=d.get("request_seq"),
            success=d.get("success"),
            message=d.get("message"),
            body=d.get("body"),
            event=d.get("event"),
        )

    def encode(self) -> bytes:
        """Encode to DAP wire format (Content-Length framing)."""
        payload = json.dumps(self.to_dict()).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        return header + payload


@dataclass
class Breakpoint:
    """Represents a breakpoint set in the debugger."""

    file: str
    line: int
    condition: Optional[str] = None
    hit_count: Optional[int] = None
    log_message: Optional[str] = None
    enabled: bool = True
    # Populated after verification by the debug adapter
    id: Optional[int] = None
    verified: bool = False


@dataclass
class StackFrame:
    """Represents a single frame in the call stack."""

    id: int
    name: str
    source_path: str
    line: int
    column: int


@dataclass
class Variable:
    """Represents a variable visible during debugging."""

    name: str
    value: str
    type: str = ""
    children: List[Variable] = field(default_factory=list)
    expandable: bool = False
    variables_reference: int = 0


class DebugType(str, Enum):
    PYTHON = "python"
    NODE = "node"
    CPP = "cpp"


@dataclass
class DebugConfig:
    """Configuration for launching a debug session."""

    program: str
    args: List[str] = field(default_factory=list)
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    stop_on_entry: bool = False
    type: str = "python"  # python | node | cpp


# ---------------------------------------------------------------------------
# DAP Transport
# ---------------------------------------------------------------------------

class _DAPTransport:
    """Handles DAP JSON messaging over stdio with Content-Length framing."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._seq = 0
        self._lock = threading.Lock()
        self._pending: Dict[int, threading.Event] = {}
        self._responses: Dict[int, DAPMessage] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._event_handlers: Dict[str, List[Callable[[DAPMessage], None]]] = {}
        self._socket: Optional[socket.socket] = None
        self._socket_rfile: Optional[Any] = None
        self._socket_wfile: Optional[Any] = None

    # -- connection lifecycle ------------------------------------------------

    def start_process(self, cmd: List[str], cwd: Optional[str] = None,
                      env: Optional[Dict[str, str]] = None) -> None:
        merged_env: Optional[Dict[str, str]] = None
        if env:
            merged_env = {**os.environ, **env}

        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=merged_env,
        )
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._reader_thread.start()

    def connect_socket(self, host: str, port: int, timeout: float = 10.0) -> None:
        """Connect to a debug adapter via TCP socket."""
        deadline = time.monotonic() + timeout
        sock: Optional[socket.socket] = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(max(0.5, deadline - time.monotonic()))
                sock.connect((host, port))
                break
            except OSError:
                if sock:
                    sock.close()
                    sock = None
                time.sleep(0.25)
        if sock is None:
            raise ConnectionError(f"Cannot connect to {host}:{port}")
        self._socket = sock
        self._socket_rfile = sock.makefile("rb")
        self._socket_wfile = sock.makefile("wb")
        self._running = True
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True
        )
        self._reader_thread.start()

    def shutdown(self) -> None:
        self._running = False
        if self._process:
            try:
                if self._process.stdin:
                    self._process.stdin.close()
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            self._socket_rfile = None
            self._socket_wfile = None
        # Wake any pending requests
        for evt in self._pending.values():
            evt.set()
        self._pending.clear()
        self._responses.clear()

    # -- sending / receiving -------------------------------------------------

    def _next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def send_request(self, command: str,
                     arguments: Optional[Dict[str, Any]] = None,
                     timeout: float = 30.0) -> DAPMessage:
        seq = self._next_seq()
        msg = DAPMessage(
            seq=seq, type="request", command=command, arguments=arguments
        )
        event = threading.Event()
        self._pending[seq] = event
        self._write(msg.encode())
        if not event.wait(timeout=timeout):
            self._pending.pop(seq, None)
            return DAPMessage(
                seq=0, type="response", request_seq=seq,
                success=False, command=command,
                message="Request timed out",
            )
        return self._responses.pop(seq, DAPMessage(
            seq=0, type="response", request_seq=seq,
            success=False, command=command, message="No response",
        ))

    def _write(self, data: bytes) -> None:
        try:
            if self._socket_wfile:
                self._socket_wfile.write(data)
                self._socket_wfile.flush()
            elif self._process and self._process.stdin:
                self._process.stdin.write(data)
                self._process.stdin.flush()
        except Exception:
            pass

    def _read_loop(self) -> None:
        while self._running:
            try:
                msg = self._read_message()
                if msg is None:
                    break
                self._dispatch(msg)
            except Exception:
                if self._running:
                    continue
                break

    def _read_message(self) -> Optional[DAPMessage]:
        stream = self._socket_rfile if self._socket_rfile else (
            self._process.stdout if self._process else None
        )
        if stream is None:
            return None

        headers: Dict[str, str] = {}
        while True:
            raw_line = stream.readline()
            if not raw_line:
                return None
            line = raw_line.decode("ascii", errors="replace").strip()
            if not line:
                break
            if ":" in line:
                key, _, val = line.partition(":")
                headers[key.strip().lower()] = val.strip()

        length_str = headers.get("content-length")
        if not length_str:
            return None
        try:
            length = int(length_str)
        except ValueError:
            return None

        body = b""
        while len(body) < length:
            chunk = stream.read(length - len(body))
            if not chunk:
                return None
            body += chunk

        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return DAPMessage.from_dict(data)

    def _dispatch(self, msg: DAPMessage) -> None:
        if msg.type == "response" and msg.request_seq is not None:
            self._responses[msg.request_seq] = msg
            evt = self._pending.pop(msg.request_seq, None)
            if evt:
                evt.set()
        elif msg.type == "event":
            event_name = msg.event or ""
            for handler in self._event_handlers.get(event_name, []):
                try:
                    handler(msg)
                except Exception:
                    pass
            for handler in self._event_handlers.get("*", []):
                try:
                    handler(msg)
                except Exception:
                    pass

    # -- event subscription --------------------------------------------------

    def on_event(self, event: str, handler: Callable[[DAPMessage], None]) -> None:
        self._event_handlers.setdefault(event, []).append(handler)


# ---------------------------------------------------------------------------
# Debug adapter auto-detection helpers
# ---------------------------------------------------------------------------

def _find_executable(name: str) -> Optional[str]:
    return shutil.which(name)


def _build_adapter_command(config: DebugConfig) -> Tuple[List[str], Optional[Dict[str, str]]]:
    """Return (command, env) to launch the appropriate debug adapter."""

    debug_type = config.type.lower()
    env: Optional[Dict[str, str]] = config.env

    if debug_type == "python":
        python = _find_executable("python3") or _find_executable("python") or sys.executable
        return [python, "-m", "debugpy.adapter"], env

    if debug_type == "node":
        node_dap = _find_executable("js-debug-adapter")
        if node_dap:
            return [node_dap], env
        node = _find_executable("node") or "node"
        return [node, "--inspect-brk", config.program], env

    if debug_type == "cpp":
        # Prefer lldb-vscode / lldb-dap; fall back to gdb with MI adapter
        for name in ("lldb-dap", "lldb-vscode"):
            exe = _find_executable(name)
            if exe:
                return [exe], env
        gdb = _find_executable("gdb")
        if gdb:
            return [gdb, "--interpreter=dap"], env
        raise RuntimeError("No C/C++ debug adapter found (need lldb-dap or gdb >= 14)")

    raise ValueError(f"Unsupported debug type: {debug_type}")


# ---------------------------------------------------------------------------
# Debugger
# ---------------------------------------------------------------------------

class Debugger:
    """Full-featured DAP-based debugger for EoStudio.

    Backward-compatible with the original stub API while exposing the
    complete Debug Adapter Protocol feature set.
    """

    def __init__(self) -> None:
        self._transport: Optional[_DAPTransport] = None
        self._running = False
        self._initialized = False
        self._breakpoints: Dict[str, List[Breakpoint]] = {}  # file -> [bp]
        self._watches: List[str] = []
        self._config: Optional[DebugConfig] = None
        self._stopped_thread_id: Optional[int] = None
        self._capabilities: Dict[str, Any] = {}
        self._lock = threading.Lock()

        # Public callbacks -- users can assign their own handlers
        self.on_stopped: Optional[Callable[[DAPMessage], None]] = None
        self.on_terminated: Optional[Callable[[DAPMessage], None]] = None
        self.on_output: Optional[Callable[[str, str], None]] = None
        self.on_breakpoint_event: Optional[Callable[[DAPMessage], None]] = None
        self.on_thread_event: Optional[Callable[[DAPMessage], None]] = None
        self.on_exited: Optional[Callable[[int], None]] = None

    # -- internal helpers ----------------------------------------------------

    def _setup_event_handlers(self) -> None:
        assert self._transport is not None
        self._transport.on_event("stopped", self._handle_stopped)
        self._transport.on_event("terminated", self._handle_terminated)
        self._transport.on_event("exited", self._handle_exited)
        self._transport.on_event("output", self._handle_output)
        self._transport.on_event("breakpoint", self._handle_breakpoint_event)
        self._transport.on_event("thread", self._handle_thread_event)

    def _handle_stopped(self, msg: DAPMessage) -> None:
        body = msg.body or {}
        self._stopped_thread_id = body.get("threadId")
        if self.on_stopped:
            self.on_stopped(msg)

    def _handle_terminated(self, msg: DAPMessage) -> None:
        self._running = False
        if self.on_terminated:
            self.on_terminated(msg)

    def _handle_exited(self, msg: DAPMessage) -> None:
        body = msg.body or {}
        code = body.get("exitCode", -1)
        if self.on_exited:
            self.on_exited(code)

    def _handle_output(self, msg: DAPMessage) -> None:
        body = msg.body or {}
        category = body.get("category", "console")
        text = body.get("output", "")
        if self.on_output:
            self.on_output(category, text)

    def _handle_breakpoint_event(self, msg: DAPMessage) -> None:
        if self.on_breakpoint_event:
            self.on_breakpoint_event(msg)

    def _handle_thread_event(self, msg: DAPMessage) -> None:
        if self.on_thread_event:
            self.on_thread_event(msg)

    def _request(self, command: str,
                 arguments: Optional[Dict[str, Any]] = None,
                 timeout: float = 30.0) -> DAPMessage:
        if not self._transport:
            return DAPMessage(seq=0, type="response", success=False,
                              command=command, message="No active session")
        return self._transport.send_request(command, arguments, timeout=timeout)

    def _initialize(self) -> bool:
        resp = self._request("initialize", {
            "clientID": "eostudio",
            "clientName": "EoStudio",
            "adapterID": self._config.type if self._config else "python",
            "pathFormat": "path",
            "linesStartAt1": True,
            "columnsStartAt1": True,
            "supportsVariableType": True,
            "supportsVariablePaging": False,
            "supportsRunInTerminalRequest": False,
            "supportsProgressReporting": False,
            "supportsInvalidatedEvent": False,
            "supportsMemoryReferences": False,
            "locale": "en-US",
        })
        if not resp.success:
            return False
        self._capabilities = resp.body or {}
        self._initialized = True
        return True

    def _send_breakpoints_for_file(self, file: str) -> None:
        bps = self._breakpoints.get(file, [])
        source_bps = []
        for bp in bps:
            if not bp.enabled:
                continue
            entry: Dict[str, Any] = {"line": bp.line}
            if bp.condition:
                entry["condition"] = bp.condition
            if bp.hit_count is not None:
                entry["hitCondition"] = str(bp.hit_count)
            if bp.log_message:
                entry["logMessage"] = bp.log_message
            source_bps.append(entry)

        resp = self._request("setBreakpoints", {
            "source": {"path": file},
            "breakpoints": source_bps,
        })

        if resp.success and resp.body:
            returned = resp.body.get("breakpoints", [])
            enabled_bps = [b for b in bps if b.enabled]
            for idx, rbp in enumerate(returned):
                if idx < len(enabled_bps):
                    enabled_bps[idx].verified = rbp.get("verified", False)
                    enabled_bps[idx].id = rbp.get("id")
                    if "line" in rbp:
                        enabled_bps[idx].line = rbp["line"]

    def _send_all_breakpoints(self) -> None:
        for file in list(self._breakpoints.keys()):
            self._send_breakpoints_for_file(file)

    def _do_launch(self, config: DebugConfig) -> bool:
        self._config = config
        cmd, env = _build_adapter_command(config)

        transport = _DAPTransport()
        try:
            transport.start_process(cmd, cwd=config.cwd, env=env)
        except Exception:
            return False
        self._transport = transport
        self._setup_event_handlers()

        if not self._initialize():
            self.stop()
            return False

        launch_args: Dict[str, Any] = {
            "program": config.program,
            "stopOnEntry": config.stop_on_entry,
            "noDebug": False,
        }
        if config.args:
            launch_args["args"] = config.args
        if config.cwd:
            launch_args["cwd"] = config.cwd
        if config.env:
            launch_args["env"] = config.env

        # Adapter-specific tweaks
        if config.type == "python":
            launch_args["type"] = "debugpy"
            launch_args["request"] = "launch"
            launch_args["justMyCode"] = True
        elif config.type == "node":
            launch_args["type"] = "pwa-node"
            launch_args["request"] = "launch"
        elif config.type == "cpp":
            launch_args["type"] = "cppdbg"
            launch_args["request"] = "launch"
            launch_args["MIMode"] = "gdb"

        resp = self._request("launch", launch_args, timeout=30)
        if not resp.success:
            self.stop()
            return False

        self._running = True
        self._send_all_breakpoints()
        self._request("configurationDone")
        return True

    # -- public API (backward-compatible) ------------------------------------

    def start(self, path: str) -> bool:
        """Launch a debug session for the given file (backward-compatible).

        Infers the debug type from the file extension.
        """
        ext = Path(path).suffix.lower()
        if ext in (".js", ".mjs", ".cjs", ".ts"):
            dtype = "node"
        elif ext in (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"):
            dtype = "cpp"
        else:
            dtype = "python"

        config = DebugConfig(
            program=str(Path(path).resolve()),
            cwd=str(Path(path).resolve().parent),
            type=dtype,
        )
        return self.launch(config)

    def launch(self, config: DebugConfig) -> bool:
        """Launch a debug session with a full configuration."""
        if self._running:
            self.stop()
        return self._do_launch(config)

    def attach(self, host: str, port: int) -> bool:
        """Attach to a running debug adapter via TCP."""
        if self._running:
            self.stop()

        transport = _DAPTransport()
        try:
            transport.connect_socket(host, port)
        except ConnectionError:
            return False

        self._transport = transport
        self._config = DebugConfig(program="", type="python")
        self._setup_event_handlers()

        if not self._initialize():
            self.stop()
            return False

        resp = self._request("attach", {
            "type": "debugpy",
            "request": "attach",
        })
        if not resp.success:
            self.stop()
            return False

        self._running = True
        self._send_all_breakpoints()
        self._request("configurationDone")
        return True

    def stop(self) -> None:
        """Terminate the debug session."""
        if self._transport:
            try:
                self._request("disconnect", {"restart": False, "terminateDebuggee": True}, timeout=5)
            except Exception:
                pass
            self._transport.shutdown()
            self._transport = None
        self._running = False
        self._initialized = False
        self._stopped_thread_id = None

    def is_running(self) -> bool:
        return self._running

    # -- execution control ---------------------------------------------------

    def continue_execution(self) -> None:
        tid = self._stopped_thread_id or 0
        self._request("continue", {"threadId": tid})
        self._stopped_thread_id = None

    def pause(self) -> None:
        tid = self._stopped_thread_id or 0
        self._request("pause", {"threadId": tid})

    def step_over(self) -> None:
        tid = self._stopped_thread_id or 0
        self._request("next", {"threadId": tid})

    def step_into(self) -> None:
        tid = self._stopped_thread_id or 0
        self._request("stepIn", {"threadId": tid})

    def step_out(self) -> None:
        tid = self._stopped_thread_id or 0
        self._request("stepOut", {"threadId": tid})

    # -- breakpoints ---------------------------------------------------------

    def add_breakpoint(self, file: str, line: int) -> None:
        """Add a breakpoint (backward-compatible, no return value)."""
        self.set_breakpoint(file, line)

    def remove_breakpoint(self, file: str, line: int) -> None:
        """Remove a breakpoint (backward-compatible)."""
        file = str(Path(file).resolve())
        bps = self._breakpoints.get(file, [])
        self._breakpoints[file] = [b for b in bps if b.line != line]
        if not self._breakpoints[file]:
            del self._breakpoints[file]
        if self._running:
            self._send_breakpoints_for_file(file)

    def set_breakpoint(self, file: str, line: int,
                       condition: Optional[str] = None,
                       log_message: Optional[str] = None) -> Breakpoint:
        """Set a breakpoint with optional condition / log message."""
        file = str(Path(file).resolve())
        bp = Breakpoint(file=file, line=line, condition=condition,
                        log_message=log_message, enabled=True)
        self._breakpoints.setdefault(file, []).append(bp)
        if self._running:
            self._send_breakpoints_for_file(file)
        return bp

    def get_breakpoints(self) -> List[Breakpoint]:
        """Return all breakpoints across all files."""
        result: List[Breakpoint] = []
        for bps in self._breakpoints.values():
            result.extend(bps)
        return result

    # -- stack & variables ---------------------------------------------------

    def get_stack_trace(self, thread_id: Optional[int] = None) -> List[StackFrame]:
        tid = thread_id or self._stopped_thread_id or 0
        resp = self._request("stackTrace", {
            "threadId": tid,
            "startFrame": 0,
            "levels": 100,
        })
        frames: List[StackFrame] = []
        if resp.success and resp.body:
            for f in resp.body.get("stackFrames", []):
                source = f.get("source", {})
                frames.append(StackFrame(
                    id=f.get("id", 0),
                    name=f.get("name", ""),
                    source_path=source.get("path", ""),
                    line=f.get("line", 0),
                    column=f.get("column", 0),
                ))
        return frames

    def get_scopes(self, frame_id: int) -> List[Dict[str, Any]]:
        resp = self._request("scopes", {"frameId": frame_id})
        if resp.success and resp.body:
            return resp.body.get("scopes", [])
        return []

    def get_variables(self, frame_id: int) -> List[Variable]:
        """Get variables visible in the given stack frame.

        Fetches scopes first, then retrieves variables for each scope.
        """
        scopes = self.get_scopes(frame_id)
        result: List[Variable] = []
        for scope in scopes:
            ref = scope.get("variablesReference", 0)
            if ref:
                result.extend(self._fetch_variables(ref))
        return result

    def _fetch_variables(self, variables_reference: int) -> List[Variable]:
        resp = self._request("variables", {
            "variablesReference": variables_reference,
        })
        result: List[Variable] = []
        if resp.success and resp.body:
            for v in resp.body.get("variables", []):
                var_ref = v.get("variablesReference", 0)
                result.append(Variable(
                    name=v.get("name", ""),
                    value=v.get("value", ""),
                    type=v.get("type", ""),
                    expandable=var_ref > 0,
                    variables_reference=var_ref,
                ))
        return result

    def expand_variable(self, variables_reference: int) -> List[Variable]:
        """Expand a compound variable to get its children."""
        return self._fetch_variables(variables_reference)

    # -- threads -------------------------------------------------------------

    def get_threads(self) -> List[Dict[str, Any]]:
        resp = self._request("threads")
        if resp.success and resp.body:
            return resp.body.get("threads", [])
        return []

    # -- evaluation ----------------------------------------------------------

    def evaluate(self, expression: str,
                 frame_id: Optional[int] = None) -> str:
        """Evaluate an expression in the debug console."""
        args: Dict[str, Any] = {
            "expression": expression,
            "context": "repl",
        }
        if frame_id is not None:
            args["frameId"] = frame_id
        resp = self._request("evaluate", args)
        if resp.success and resp.body:
            return resp.body.get("result", "")
        return resp.message or ""

    # -- watch expressions ---------------------------------------------------

    def set_watch(self, expression: str) -> None:
        """Add a watch expression."""
        if expression not in self._watches:
            self._watches.append(expression)

    def remove_watch(self, expression: str) -> None:
        """Remove a watch expression."""
        try:
            self._watches.remove(expression)
        except ValueError:
            pass

    def get_watches(self) -> List[Dict[str, Any]]:
        """Evaluate all watch expressions and return results."""
        frame_id: Optional[int] = None
        if self._stopped_thread_id is not None:
            frames = self.get_stack_trace(self._stopped_thread_id)
            if frames:
                frame_id = frames[0].id

        results: List[Dict[str, Any]] = []
        for expr in self._watches:
            args: Dict[str, Any] = {
                "expression": expr,
                "context": "watch",
            }
            if frame_id is not None:
                args["frameId"] = frame_id
            resp = self._request("evaluate", args)
            if resp.success and resp.body:
                results.append({
                    "expression": expr,
                    "result": resp.body.get("result", ""),
                    "type": resp.body.get("type", ""),
                    "variablesReference": resp.body.get("variablesReference", 0),
                })
            else:
                results.append({
                    "expression": expr,
                    "result": resp.message or "<error>",
                    "type": "",
                    "variablesReference": 0,
                })
        return results


# ---------------------------------------------------------------------------
# DebugManager
# ---------------------------------------------------------------------------

class DebugManager:
    """Manages multiple debug sessions for EoStudio."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Debugger] = {}
        self._active_id: Optional[str] = None
        self._counter = 0
        self._lock = threading.Lock()

    def _generate_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"session-{self._counter}"

    @property
    def active_session(self) -> Optional[Debugger]:
        if self._active_id:
            return self._sessions.get(self._active_id)
        return None

    def create_session(self, session_id: Optional[str] = None) -> Tuple[str, Debugger]:
        """Create a new debug session and return (id, debugger)."""
        sid = session_id or self._generate_id()
        debugger = Debugger()
        self._sessions[sid] = debugger
        if self._active_id is None:
            self._active_id = sid
        return sid, debugger

    def get_session(self, session_id: str) -> Optional[Debugger]:
        return self._sessions.get(session_id)

    def set_active(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._active_id = session_id
            return True
        return False

    def stop_session(self, session_id: str) -> None:
        debugger = self._sessions.pop(session_id, None)
        if debugger:
            debugger.stop()
        if self._active_id == session_id:
            self._active_id = next(iter(self._sessions), None)

    def stop_all(self) -> None:
        for debugger in self._sessions.values():
            debugger.stop()
        self._sessions.clear()
        self._active_id = None

    def list_sessions(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for sid, debugger in self._sessions.items():
            result.append({
                "id": sid,
                "running": debugger.is_running(),
                "active": sid == self._active_id,
            })
        return result

    def launch(self, config: DebugConfig,
               session_id: Optional[str] = None) -> Tuple[str, bool]:
        """Create a session and launch with the given config."""
        sid, debugger = self.create_session(session_id)
        ok = debugger.launch(config)
        if not ok:
            self.stop_session(sid)
        return sid, ok

    def attach(self, host: str, port: int,
               session_id: Optional[str] = None) -> Tuple[str, bool]:
        """Create a session and attach to a running process."""
        sid, debugger = self.create_session(session_id)
        ok = debugger.attach(host, port)
        if not ok:
            self.stop_session(sid)
        return sid, ok
