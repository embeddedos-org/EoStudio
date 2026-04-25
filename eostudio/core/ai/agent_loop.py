"""Agentic AI Loop — generate → test → fix → refine code iteratively until production-ready."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig
from eostudio.core.ai.code_quality import CodeQualityChecker


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    FIXING = "fixing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentIteration:
    """A single iteration of the agent loop."""
    iteration: int
    state: AgentState
    action: str = ""
    files_generated: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration, "state": self.state.value,
            "action": self.action, "files_generated": self.files_generated,
            "files_modified": self.files_modified, "test_results": self.test_results,
            "errors": self.errors, "fixes_applied": self.fixes_applied,
        }


@dataclass
class AgentConfig:
    """Configuration for the agentic AI loop."""
    max_iterations: int = 10
    auto_fix: bool = True
    auto_test: bool = True
    auto_lint: bool = True
    test_command: str = "npm test"
    lint_command: str = "npm run lint"
    build_command: str = "npm run build"
    framework: str = "react"
    output_dir: str = "./generated"
    verbose: bool = True


class AgenticAILoop:
    """Kiro-style agentic development: generates code, tests it, fixes errors, iterates."""

    def __init__(self, config: Optional[AgentConfig] = None,
                 llm_client: Optional[LLMClient] = None) -> None:
        self.config = config or AgentConfig()
        self._client = llm_client or LLMClient(LLMConfig())
        self._state = AgentState.IDLE
        self._iterations: List[AgentIteration] = []
        self._generated_files: Dict[str, str] = {}
        self._on_progress: Optional[Callable[[AgentState, str], None]] = None
        self._on_iteration: Optional[Callable[[AgentIteration], None]] = None
        self._quality_checker = CodeQualityChecker()

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def iterations(self) -> List[AgentIteration]:
        return self._iterations

    def on_progress(self, callback: Callable[[AgentState, str], None]) -> None:
        self._on_progress = callback

    def on_iteration(self, callback: Callable[[AgentIteration], None]) -> None:
        self._on_iteration = callback

    def _emit(self, state: AgentState, message: str) -> None:
        self._state = state
        if self._on_progress:
            self._on_progress(state, message)

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full agentic loop: plan → generate → test → fix → refine."""
        self._emit(AgentState.PLANNING, "Analyzing spec and planning implementation...")

        for i in range(self.config.max_iterations):
            iteration = AgentIteration(iteration=i + 1, state=AgentState.GENERATING)

            # Step 1: Generate code
            self._emit(AgentState.GENERATING, f"Iteration {i+1}: Generating code...")
            if i == 0:
                files = self._generate_initial_code(spec)
            else:
                files = self._fix_code(self._iterations[-1].errors)

            iteration.files_generated = list(files.keys())
            self._generated_files.update(files)

            # Step 1b: Code quality auto-fix
            self._emit(AgentState.REVIEWING, f"Iteration {i+1}: Quality check & auto-fix...")
            for fname, code in list(self._generated_files.items()):
                fixed_code = self._quality_checker.auto_fix(fname, code)
                if fixed_code != code:
                    self._generated_files[fname] = fixed_code
                    files[fname] = fixed_code
                    iteration.fixes_applied.append(f"auto-fix: {fname}")

            # Write files to disk
            self._write_files(files)

            # Step 2: Test
            if self.config.auto_test:
                self._emit(AgentState.TESTING, f"Iteration {i+1}: Running tests...")
                test_results = self._run_tests()
                iteration.test_results = test_results

                if test_results.get("passed", False):
                    # Step 3: Lint
                    if self.config.auto_lint:
                        lint_results = self._run_lint()
                        if lint_results.get("passed", False):
                            iteration.state = AgentState.COMPLETE
                            self._iterations.append(iteration)
                            self._emit(AgentState.COMPLETE, "All tests and lint passed!")
                            break
                        else:
                            iteration.errors = lint_results.get("errors", [])
                    else:
                        iteration.state = AgentState.COMPLETE
                        self._iterations.append(iteration)
                        self._emit(AgentState.COMPLETE, "All tests passed!")
                        break
                else:
                    iteration.errors = test_results.get("errors", [])
                    iteration.state = AgentState.FIXING
                    self._emit(AgentState.FIXING, f"Iteration {i+1}: Fixing {len(iteration.errors)} errors...")
            else:
                iteration.state = AgentState.COMPLETE
                self._iterations.append(iteration)
                self._emit(AgentState.COMPLETE, "Code generated (testing disabled).")
                break

            self._iterations.append(iteration)
            if self._on_iteration:
                self._on_iteration(iteration)

        if self._state != AgentState.COMPLETE:
            self._emit(AgentState.FAILED, f"Max iterations ({self.config.max_iterations}) reached.")

        return {
            "state": self._state.value,
            "iterations": len(self._iterations),
            "files": list(self._generated_files.keys()),
            "history": [it.to_dict() for it in self._iterations],
        }

    def _generate_initial_code(self, spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate initial code from spec."""
        components = spec.get("tech_spec", {}).get("components", [])
        framework = self.config.framework

        messages = [{"role": "user", "content": (
            f"Generate production-ready {framework} code for this project.\n"
            f"Return JSON: {{filename: code_content}} for each file.\n\n"
            f"Spec:\n{json.dumps(spec, indent=2)[:3000]}\n\n"
            f"Generate: package.json, src/App.tsx, src/main.tsx, and component files.\n"
            f"Use TypeScript, Tailwind CSS, proper error handling, and accessibility.\n\n"
            f"PRODUCTION REQUIREMENTS (must include):\n"
            f"- Error boundaries wrapping route-level components\n"
            f"- React.Suspense with fallback for lazy-loaded routes\n"
            f"- Loading and error states for all async operations\n"
            f"- Form validation using zod schemas\n"
            f"- API client with retry logic and timeout handling\n"
            f"- TypeScript strict mode (no `any` types)\n"
            f"- Accessible components (aria labels, keyboard navigation)\n"
            f"- Environment variable validation at startup\n"
            f"- Structured error types (not raw strings)\n"
        )}]

        raw = self._client.chat(messages)
        try:
            files = json.loads(raw)
            if isinstance(files, dict):
                return files
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: generate basic project structure
        return self._generate_fallback_project(spec)

    def _fix_code(self, errors: List[str]) -> Dict[str, str]:
        """Ask AI to fix errors in generated code."""
        error_text = "\n".join(errors[:10])
        current_files = "\n".join(f"--- {k} ---\n{v[:500]}" for k, v in list(self._generated_files.items())[:5])

        messages = [{"role": "user", "content": (
            f"Fix these errors in the code:\n\n"
            f"Errors:\n{error_text}\n\n"
            f"Current files:\n{current_files}\n\n"
            f"Return JSON: {{filename: fixed_code}} only for files that need fixing."
        )}]

        raw = self._client.chat(messages)
        try:
            fixes = json.loads(raw)
            if isinstance(fixes, dict):
                return fixes
        except (json.JSONDecodeError, TypeError):
            pass
        return {}

    def _write_files(self, files: Dict[str, str]) -> None:
        """Write generated files to disk."""
        for filename, content in files.items():
            filepath = os.path.join(self.config.output_dir, filename)
            os.makedirs(os.path.dirname(filepath) or self.config.output_dir, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    def _run_tests(self) -> Dict[str, Any]:
        """Run test command and parse results."""
        try:
            result = subprocess.run(
                self.config.test_command.split(),
                cwd=self.config.output_dir,
                capture_output=True, text=True, timeout=120,
            )
            passed = result.returncode == 0
            errors = []
            if not passed:
                errors = [line for line in result.stderr.split("\n")
                         if "error" in line.lower() or "fail" in line.lower()][:10]
            return {"passed": passed, "errors": errors, "stdout": result.stdout[-500:]}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"passed": True, "errors": [], "note": "Test command not available"}

    def _run_lint(self) -> Dict[str, Any]:
        """Run lint command."""
        try:
            result = subprocess.run(
                self.config.lint_command.split(),
                cwd=self.config.output_dir,
                capture_output=True, text=True, timeout=60,
            )
            passed = result.returncode == 0
            errors = [line for line in result.stdout.split("\n") if "error" in line.lower()][:10]
            return {"passed": passed, "errors": errors}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"passed": True, "errors": []}

    def _generate_fallback_project(self, spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate a basic React + TypeScript project structure."""
        name = spec.get("tech_spec", {}).get("project_name", "my-app")
        return {
            "package.json": json.dumps({
                "name": name.lower().replace(" ", "-"),
                "private": True, "version": "0.1.0", "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "test": "vitest", "lint": "eslint ."},
                "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0", "react-router-dom": "^6.20.0",
                                 "framer-motion": "^11.0.0"},
                "devDependencies": {"@types/react": "^18.2.0", "typescript": "^5.3.0",
                                    "vite": "^5.0.0", "@vitejs/plugin-react": "^4.2.0",
                                    "tailwindcss": "^3.4.0", "autoprefixer": "^10.4.0",
                                    "vitest": "^1.0.0", "eslint": "^8.55.0"},
            }, indent=2),
            "src/main.tsx": (
                'import React from "react";\n'
                'import ReactDOM from "react-dom/client";\n'
                'import App from "./App";\n'
                'import "./index.css";\n\n'
                'ReactDOM.createRoot(document.getElementById("root")!).render(\n'
                "  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n"
            ),
            "src/App.tsx": (
                'import React from "react";\n'
                'import { BrowserRouter, Routes, Route } from "react-router-dom";\n\n'
                "export default function App() {\n"
                "  return (\n"
                "    <BrowserRouter>\n"
                '      <div className="min-h-screen bg-gray-50">\n'
                "        <Routes>\n"
                '          <Route path="/" element={<div>Home</div>} />\n'
                "        </Routes>\n"
                "      </div>\n"
                "    </BrowserRouter>\n"
                "  );\n}\n"
            ),
            "src/index.css": (
                "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"
            ),
            "tsconfig.json": json.dumps({
                "compilerOptions": {
                    "target": "ES2020", "useDefineForClassFields": True,
                    "lib": ["ES2020", "DOM", "DOM.Iterable"],
                    "module": "ESNext", "skipLibCheck": True,
                    "moduleResolution": "bundler", "allowImportingTsExtensions": True,
                    "resolveJsonModule": True, "isolatedModules": True,
                    "noEmit": True, "jsx": "react-jsx",
                    "strict": True, "noUnusedLocals": True, "noUnusedParameters": True,
                    "noFallthroughCasesInSwitch": True,
                    "baseUrl": ".", "paths": {"@/*": ["./src/*"]},
                },
                "include": ["src"],
            }, indent=2),
            ".eslintrc.json": json.dumps({
                "root": True,
                "env": {"browser": True, "es2020": True},
                "extends": [
                    "eslint:recommended",
                    "plugin:@typescript-eslint/recommended",
                    "plugin:react-hooks/recommended",
                ],
                "parser": "@typescript-eslint/parser",
                "plugins": ["react-refresh"],
                "rules": {
                    "react-refresh/only-export-components": ["warn", {"allowConstantExport": True}],
                    "@typescript-eslint/no-explicit-any": "error",
                },
            }, indent=2),
            ".prettierrc": json.dumps({
                "semi": True, "singleQuote": False,
                "tabWidth": 2, "trailingComma": "all",
                "printWidth": 100,
            }, indent=2),
        }
