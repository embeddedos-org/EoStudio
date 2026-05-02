"""
Language Server Protocol client implementation for EoStudio.

Provides a full LSP client using JSON-RPC over stdio, supporting completion,
hover, go-to-definition, references, rename, formatting, and diagnostics.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LSPMessage:
    """Represents a JSON-RPC 2.0 message used by the Language Server Protocol."""

    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"jsonrpc": "2.0"}
        if self.id is not None:
            msg["id"] = self.id
        if self.method is not None:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error
        return msg

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> LSPMessage:
        return LSPMessage(
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class LSPConfig:
    """Configuration for a language server."""

    language: str
    command: List[str]
    initialization_options: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Default server configurations
# ---------------------------------------------------------------------------

_DEFAULT_CONFIGS: Dict[str, LSPConfig] = {
    "python": LSPConfig(
        language="python",
        command=["pyright-langserver", "--stdio"],
    ),
    "pylsp": LSPConfig(
        language="python",
        command=["pylsp"],
    ),
    "javascript": LSPConfig(
        language="javascript",
        command=["typescript-language-server", "--stdio"],
    ),
    "typescript": LSPConfig(
        language="typescript",
        command=["typescript-language-server", "--stdio"],
    ),
    "c": LSPConfig(
        language="c",
        command=["clangd"],
    ),
    "cpp": LSPConfig(
        language="cpp",
        command=["clangd"],
    ),
    "rust": LSPConfig(
        language="rust",
        command=["rust-analyzer"],
    ),
    "go": LSPConfig(
        language="go",
        command=["gopls", "serve"],
    ),
    "java": LSPConfig(
        language="java",
        command=["jdtls"],
    ),
}


def get_config(language: str) -> LSPConfig:
    """Return the default LSPConfig for *language*, raising ValueError if unknown."""
    key = language.lower()
    if key in _DEFAULT_CONFIGS:
        return _DEFAULT_CONFIGS[key]
    raise ValueError(
        f"No default language-server configuration for '{language}'. "
        f"Known languages: {', '.join(sorted(_DEFAULT_CONFIGS))}"
    )


# ---------------------------------------------------------------------------
# LanguageServer - full LSP client
# ---------------------------------------------------------------------------


class LanguageServer:
    """LSP client that communicates with a language server over stdio.

    Backward-compatible with the original stub interface while exposing the
    full set of LSP operations required by EoStudio.
    """

    def __init__(
        self,
        language: str = "python",
        workspace_path: str = ".",
        config: Optional[LSPConfig] = None,
    ) -> None:
        self.language = language
        self.workspace_path = os.path.abspath(workspace_path)
        self.config = config or get_config(language)

        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._id_lock = threading.Lock()

        # Response routing: request-id -> threading.Event + storage
        self._pending: Dict[int, threading.Event] = {}
        self._responses: Dict[int, Dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

        # Diagnostics received asynchronously from the server
        self._diagnostics: Dict[str, List[Dict[str, Any]]] = {}
        self._diagnostics_lock = threading.Lock()

        # Version tracking for open documents
        self._document_versions: Dict[str, int] = {}

        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._write_lock = threading.Lock()

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Launch the language server subprocess and initialize the session."""
        if self.is_running():
            return

        self._stop_event.clear()
        try:
            self._process = subprocess.Popen(
                self.config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Language server command not found: {self.config.command}. "
                "Make sure the server is installed and on your PATH."
            )

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="lsp-reader"
        )
        self._reader_thread.start()

        self.initialize()
        self.initialized()

    def stop(self) -> None:
        """Gracefully shut down the language server."""
        if not self.is_running():
            return

        try:
            self._send_request("shutdown", params=None)
        except Exception:
            logger.debug("shutdown request failed", exc_info=True)

        try:
            self._send_notification("exit")
        except Exception:
            logger.debug("exit notification failed", exc_info=True)

        self._stop_event.set()

        if self._process is not None:
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
            self._process = None

        if self._reader_thread is not None:
            self._reader_thread.join(timeout=3)
            self._reader_thread = None

        with self._pending_lock:
            for evt in self._pending.values():
                evt.set()
            self._pending.clear()
            self._responses.clear()

    def is_running(self) -> bool:
        """Return True if the language server process is alive."""
        return self._process is not None and self._process.poll() is None

    # -- JSON-RPC transport --------------------------------------------------

    def _next_id(self) -> int:
        with self._id_lock:
            self._request_id += 1
            return self._request_id

    def _send_message(self, msg: LSPMessage) -> None:
        """Encode and write a JSON-RPC message with Content-Length framing."""
        body = json.dumps(msg.to_dict(), separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        with self._write_lock:
            if self._process is None or self._process.stdin is None:
                raise RuntimeError("Language server is not running.")
            self._process.stdin.write(header + body)
            self._process.stdin.flush()

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read one JSON-RPC message from the server stdout (blocking)."""
        if self._process is None or self._process.stdout is None:
            return None

        stdout = self._process.stdout
        content_length = -1

        # Read headers
        while True:
            line = stdout.readline()
            if not line:
                return None  # EOF
            line_str = line.decode("ascii", errors="replace").strip()
            if not line_str:
                break  # End of headers
            if line_str.lower().startswith("content-length:"):
                content_length = int(line_str.split(":", 1)[1].strip())

        if content_length < 0:
            return None

        body = b""
        while len(body) < content_length:
            chunk = stdout.read(content_length - len(body))
            if not chunk:
                return None
            body += chunk

        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON-RPC body: %s", body[:200])
            return None

    # -- background reader ---------------------------------------------------

    def _reader_loop(self) -> None:
        """Background thread: read messages and dispatch responses/notifications."""
        while not self._stop_event.is_set():
            try:
                msg = self._read_message()
            except Exception:
                if self._stop_event.is_set():
                    break
                logger.debug("reader error", exc_info=True)
                break

            if msg is None:
                break

            msg_id = msg.get("id")

            # Server notification (no id)
            if msg_id is None:
                self._handle_notification(msg)
                continue

            # Response to a request we sent
            with self._pending_lock:
                if msg_id in self._pending:
                    self._responses[msg_id] = msg
                    self._pending[msg_id].set()

    def _handle_notification(self, msg: Dict[str, Any]) -> None:
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri", "")
            diags = params.get("diagnostics", [])
            with self._diagnostics_lock:
                self._diagnostics[uri] = diags
        elif method == "window/logMessage":
            text = params.get("message", "")
            logger.debug("LSP log: %s", text)

    # -- request / notification helpers --------------------------------------

    def _send_request(
        self,
        method: str,
        params: Any = None,
        timeout: float = 30.0,
    ) -> Any:
        """Send a JSON-RPC request and wait for the response."""
        rid = self._next_id()
        event = threading.Event()

        with self._pending_lock:
            self._pending[rid] = event

        msg = LSPMessage(id=rid, method=method, params=params)
        self._send_message(msg)

        if not event.wait(timeout=timeout):
            with self._pending_lock:
                self._pending.pop(rid, None)
                self._responses.pop(rid, None)
            raise TimeoutError(
                f"LSP request '{method}' (id={rid}) timed out"
            )

        with self._pending_lock:
            self._pending.pop(rid, None)
            response = self._responses.pop(rid, {})

        if "error" in response:
            err = response["error"]
            raise RuntimeError(
                f"LSP error [{err.get('code')}]: {err.get('message')}"
            )
        return response.get("result")

    def _send_notification(self, method: str, params: Any = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        msg = LSPMessage(method=method, params=params)
        self._send_message(msg)

    # -- LSP lifecycle requests ----------------------------------------------

    def initialize(self) -> Dict[str, Any]:
        """Send the ``initialize`` request with client capabilities."""
        params = {
            "processId": os.getpid(),
            "rootUri": self._path_to_uri(self.workspace_path),
            "rootPath": self.workspace_path,
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": True,
                            "documentationFormat": [
                                "plaintext",
                                "markdown",
                            ],
                        },
                    },
                    "hover": {
                        "contentFormat": ["plaintext", "markdown"],
                    },
                    "definition": {},
                    "references": {},
                    "rename": {
                        "prepareSupport": True,
                    },
                    "formatting": {},
                    "publishDiagnostics": {
                        "relatedInformation": True,
                    },
                    "synchronization": {
                        "didSave": True,
                        "willSave": False,
                        "willSaveWaitUntil": False,
                    },
                },
                "workspace": {
                    "workspaceFolders": True,
                    "configuration": True,
                },
            },
            "workspaceFolders": [
                {
                    "uri": self._path_to_uri(self.workspace_path),
                    "name": os.path.basename(self.workspace_path),
                }
            ],
        }
        if self.config.initialization_options:
            params["initializationOptions"] = (
                self.config.initialization_options
            )
        result = self._send_request("initialize", params)
        return result or {}

    def initialized(self) -> None:
        """Send the ``initialized`` notification."""
        self._send_notification("initialized", {})

    # -- document synchronization --------------------------------------------

    def did_open(self, uri: str, language_id: str, text: str) -> None:
        """Notify the server that a document was opened."""
        self._document_versions[uri] = 1
        self._send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": text,
                }
            },
        )

    def did_change(self, uri: str, text: str) -> None:
        """Notify the server that a document changed (full sync)."""
        version = self._document_versions.get(uri, 0) + 1
        self._document_versions[uri] = version
        self._send_notification(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": version},
                "contentChanges": [{"text": text}],
            },
        )

    def did_save(self, uri: str) -> None:
        """Notify the server that a document was saved."""
        self._send_notification(
            "textDocument/didSave",
            {"textDocument": {"uri": uri}},
        )

    def did_close(self, uri: str) -> None:
        """Notify the server that a document was closed."""
        self._document_versions.pop(uri, None)
        self._send_notification(
            "textDocument/didClose",
            {"textDocument": {"uri": uri}},
        )

    # -- LSP features --------------------------------------------------------

    def complete(
        self,
        source: str,
        line: int,
        column: int,
        uri: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Request completions at a position.

        This method is backward-compatible with the original stub: it accepts
        *source* text and a position.  When *uri* is ``None`` a temporary
        document URI is synthesized.
        """
        if uri is None:
            uri = self._path_to_uri(
                os.path.join(self.workspace_path, "__eostudio_tmp__.py")
            )
            self.did_open(uri, self.language, source)

        result = self._send_request(
            "textDocument/completion",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": column},
            },
        )
        if result is None:
            return []
        items = (
            result
            if isinstance(result, list)
            else result.get("items", [])
        )
        return [
            {
                "label": item.get("label", ""),
                "kind": item.get("kind"),
                "detail": item.get("detail", ""),
                "documentation": _extract_documentation(
                    item.get("documentation")
                ),
                "insertText": (
                    item.get("insertText") or item.get("label", "")
                ),
            }
            for item in items
        ]

    def hover(
        self, uri: str, line: int, character: int
    ) -> Dict[str, Any]:
        """Request hover information at a position."""
        result = self._send_request(
            "textDocument/hover",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            },
        )
        if result is None:
            return {}
        contents = result.get("contents", "")
        return {
            "contents": _extract_documentation(contents),
            "range": result.get("range"),
        }

    def definition(
        self, uri: str, line: int, character: int
    ) -> List[Dict[str, Any]]:
        """Request go-to-definition at a position."""
        result = self._send_request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            },
        )
        return _normalize_locations(result)

    def references(
        self, uri: str, line: int, character: int
    ) -> List[Dict[str, Any]]:
        """Request find-references at a position."""
        result = self._send_request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": True},
            },
        )
        return _normalize_locations(result)

    def rename(
        self, uri: str, line: int, character: int, new_name: str
    ) -> Dict[str, Any]:
        """Request a rename refactoring."""
        result = self._send_request(
            "textDocument/rename",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "newName": new_name,
            },
        )
        if result is None:
            return {}
        return result

    def formatting(self, uri: str) -> List[Dict[str, Any]]:
        """Request document formatting."""
        result = self._send_request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": uri},
                "options": {"tabSize": 4, "insertSpaces": True},
            },
        )
        return result if isinstance(result, list) else []

    def diagnostics(
        self, source: str, uri: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return the latest diagnostics for a document.

        Backward-compatible: accepts raw *source* text.  If the document has
        not been opened yet it will be opened automatically so the server can
        analyse it.
        """
        if uri is None:
            uri = self._path_to_uri(
                os.path.join(self.workspace_path, "__eostudio_tmp__.py")
            )
            self.did_open(uri, self.language, source)
        else:
            self.did_change(uri, source)

        # Give the server a moment to publish diagnostics
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            with self._diagnostics_lock:
                if uri in self._diagnostics:
                    diags = self._diagnostics[uri]
                    return [
                        {
                            "range": d.get("range"),
                            "severity": d.get("severity"),
                            "message": d.get("message", ""),
                            "source": d.get("source", ""),
                            "code": d.get("code"),
                        }
                        for d in diags
                    ]
            time.sleep(0.1)
        return []

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _path_to_uri(path: str) -> str:
        """Convert a filesystem path to a ``file://`` URI."""
        abspath = os.path.abspath(path)
        # On Windows, drive letters need special handling
        if os.name == "nt":
            abspath = abspath.replace("\\", "/")
            if abspath[0] != "/":
                abspath = "/" + abspath
        return "file://" + abspath

    @staticmethod
    def uri_to_path(uri: str) -> str:
        """Convert a ``file://`` URI back to a filesystem path."""
        if uri.startswith("file:///") and os.name == "nt":
            return uri[8:].replace("/", "\\")
        if uri.startswith("file://"):
            return uri[7:]
        return uri


# ---------------------------------------------------------------------------
# LanguageServerManager
# ---------------------------------------------------------------------------


class LanguageServerManager:
    """Manages multiple LanguageServer instances keyed by language."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = os.path.abspath(workspace_path)
        self._servers: Dict[str, LanguageServer] = {}
        self._lock = threading.Lock()

    def get(self, language: str) -> LanguageServer:
        """Return a running LanguageServer for *language*, starting one if needed."""
        key = language.lower()
        with self._lock:
            server = self._servers.get(key)
            if server is not None and server.is_running():
                return server
            server = LanguageServer(
                language=key, workspace_path=self.workspace_path
            )
            server.start()
            self._servers[key] = server
            return server

    def stop(self, language: str) -> None:
        """Stop the server for *language* if it is running."""
        key = language.lower()
        with self._lock:
            server = self._servers.pop(key, None)
        if server is not None:
            server.stop()

    def stop_all(self) -> None:
        """Stop every managed server."""
        with self._lock:
            servers = list(self._servers.values())
            self._servers.clear()
        for server in servers:
            try:
                server.stop()
            except Exception:
                logger.debug("Error stopping server", exc_info=True)

    def running_languages(self) -> List[str]:
        """Return a list of languages with running servers."""
        with self._lock:
            return [
                k for k, v in self._servers.items() if v.is_running()
            ]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _extract_documentation(doc: Any) -> str:
    """Extract plain-text documentation from an LSP MarkupContent or string."""
    if doc is None:
        return ""
    if isinstance(doc, str):
        return doc
    if isinstance(doc, dict):
        return doc.get("value", "")
    if isinstance(doc, list):
        parts = []
        for item in doc:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("value", ""))
        return "\n".join(parts)
    return str(doc)


def _normalize_locations(result: Any) -> List[Dict[str, Any]]:
    """Normalise definition/references results into a list of location dicts."""
    if result is None:
        return []
    if isinstance(result, dict):
        result = [result]
    if not isinstance(result, list):
        return []
    locations: List[Dict[str, Any]] = []
    for item in result:
        loc: Dict[str, Any] = {}
        if "uri" in item:
            loc["uri"] = item["uri"]
            loc["range"] = item.get("range")
        elif "targetUri" in item:
            # LocationLink
            loc["uri"] = item["targetUri"]
            loc["range"] = (
                item.get("targetSelectionRange")
                or item.get("targetRange")
            )
        else:
            continue
        locations.append(loc)
    return locations
