"""Agentic Coder — Devin/Claude Code-style autonomous coding agent.

The AgenticCoder can:
- Understand a natural language task description
- Break it into subtasks (plan)
- Write, edit, and refactor code files
- Run tests and fix failures autonomously
- Search the codebase for relevant context
- Commit changes with meaningful messages
- Report progress in real-time via callbacks

Architecture:
    Task → Planner → SubtaskQueue → Executor → Verifier → Committer
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from eostudio.core.ai.multi_model_router import MultiModelRouter, RouterConfig, TaskType

log = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = auto()
    PLANNING = auto()
    EXECUTING = auto()
    TESTING = auto()
    FIXING = auto()
    COMMITTING = auto()
    DONE = auto()
    FAILED = auto()


@dataclass
class SubTask:
    """A single step in the agent's execution plan."""

    id: str
    description: str
    action: str  # "create_file", "edit_file", "run_command", "search", "test"
    target: str = ""  # File path or command
    content: str = ""  # File content or search query
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | done | failed
    result: str = ""


@dataclass
class AgentPlan:
    """The agent's execution plan for a task."""

    task: str
    subtasks: List[SubTask]
    estimated_files: int = 0
    estimated_tests: int = 0
    language: str = "python"


@dataclass
class AgentResult:
    """Final result from the agentic coder."""

    success: bool
    task: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    commit_hash: str = ""
    summary: str = ""
    duration_seconds: float = 0.0
    subtask_results: List[SubTask] = field(default_factory=list)


ProgressCallback = Callable[[AgentStatus, str, Optional[SubTask]], None]


class AgenticCoder:
    """Autonomous coding agent that plans and executes multi-step coding tasks.

    Usage::

        agent = AgenticCoder(workspace="/path/to/project")

        def on_progress(status, message, subtask):
            print(f"[{status.name}] {message}")

        result = agent.run(
            "Add a REST API endpoint for user authentication with JWT tokens",
            on_progress=on_progress,
        )
        print(result.summary)
    """

    MAX_FIX_ATTEMPTS = 3
    MAX_SUBTASKS = 20

    def __init__(
        self,
        workspace: str = ".",
        router: Optional[MultiModelRouter] = None,
        auto_commit: bool = False,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self._router = router or MultiModelRouter(RouterConfig(primary_model="gpt-4.1", fallback_model="gpt-4.1-mini"))
        self.auto_commit = auto_commit
        self._status = AgentStatus.IDLE
        self._current_plan: Optional[AgentPlan] = None

    @property
    def status(self) -> AgentStatus:
        return self._status

    def run(
        self,
        task: str,
        on_progress: Optional[ProgressCallback] = None,
        dry_run: bool = False,
    ) -> AgentResult:
        """Execute a coding task autonomously.

        Args:
            task: Natural language description of the task.
            on_progress: Optional callback for real-time progress updates.
            dry_run: If True, plan but don't execute file operations.

        Returns:
            AgentResult with details of what was done.
        """
        start = time.monotonic()
        self._emit(AgentStatus.PLANNING, f"Planning: {task}", None, on_progress)

        try:
            plan = self._plan(task)
            self._current_plan = plan
            self._emit(
                AgentStatus.PLANNING,
                f"Plan ready: {len(plan.subtasks)} steps",
                None,
                on_progress,
            )
        except Exception as exc:
            log.error("Planning failed: %s", exc)
            return AgentResult(success=False, task=task, summary=f"Planning failed: {exc}")

        files_created: List[str] = []
        files_modified: List[str] = []
        completed: List[SubTask] = []

        self._emit(AgentStatus.EXECUTING, "Starting execution", None, on_progress)

        for subtask in plan.subtasks:
            if len(completed) >= self.MAX_SUBTASKS:
                break

            self._emit(AgentStatus.EXECUTING, subtask.description, subtask, on_progress)

            if dry_run:
                subtask.status = "done"
                subtask.result = "(dry run)"
                completed.append(subtask)
                continue

            try:
                result = self._execute_subtask(subtask)
                subtask.status = "done"
                subtask.result = result

                if subtask.action == "create_file":
                    files_created.append(subtask.target)
                elif subtask.action == "edit_file":
                    files_modified.append(subtask.target)

            except Exception as exc:
                subtask.status = "failed"
                subtask.result = str(exc)
                log.warning("Subtask failed: %s — %s", subtask.description, exc)

            completed.append(subtask)

        # Run tests
        tests_passed = 0
        tests_failed = 0
        if not dry_run and self._has_tests():
            self._emit(AgentStatus.TESTING, "Running tests", None, on_progress)
            tests_passed, tests_failed, test_output = self._run_tests()

            if tests_failed > 0:
                self._emit(AgentStatus.FIXING, f"Fixing {tests_failed} test failures", None, on_progress)
                for attempt in range(self.MAX_FIX_ATTEMPTS):
                    fixed = self._fix_tests(test_output, files_created + files_modified)
                    if fixed:
                        tests_passed, tests_failed, test_output = self._run_tests()
                        if tests_failed == 0:
                            break

        # Auto-commit if requested
        commit_hash = ""
        if self.auto_commit and not dry_run and (files_created or files_modified):
            self._emit(AgentStatus.COMMITTING, "Committing changes", None, on_progress)
            commit_hash = self._commit(task, files_created + files_modified)

        duration = time.monotonic() - start
        summary = self._generate_summary(task, completed, files_created, files_modified, tests_passed, tests_failed)

        self._emit(AgentStatus.DONE, summary, None, on_progress)

        return AgentResult(
            success=tests_failed == 0,
            task=task,
            files_created=files_created,
            files_modified=files_modified,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            commit_hash=commit_hash,
            summary=summary,
            duration_seconds=round(duration, 2),
            subtask_results=completed,
        )

    def stream_run(
        self,
        task: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream agent progress as events.

        Yields dicts with keys: type, message, subtask, status
        """
        events: List[Dict[str, Any]] = []
        lock_event = __import__("threading").Event()

        def on_progress(status: AgentStatus, message: str, subtask: Optional[SubTask]) -> None:
            events.append(
                {
                    "type": "progress",
                    "status": status.name,
                    "message": message,
                    "subtask": subtask.description if subtask else None,
                }
            )
            lock_event.set()

        import threading

        result_holder: List[AgentResult] = []

        def _run() -> None:
            result = self.run(task, on_progress=on_progress)
            result_holder.append(result)
            events.append(
                {
                    "type": "done",
                    "result": {
                        "success": result.success,
                        "summary": result.summary,
                        "files_created": result.files_created,
                        "files_modified": result.files_modified,
                    },
                }
            )
            lock_event.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        while t.is_alive() or events:
            lock_event.wait(timeout=0.1)
            lock_event.clear()
            while events:
                yield events.pop(0)

    # ------------------------------------------------------------------
    # Internal: Planning
    # ------------------------------------------------------------------

    def _plan(self, task: str) -> AgentPlan:
        """Ask the LLM to create an execution plan."""
        workspace_summary = self._summarize_workspace()

        prompt = (
            f"You are an expert software engineer. Create a detailed execution plan for this task:\n\n"
            f"Task: {task}\n\n"
            f"Workspace summary:\n{workspace_summary}\n\n"
            f"Return a JSON object with:\n"
            f"- language: primary programming language\n"
            f"- estimated_files: number of files to create/modify\n"
            f"- subtasks: array of steps, each with:\n"
            f"  - id: unique string like 'step_1'\n"
            f"  - description: what this step does\n"
            f"  - action: one of create_file|edit_file|run_command|search|test\n"
            f"  - target: file path or command string\n"
            f"  - content: file content or search query (for create_file/search)\n"
            f"  - depends_on: array of step IDs this depends on\n"
            f"\nKeep the plan focused and under 15 steps."
        )

        raw = self._router.complete(prompt, task=TaskType.AGENT_LOOP, complexity=8)

        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]+\}", raw)
        if json_match:
            try:
                data = json.loads(json_match.group())
                subtasks = [SubTask(**st) for st in data.get("subtasks", [])]
                return AgentPlan(
                    task=task,
                    subtasks=subtasks,
                    estimated_files=data.get("estimated_files", len(subtasks)),
                    language=data.get("language", "python"),
                )
            except (json.JSONDecodeError, TypeError) as exc:
                log.warning("Failed to parse plan JSON: %s", exc)

        # Fallback: single-step plan
        return AgentPlan(
            task=task,
            subtasks=[
                SubTask(
                    id="step_1",
                    description=f"Implement: {task}",
                    action="create_file",
                    target="implementation.py",
                    content="# TODO: implement",
                )
            ],
        )

    # ------------------------------------------------------------------
    # Internal: Execution
    # ------------------------------------------------------------------

    def _execute_subtask(self, subtask: SubTask) -> str:
        """Execute a single subtask."""
        if subtask.action == "create_file":
            return self._create_file(subtask.target, subtask.content, subtask.description)
        elif subtask.action == "edit_file":
            return self._edit_file(subtask.target, subtask.description)
        elif subtask.action == "run_command":
            return self._run_command(subtask.target)
        elif subtask.action == "search":
            return self._search_codebase(subtask.content)
        elif subtask.action == "test":
            _, _, output = self._run_tests()
            return output
        else:
            return f"Unknown action: {subtask.action}"

    def _create_file(self, rel_path: str, content: str, description: str) -> str:
        """Create a file, generating content with AI if not provided."""
        full_path = self.workspace / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if not content or content.strip() == "# TODO: implement":
            # Generate content with AI
            content = self._generate_file_content(rel_path, description)

        full_path.write_text(content, encoding="utf-8")
        return f"Created {rel_path} ({len(content)} bytes)"

    def _edit_file(self, rel_path: str, instruction: str) -> str:
        """Edit an existing file according to an instruction."""
        full_path = self.workspace / rel_path
        if not full_path.exists():
            return f"File not found: {rel_path}"

        existing = full_path.read_text(encoding="utf-8")
        prompt = (
            f"Edit this file according to the instruction.\n\n"
            f"Instruction: {instruction}\n\n"
            f"File: {rel_path}\n"
            f"Current content:\n{existing}\n\n"
            f"Return the complete updated file content only."
        )
        new_content = self._router.complete(prompt, task=TaskType.REFACTOR, complexity=6)
        new_content = self._strip_fences(new_content)
        full_path.write_text(new_content, encoding="utf-8")
        return f"Edited {rel_path}"

    def _generate_file_content(self, rel_path: str, description: str) -> str:
        """Generate file content using AI."""
        ext = Path(rel_path).suffix
        lang_map = {
            ".py": "Python",
            ".ts": "TypeScript",
            ".tsx": "TypeScript React",
            ".js": "JavaScript",
            ".rs": "Rust",
            ".go": "Go",
            ".cpp": "C++",
        }
        lang = lang_map.get(ext, "code")

        prompt = (
            f"Write complete, production-quality {lang} code for:\n{description}\n\n"
            f"File: {rel_path}\n"
            f"Include proper error handling, type hints, and docstrings.\n"
            f"Return only the code, no explanations."
        )
        content = self._router.complete(prompt, task=TaskType.CODE_GENERATION, complexity=7)
        return self._strip_fences(content)

    def _run_command(self, command: str) -> str:
        """Run a shell command in the workspace."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr
            return output[:2000]  # Truncate
        except subprocess.TimeoutExpired:
            return "Command timed out after 60s"
        except Exception as exc:
            return f"Command failed: {exc}"

    def _search_codebase(self, query: str) -> str:
        """Search the codebase for relevant code."""
        results: List[str] = []
        for path in self.workspace.rglob("*.py"):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                if query.lower() in content.lower():
                    results.append(str(path.relative_to(self.workspace)))
            except Exception:
                pass
        return f"Found in: {', '.join(results[:10])}" if results else "Not found"

    def _has_tests(self) -> bool:
        """Check if the workspace has a test suite."""
        return (self.workspace / "tests").exists() or bool(list(self.workspace.glob("test_*.py")))

    def _run_tests(self) -> Tuple[int, int, str]:
        """Run the test suite and return (passed, failed, output)."""
        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr

        # Parse pytest output
        passed = len(re.findall(r"\d+ passed", output))
        failed_match = re.search(r"(\d+) failed", output)
        failed = int(failed_match.group(1)) if failed_match else 0
        passed_match = re.search(r"(\d+) passed", output)
        passed = int(passed_match.group(1)) if passed_match else 0

        return passed, failed, output[:3000]

    def _fix_tests(self, test_output: str, changed_files: List[str]) -> bool:
        """Attempt to fix failing tests using AI."""
        if not changed_files:
            return False

        for file_path in changed_files[:3]:  # Fix up to 3 files
            full_path = self.workspace / file_path
            if not full_path.exists():
                continue

            content = full_path.read_text(encoding="utf-8")
            prompt = (
                f"Fix the code to make the tests pass.\n\n"
                f"Test output:\n{test_output}\n\n"
                f"File: {file_path}\n"
                f"Current content:\n{content}\n\n"
                f"Return the fixed file content only."
            )
            fixed = self._router.complete(prompt, task=TaskType.DEBUG, complexity=7)
            fixed = self._strip_fences(fixed)
            if fixed and fixed != content:
                full_path.write_text(fixed, encoding="utf-8")
                return True
        return False

    def _commit(self, task: str, files: List[str]) -> str:
        """Commit changes to git."""
        try:
            subprocess.run(["git", "add"] + files, cwd=str(self.workspace), check=True)
            msg = f"feat: {task[:72]}"
            result = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
            )
            # Extract commit hash
            match = re.search(r"\[[\w/]+ ([a-f0-9]+)\]", result.stdout)
            return match.group(1) if match else ""
        except Exception as exc:
            log.warning("Commit failed: %s", exc)
            return ""

    def _summarize_workspace(self) -> str:
        """Create a brief summary of the workspace for the planner."""
        lines: List[str] = []
        py_files = list(self.workspace.rglob("*.py"))[:20]
        if py_files:
            lines.append(f"Python files: {', '.join(str(f.relative_to(self.workspace)) for f in py_files[:10])}")

        readme = self.workspace / "README.md"
        if readme.exists():
            first_lines = readme.read_text(encoding="utf-8")[:500]
            lines.append(f"README excerpt: {first_lines}")

        return "\n".join(lines) or "Empty workspace"

    def _generate_summary(
        self,
        task: str,
        subtasks: List[SubTask],
        created: List[str],
        modified: List[str],
        passed: int,
        failed: int,
    ) -> str:
        done = sum(1 for s in subtasks if s.status == "done")
        total = len(subtasks)
        parts = [
            f"Task: {task}",
            f"Completed {done}/{total} steps",
        ]
        if created:
            parts.append(f"Created: {', '.join(created)}")
        if modified:
            parts.append(f"Modified: {', '.join(modified)}")
        if passed or failed:
            parts.append(f"Tests: {passed} passed, {failed} failed")
        return " | ".join(parts)

    @staticmethod
    def _strip_fences(text: str) -> str:
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
        text = re.sub(r"\n?```$", "", text.strip())
        return text.strip()

    @staticmethod
    def _emit(
        status: AgentStatus,
        message: str,
        subtask: Optional[SubTask],
        callback: Optional[ProgressCallback],
    ) -> None:
        log.info("[%s] %s", status.name, message)
        if callback:
            try:
                callback(status, message, subtask)
            except Exception:
                pass
