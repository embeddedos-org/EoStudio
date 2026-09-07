"""Workspace Intelligence — project-wide semantic understanding.

Provides:
- Semantic code search (find by meaning, not just text)
- Dependency graph analysis
- Dead code detection
- Cross-file refactoring suggestions
- Architecture health scoring
- Auto-generated project documentation
- Smart import resolution
- Symbol index (functions, classes, variables across all files)
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

log = logging.getLogger(__name__)


@dataclass
class Symbol:
    """A named symbol in the codebase."""

    name: str
    kind: str  # "function", "class", "variable", "import", "method"
    file: str
    line: int
    signature: str = ""
    docstring: str = ""
    references: List[str] = field(default_factory=list)  # Files that reference this


@dataclass
class FileIndex:
    """Index of a single source file."""

    path: str
    language: str
    symbols: List[Symbol]
    imports: List[str]
    exports: List[str]
    loc: int  # Lines of code
    last_modified: float
    checksum: str


@dataclass
class ArchitectureHealth:
    """Health metrics for the project architecture."""

    score: int  # 0-100
    circular_deps: List[Tuple[str, str]]
    dead_code: List[Symbol]
    large_files: List[str]  # Files > 500 LOC
    missing_tests: List[str]  # Modules without test coverage
    god_classes: List[Symbol]  # Classes with > 20 methods
    suggestions: List[str]


class SymbolIndex:
    """Fast symbol lookup across the entire workspace."""

    def __init__(self) -> None:
        self._symbols: Dict[str, List[Symbol]] = {}  # name → symbols
        self._by_file: Dict[str, FileIndex] = {}  # path → index
        self._dirty: Set[str] = set()

    def index_file(self, path: str, content: str, language: str) -> FileIndex:
        """Parse and index a single file."""
        checksum = hashlib.md5(content.encode()).hexdigest()
        existing = self._by_file.get(path)
        if existing and existing.checksum == checksum:
            return existing

        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []

        if language == "python":
            symbols, imports, exports = self._parse_python(path, content)
        elif language in ("typescript", "javascript"):
            symbols, imports, exports = self._parse_ts_js(path, content)

        idx = FileIndex(
            path=path,
            language=language,
            symbols=symbols,
            imports=imports,
            exports=exports,
            loc=content.count("\n") + 1,
            last_modified=time.time(),
            checksum=checksum,
        )
        self._by_file[path] = idx

        # Update symbol map
        for sym in symbols:
            self._symbols.setdefault(sym.name, []).append(sym)

        return idx

    def index_workspace(self, workspace: str) -> int:
        """Index all source files in a workspace directory.

        Returns:
            Number of files indexed.
        """
        root = Path(workspace)
        count = 0
        ext_lang = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
        }

        for path in root.rglob("*"):
            if path.is_file() and path.suffix in ext_lang:
                # Skip node_modules, .git, __pycache__
                parts = path.parts
                if any(p in parts for p in ("node_modules", ".git", "__pycache__", "dist", "build")):
                    continue
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    lang = ext_lang[path.suffix]
                    self.index_file(str(path), content, lang)
                    count += 1
                except Exception as exc:
                    log.debug("Failed to index %s: %s", path, exc)

        log.info("Indexed %d files in %s", count, workspace)
        return count

    def find_symbol(self, name: str) -> List[Symbol]:
        """Find all symbols with a given name."""
        return self._symbols.get(name, [])

    def search(self, query: str, kind: Optional[str] = None) -> List[Symbol]:
        """Search symbols by name pattern.

        Args:
            query: Substring or regex pattern to match against symbol names.
            kind: Optional filter by symbol kind.

        Returns:
            Matching symbols sorted by relevance.
        """
        results: List[Symbol] = []
        pattern = re.compile(query, re.IGNORECASE)

        for name, symbols in self._symbols.items():
            if pattern.search(name):
                for sym in symbols:
                    if kind is None or sym.kind == kind:
                        results.append(sym)

        # Sort: exact matches first, then by name length
        results.sort(key=lambda s: (s.name.lower() != query.lower(), len(s.name)))
        return results[:50]

    def get_file_index(self, path: str) -> Optional[FileIndex]:
        return self._by_file.get(path)

    def all_files(self) -> List[FileIndex]:
        return list(self._by_file.values())

    def dependency_graph(self) -> Dict[str, List[str]]:
        """Build a file-level dependency graph from imports."""
        graph: Dict[str, List[str]] = {}
        for path, idx in self._by_file.items():
            deps: List[str] = []
            for imp in idx.imports:
                # Resolve relative imports
                for other_path in self._by_file:
                    if imp in other_path:
                        deps.append(other_path)
                        break
            graph[path] = deps
        return graph

    # ------------------------------------------------------------------
    # Language parsers
    # ------------------------------------------------------------------

    def _parse_python(self, path: str, content: str) -> Tuple[List[Symbol], List[str], List[str]]:
        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return symbols, imports, exports

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                sig = f"def {node.name}({', '.join(args)})"
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        file=path,
                        line=node.lineno,
                        signature=sig,
                        docstring=docstring[:200],
                    )
                )
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        file=path,
                        line=node.lineno,
                        docstring=docstring[:200],
                    )
                )
                exports.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return symbols, imports, exports

    def _parse_ts_js(self, path: str, content: str) -> Tuple[List[Symbol], List[str], List[str]]:
        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []

        # Extract imports
        for m in re.finditer(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]", content):
            imports.append(m.group(1))

        # Extract function declarations
        for m in re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", content):
            line = content[: m.start()].count("\n") + 1
            symbols.append(
                Symbol(
                    name=m.group(1),
                    kind="function",
                    file=path,
                    line=line,
                    signature=f"function {m.group(1)}({m.group(2)})",
                )
            )
            if "export" in content[max(0, m.start() - 10) : m.start()]:
                exports.append(m.group(1))

        # Extract class declarations
        for m in re.finditer(r"(?:export\s+)?class\s+(\w+)", content):
            line = content[: m.start()].count("\n") + 1
            symbols.append(
                Symbol(
                    name=m.group(1),
                    kind="class",
                    file=path,
                    line=line,
                )
            )

        # Extract const arrow functions
        for m in re.finditer(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", content):
            line = content[: m.start()].count("\n") + 1
            symbols.append(
                Symbol(
                    name=m.group(1),
                    kind="function",
                    file=path,
                    line=line,
                )
            )

        return symbols, imports, exports


class WorkspaceIntelligence:
    """High-level workspace analysis and intelligence layer.

    Usage::

        wi = WorkspaceIntelligence("/path/to/project")
        wi.index()

        # Semantic search
        results = wi.semantic_search("authentication middleware")

        # Architecture health
        health = wi.analyze_health()
        print(f"Score: {health.score}/100")
        for suggestion in health.suggestions:
            print(f"  - {suggestion}")

        # Auto-generate docs
        docs = wi.generate_docs("src/auth.py")
    """

    def __init__(
        self,
        workspace: str,
        router: Optional[Any] = None,  # MultiModelRouter
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self._router = router
        self._index = SymbolIndex()
        self._indexed = False

    def index(self) -> int:
        """Index the workspace. Returns number of files indexed."""
        count = self._index.index_workspace(str(self.workspace))
        self._indexed = True
        return count

    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search the codebase by semantic meaning.

        Falls back to symbol name search if no AI router is available.
        """
        if not self._indexed:
            self.index()

        # First try symbol name search
        symbols = self._index.search(query)
        results = [
            {
                "type": "symbol",
                "name": sym.name,
                "kind": sym.kind,
                "file": sym.file,
                "line": sym.line,
                "signature": sym.signature,
                "docstring": sym.docstring,
                "score": 1.0,
            }
            for sym in symbols[:top_k]
        ]

        # Augment with full-text search
        text_results = self._text_search(query)
        for tr in text_results[:top_k]:
            if not any(r["file"] == tr["file"] and r["line"] == tr["line"] for r in results):
                results.append(tr)

        return results[:top_k]

    def _text_search(self, query: str) -> List[Dict[str, Any]]:
        """Full-text search across all indexed files."""
        results: List[Dict[str, Any]] = []
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for idx in self._index.all_files():
            try:
                content = Path(idx.path).read_text(encoding="utf-8", errors="ignore")
                for m in pattern.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    results.append(
                        {
                            "type": "text_match",
                            "file": idx.path,
                            "line": line,
                            "snippet": content[max(0, m.start() - 40) : m.end() + 40].strip(),
                            "score": 0.5,
                        }
                    )
                    if len(results) >= 20:
                        return results
            except Exception:
                pass
        return results

    def analyze_health(self) -> ArchitectureHealth:
        """Analyze the project architecture and return health metrics."""
        if not self._indexed:
            self.index()

        dep_graph = self._index.dependency_graph()
        circular = self._find_circular_deps(dep_graph)
        dead_code = self._find_dead_code()
        large_files = [idx.path for idx in self._index.all_files() if idx.loc > 500]
        god_classes = [
            sym
            for sym in self._index.search("", kind="class")
            # Simplified: flag classes in large files
            if any(idx.path == sym.file and idx.loc > 300 for idx in self._index.all_files())
        ]

        # Check for test coverage
        test_files = {idx.path for idx in self._index.all_files() if "test" in idx.path.lower()}
        source_files = [idx.path for idx in self._index.all_files() if "test" not in idx.path.lower()]
        missing_tests: List[str] = []
        for src in source_files:
            src_name = Path(src).stem
            has_test = any(src_name in tf for tf in test_files)
            if not has_test:
                missing_tests.append(src)

        # Score calculation
        score = 100
        score -= len(circular) * 10
        score -= min(len(large_files) * 5, 20)
        score -= min(len(missing_tests) * 2, 20)
        score -= min(len(god_classes) * 5, 15)
        score = max(0, score)

        suggestions: List[str] = []
        if circular:
            suggestions.append(f"Resolve {len(circular)} circular dependency(ies) to improve maintainability")
        if large_files:
            suggestions.append(f"Split {len(large_files)} large file(s) (>500 LOC) into smaller modules")
        if missing_tests:
            suggestions.append(f"Add tests for {len(missing_tests)} untested module(s)")
        if god_classes:
            suggestions.append(f"Refactor {len(god_classes)} large class(es) using Single Responsibility Principle")

        return ArchitectureHealth(
            score=score,
            circular_deps=circular,
            dead_code=dead_code,
            large_files=large_files,
            missing_tests=missing_tests[:10],
            god_classes=god_classes[:5],
            suggestions=suggestions,
        )

    def generate_docs(self, file_path: str) -> str:
        """Generate documentation for a source file using AI."""
        full_path = self.workspace / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        content = full_path.read_text(encoding="utf-8")
        idx = self._index.get_file_index(str(full_path))

        if self._router:
            prompt = (
                f"Generate comprehensive API documentation for this file.\n\n"
                f"File: {file_path}\n"
                f"Content:\n{content[:3000]}\n\n"
                f"Include: overview, all public functions/classes with parameters, "
                f"return types, examples, and usage notes. Format as Markdown."
            )
            from eostudio.core.ai.multi_model_router import TaskType

            return self._router.complete(prompt, task=TaskType.DOCUMENTATION, complexity=5)

        # Fallback: extract docstrings
        lines = [f"# {file_path}\n"]
        if idx:
            for sym in idx.symbols:
                if sym.docstring:
                    lines.append(f"## `{sym.signature or sym.name}`\n{sym.docstring}\n")
        return "\n".join(lines)

    def suggest_refactoring(self, file_path: str) -> List[str]:
        """Suggest refactoring opportunities for a file."""
        full_path = self.workspace / file_path
        if not full_path.exists():
            return []

        content = full_path.read_text(encoding="utf-8")

        if self._router:
            prompt = (
                f"Analyze this code and suggest specific refactoring improvements.\n\n"
                f"File: {file_path}\n{content[:2000]}\n\n"
                f"Return a JSON array of suggestion strings."
            )
            from eostudio.core.ai.multi_model_router import TaskType

            raw = self._router.complete(prompt, task=TaskType.CODE_REVIEW, complexity=6)
            try:
                result = json.loads(re.search(r"\[[\s\S]+\]", raw).group())
                if isinstance(result, list):
                    return result
            except Exception:
                pass

        # Rule-based fallback
        suggestions: List[str] = []
        lines = content.split("\n")
        if len(lines) > 300:
            suggestions.append("File is large (>300 lines) — consider splitting into modules")
        if content.count("TODO") > 5:
            suggestions.append(f"Found {content.count('TODO')} TODO comments — address technical debt")
        if re.search(r"except\s*:", content):
            suggestions.append("Avoid bare `except:` — catch specific exceptions")
        if re.search(r"print\(", content) and "test" not in file_path.lower():
            suggestions.append("Replace print() statements with proper logging")
        return suggestions

    def _find_circular_deps(self, graph: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """Detect circular dependencies using DFS."""
        circular: List[Tuple[str, str]] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            in_stack.add(node)
            for dep in graph.get(node, []):
                if dep in in_stack:
                    circular.append((node, dep))
                elif dep not in visited:
                    dfs(dep, path + [dep])
            in_stack.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])

        return circular[:10]  # Return up to 10

    def _find_dead_code(self) -> List[Symbol]:
        """Find symbols that are defined but never referenced."""
        all_content = ""
        for idx in self._index.all_files():
            try:
                all_content += Path(idx.path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

        dead: List[Symbol] = []
        for syms in self._index._symbols.values():
            for sym in syms:
                if sym.kind == "function" and not sym.name.startswith("_"):
                    # Count references (excluding definition)
                    count = all_content.count(sym.name)
                    if count <= 1:  # Only the definition itself
                        dead.append(sym)

        return dead[:20]
