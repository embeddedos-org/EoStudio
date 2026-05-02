"""Project manager for EoStudio — workspaces, templates, and tasks."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EOSTUDIO_DIR = Path.home() / ".eostudio"
_RECENT_PROJECTS_FILE = _EOSTUDIO_DIR / "recent_projects.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceConfig:
    """Multi-root workspace configuration stored in ``.eostudio/workspace.json``."""

    folders: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    extensions: List[str] = field(default_factory=list)
    tasks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProjectTemplate:
    """A project scaffold with pre-defined files and metadata."""

    name: str = ""
    description: str = ""
    language: str = ""
    framework: str = ""
    files: Dict[str, str] = field(default_factory=dict)


@dataclass
class RecentProject:
    """Entry in the recent-projects list."""

    name: str = ""
    path: str = ""
    last_opened: float = 0.0
    pinned: bool = False


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

def _builtin_templates() -> List[ProjectTemplate]:
    """Return 20+ starter templates for common languages and frameworks."""
    return [
        ProjectTemplate("python-basic", "Basic Python project", "python", "none", {
            "main.py": '"""Entry point."""\n\n\ndef main() -> None:\n    print("Hello, world!")\n\n\nif __name__ == "__main__":\n    main()\n',
            "requirements.txt": "",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
        }),
        ProjectTemplate("python-flask", "Flask web application", "python", "flask", {
            "app.py": 'from flask import Flask\n\napp = Flask(__name__)\n\n\n@app.route("/")\ndef index():\n    return "Hello, Flask!"\n\n\nif __name__ == "__main__":\n    app.run(debug=True)\n',
            "requirements.txt": "flask\n",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
        }),
        ProjectTemplate("python-fastapi", "FastAPI web service", "python", "fastapi", {
            "main.py": 'from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get("/")\nasync def root():\n    return {"message": "Hello, FastAPI!"}\n',
            "requirements.txt": "fastapi\nuvicorn[standard]\n",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
        }),
        ProjectTemplate("python-django", "Django web application", "python", "django", {
            "manage.py": '#!/usr/bin/env python\nimport os, sys\n\ndef main():\n    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")\n    from django.core.management import execute_from_command_line\n    execute_from_command_line(sys.argv)\n\nif __name__ == "__main__":\n    main()\n',
            "requirements.txt": "django\n",
            ".gitignore": "__pycache__/\n*.pyc\ndb.sqlite3\n",
        }),
        ProjectTemplate("javascript-node", "Node.js application", "javascript", "node", {
            "index.js": 'console.log("Hello, Node.js!");\n',
            "package.json": '{\n  "name": "my-app",\n  "version": "1.0.0",\n  "main": "index.js",\n  "scripts": {"start": "node index.js"}\n}\n',
            ".gitignore": "node_modules/\n",
        }),
        ProjectTemplate("javascript-express", "Express.js web server", "javascript", "express", {
            "index.js": 'const express = require("express");\nconst app = express();\n\napp.get("/", (req, res) => res.send("Hello, Express!"));\n\napp.listen(3000, () => console.log("Listening on :3000"));\n',
            "package.json": '{\n  "name": "my-express-app",\n  "version": "1.0.0",\n  "main": "index.js",\n  "scripts": {"start": "node index.js"},\n  "dependencies": {"express": "^4.18.0"}\n}\n',
            ".gitignore": "node_modules/\n",
        }),
        ProjectTemplate("typescript-node", "TypeScript Node.js application", "typescript", "node", {
            "src/index.ts": 'console.log("Hello, TypeScript!");\n',
            "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2020", "module": "commonjs", "outDir": "dist", "strict": true},\n  "include": ["src"]\n}\n',
            "package.json": '{\n  "name": "my-ts-app",\n  "version": "1.0.0",\n  "scripts": {"build": "tsc", "start": "node dist/index.js"}\n}\n',
            ".gitignore": "node_modules/\ndist/\n",
        }),
        ProjectTemplate("react", "React single-page application", "typescript", "react", {
            "src/App.tsx": 'export default function App() {\n  return <h1>Hello, React!</h1>;\n}\n',
            "src/index.tsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(<App />);\n',
            "package.json": '{\n  "name": "my-react-app",\n  "version": "1.0.0",\n  "scripts": {"start": "react-scripts start", "build": "react-scripts build"}\n}\n',
            ".gitignore": "node_modules/\nbuild/\n",
        }),
        ProjectTemplate("nextjs", "Next.js full-stack application", "typescript", "nextjs", {
            "pages/index.tsx": 'export default function Home() {\n  return <h1>Hello, Next.js!</h1>;\n}\n',
            "package.json": '{\n  "name": "my-nextjs-app",\n  "version": "1.0.0",\n  "scripts": {"dev": "next dev", "build": "next build"}\n}\n',
            ".gitignore": "node_modules/\n.next/\n",
        }),
        ProjectTemplate("vue", "Vue.js application", "typescript", "vue", {
            "src/App.vue": '<template>\n  <h1>Hello, Vue!</h1>\n</template>\n\n<script setup lang="ts">\n</script>\n',
            "package.json": '{\n  "name": "my-vue-app",\n  "version": "1.0.0",\n  "scripts": {"dev": "vite", "build": "vite build"}\n}\n',
            ".gitignore": "node_modules/\ndist/\n",
        }),
        ProjectTemplate("rust-basic", "Rust application", "rust", "none", {
            "src/main.rs": 'fn main() {\n    println!("Hello, Rust!");\n}\n',
            "Cargo.toml": '[package]\nname = "my-app"\nversion = "0.1.0"\nedition = "2021"\n',
            ".gitignore": "target/\n",
        }),
        ProjectTemplate("rust-actix", "Rust Actix Web server", "rust", "actix-web", {
            "src/main.rs": 'use actix_web::{get, App, HttpServer, Responder};\n\n#[get("/")]\nasync fn index() -> impl Responder {\n    "Hello, Actix!"\n}\n\n#[actix_web::main]\nasync fn main() -> std::io::Result<()> {\n    HttpServer::new(|| App::new().service(index))\n        .bind("127.0.0.1:8080")?\n        .run()\n        .await\n}\n',
            "Cargo.toml": '[package]\nname = "my-actix-app"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nactix-web = "4"\n',
            ".gitignore": "target/\n",
        }),
        ProjectTemplate("go-basic", "Go application", "go", "none", {
            "main.go": 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Hello, Go!")\n}\n',
            "go.mod": 'module myapp\n\ngo 1.21\n',
            ".gitignore": "bin/\n",
        }),
        ProjectTemplate("go-gin", "Go Gin web server", "go", "gin", {
            "main.go": 'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {\n\tr := gin.Default()\n\tr.GET("/", func(c *gin.Context) {\n\t\tc.JSON(200, gin.H{"message": "Hello, Gin!"})\n\t})\n\tr.Run()\n}\n',
            "go.mod": 'module myapp\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9.1\n',
            ".gitignore": "bin/\n",
        }),
        ProjectTemplate("c-basic", "C application", "c", "none", {
            "main.c": '#include <stdio.h>\n\nint main(void) {\n    printf("Hello, C!\\n");\n    return 0;\n}\n',
            "Makefile": 'CC=gcc\nCFLAGS=-Wall -Wextra -std=c17\n\nall: main\n\nmain: main.c\n\t$(CC) $(CFLAGS) -o $@ $<\n\nclean:\n\trm -f main\n',
            ".gitignore": "*.o\nmain\n",
        }),
        ProjectTemplate("cpp-basic", "C++ application", "cpp", "none", {
            "main.cpp": '#include <iostream>\n\nint main() {\n    std::cout << "Hello, C++!" << std::endl;\n    return 0;\n}\n',
            "CMakeLists.txt": 'cmake_minimum_required(VERSION 3.16)\nproject(myapp LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 20)\nadd_executable(myapp main.cpp)\n',
            ".gitignore": "build/\n",
        }),
        ProjectTemplate("java-basic", "Java application", "java", "none", {
            "src/Main.java": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, Java!");\n    }\n}\n',
            ".gitignore": "*.class\nbuild/\n",
        }),
        ProjectTemplate("java-spring", "Spring Boot application", "java", "spring-boot", {
            "src/main/java/com/example/App.java": 'package com.example;\n\nimport org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class App {\n    public static void main(String[] args) {\n        SpringApplication.run(App.class, args);\n    }\n}\n',
            "build.gradle": 'plugins {\n    id "org.springframework.boot" version "3.2.0"\n    id "java"\n}\n\ndependencies {\n    implementation "org.springframework.boot:spring-boot-starter-web"\n}\n',
            ".gitignore": "build/\n.gradle/\n",
        }),
        ProjectTemplate("csharp-console", "C# console application", "csharp", "dotnet", {
            "Program.cs": 'Console.WriteLine("Hello, C#!");\n',
            "app.csproj": '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n',
            ".gitignore": "bin/\nobj/\n",
        }),
        ProjectTemplate("ruby-rails", "Ruby on Rails application", "ruby", "rails", {
            "config.ru": 'require_relative "config/environment"\nrun Rails.application\n',
            "Gemfile": 'source "https://rubygems.org"\ngem "rails", "~> 7.1"\n',
            ".gitignore": "log/\ntmp/\n",
        }),
        ProjectTemplate("embedded-c", "Embedded C firmware project", "c", "embedded", {
            "src/main.c": '#include <stdint.h>\n\nint main(void) {\n    while (1) {\n        // main loop\n    }\n    return 0;\n}\n',
            "Makefile": 'CC=arm-none-eabi-gcc\nCFLAGS=-mcpu=cortex-m4 -mthumb -Wall\n\nall:\n\t$(CC) $(CFLAGS) -o firmware.elf src/main.c\n\nclean:\n\trm -f firmware.elf\n',
            ".gitignore": "*.elf\n*.bin\n*.hex\nbuild/\n",
        }),
        ProjectTemplate("svelte", "Svelte application", "typescript", "svelte", {
            "src/App.svelte": '<h1>Hello, Svelte!</h1>\n',
            "package.json": '{\n  "name": "my-svelte-app",\n  "version": "1.0.0",\n  "scripts": {"dev": "vite dev", "build": "vite build"}\n}\n',
            ".gitignore": "node_modules/\ndist/\n",
        }),
    ]


# ---------------------------------------------------------------------------
# Project type detection
# ---------------------------------------------------------------------------

_PROJECT_MARKERS: List[Dict[str, Any]] = [
    {"file": "Cargo.toml", "language": "rust", "framework": "cargo"},
    {"file": "go.mod", "language": "go", "framework": "go-modules"},
    {"file": "package.json", "language": "javascript", "framework": "node"},
    {"file": "tsconfig.json", "language": "typescript", "framework": "node"},
    {"file": "pyproject.toml", "language": "python", "framework": "pyproject"},
    {"file": "setup.py", "language": "python", "framework": "setuptools"},
    {"file": "requirements.txt", "language": "python", "framework": "pip"},
    {"file": "Pipfile", "language": "python", "framework": "pipenv"},
    {"file": "Gemfile", "language": "ruby", "framework": "bundler"},
    {"file": "pom.xml", "language": "java", "framework": "maven"},
    {"file": "build.gradle", "language": "java", "framework": "gradle"},
    {"file": "CMakeLists.txt", "language": "cpp", "framework": "cmake"},
    {"file": "Makefile", "language": "c", "framework": "make"},
    {"file": ".csproj", "language": "csharp", "framework": "dotnet"},
    {"file": "mix.exs", "language": "elixir", "framework": "mix"},
    {"file": "pubspec.yaml", "language": "dart", "framework": "flutter"},
    {"file": "composer.json", "language": "php", "framework": "composer"},
    {"file": "next.config.js", "language": "typescript", "framework": "nextjs"},
    {"file": "next.config.mjs", "language": "typescript", "framework": "nextjs"},
    {"file": "nuxt.config.ts", "language": "typescript", "framework": "nuxt"},
    {"file": "svelte.config.js", "language": "typescript", "framework": "svelte"},
    {"file": "angular.json", "language": "typescript", "framework": "angular"},
]


# ---------------------------------------------------------------------------
# Project Manager
# ---------------------------------------------------------------------------

class ProjectManager:
    """Workspace and project management for EoStudio.

    Backward-compatible with the original stub API:
        ``__init__(), create(name, path), open(name), list_projects()``
    """

    def __init__(self) -> None:
        self._projects: Dict[str, Any] = {}
        self.current_project: Optional[str] = None
        self._workspace_folders: List[str] = []
        self._templates = _builtin_templates()
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # -- backward compat (original stub API) ---------------------------------

    def create(self, name: str, path: str) -> Dict[str, Any]:
        """Create a new project directory with default scaffolding."""
        project_dir = Path(path)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create .eostudio workspace metadata.
        meta_dir = project_dir / ".eostudio"
        meta_dir.mkdir(exist_ok=True)

        config = WorkspaceConfig(folders=[str(project_dir)])
        self.save_workspace_config(str(project_dir), config)

        project: Dict[str, Any] = {"name": name, "path": str(project_dir)}
        self._projects[name] = project
        self.add_to_recent(name, str(project_dir))
        return project

    def open(self, name: str) -> bool:
        """Open a previously created project by *name*."""
        if name in self._projects:
            self.current_project = name
            proj_path = self._projects[name].get("path", "")
            if proj_path:
                self.add_to_recent(name, proj_path)
            return True
        return False

    def list_projects(self) -> List[str]:
        """Return names of all known projects (backward compat)."""
        return list(self._projects.keys())

    # -- extended API --------------------------------------------------------

    def open_folder(self, path: str) -> bool:
        """Open a folder as a project, auto-detecting its type."""
        folder = Path(path)
        if not folder.is_dir():
            return False
        name = folder.name
        self._projects[name] = {"name": name, "path": str(folder)}
        self.current_project = name
        if str(folder) not in self._workspace_folders:
            self._workspace_folders.append(str(folder))
        self.add_to_recent(name, str(folder))
        return True

    # -- recent projects -----------------------------------------------------

    @staticmethod
    def get_recent_projects() -> List[RecentProject]:
        """Load the recent-projects list from ``~/.eostudio/recent_projects.json``."""
        if not _RECENT_PROJECTS_FILE.exists():
            return []
        try:
            raw = json.loads(_RECENT_PROJECTS_FILE.read_text(encoding="utf-8"))
            return [RecentProject(**entry) for entry in raw]
        except Exception:
            return []

    @staticmethod
    def _save_recent(projects: List[RecentProject]) -> None:
        _EOSTUDIO_DIR.mkdir(parents=True, exist_ok=True)
        _RECENT_PROJECTS_FILE.write_text(
            json.dumps([asdict(p) for p in projects], indent=2),
            encoding="utf-8",
        )

    def add_to_recent(self, name: str, path: str) -> None:
        """Add or refresh a project in the recent-projects list."""
        projects = self.get_recent_projects()
        # Remove existing entry with the same path.
        projects = [p for p in projects if p.path != path]
        projects.insert(0, RecentProject(name=name, path=path, last_opened=time.time()))
        # Keep a reasonable cap.
        projects = projects[:50]
        self._save_recent(projects)

    @staticmethod
    def remove_from_recent(path: str) -> None:
        """Remove a project from the recent list by path."""
        projects = ProjectManager.get_recent_projects()
        projects = [p for p in projects if p.path != path]
        ProjectManager._save_recent(projects)

    # -- templates -----------------------------------------------------------

    def create_from_template(self, template: str, path: str, name: str) -> Dict[str, Any]:
        """Scaffold a project from a built-in template."""
        tpl = next((t for t in self._templates if t.name == template), None)
        if tpl is None:
            raise ValueError(f"Unknown template: {template}")

        project_dir = Path(path)
        project_dir.mkdir(parents=True, exist_ok=True)

        for rel_path, content in tpl.files.items():
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        return self.create(name, str(project_dir))

    def list_templates(self) -> List[ProjectTemplate]:
        """Return all available project templates."""
        return list(self._templates)

    # -- project type detection -----------------------------------------------

    @staticmethod
    def detect_project_type(path: str) -> Dict[str, Any]:
        """Heuristically detect language and framework from files in *path*."""
        folder = Path(path)
        if not folder.is_dir():
            return {"language": "unknown", "framework": "unknown"}

        entries = {e.name for e in folder.iterdir()}

        for marker in _PROJECT_MARKERS:
            marker_file: str = marker["file"]
            # Handle .csproj-style suffix match.
            if marker_file.startswith("."):
                if any(e.endswith(marker_file) for e in entries):
                    return {"language": marker["language"], "framework": marker["framework"]}
            elif marker_file in entries:
                return {"language": marker["language"], "framework": marker["framework"]}

        return {"language": "unknown", "framework": "unknown"}

    # -- workspace config ----------------------------------------------------

    @staticmethod
    def get_workspace_config(path: str) -> WorkspaceConfig:
        """Read ``.eostudio/workspace.json`` from *path*."""
        config_file = Path(path) / ".eostudio" / "workspace.json"
        if not config_file.exists():
            return WorkspaceConfig(folders=[path])
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return WorkspaceConfig(**data)
        except Exception:
            return WorkspaceConfig(folders=[path])

    @staticmethod
    def save_workspace_config(path: str, config: WorkspaceConfig) -> None:
        """Write ``.eostudio/workspace.json`` under *path*."""
        meta_dir = Path(path) / ".eostudio"
        meta_dir.mkdir(parents=True, exist_ok=True)
        config_file = meta_dir / "workspace.json"
        config_file.write_text(
            json.dumps(asdict(config), indent=2),
            encoding="utf-8",
        )

    # -- tasks ---------------------------------------------------------------

    @staticmethod
    def get_tasks(path: str) -> List[Dict[str, Any]]:
        """Read tasks from ``.eostudio/tasks.json``."""
        tasks_file = Path(path) / ".eostudio" / "tasks.json"
        if not tasks_file.exists():
            return []
        try:
            return json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    @staticmethod
    def run_task(path: str, task_name: str) -> str:
        """Execute a named task defined in ``.eostudio/tasks.json``.

        Returns the combined stdout/stderr output.
        """
        tasks = ProjectManager.get_tasks(path)
        task = next((t for t in tasks if t.get("name") == task_name), None)
        if task is None:
            raise ValueError(f"Task not found: {task_name}")

        command = task.get("command", "")
        if not command:
            raise ValueError(f"Task '{task_name}' has no command")

        result = subprocess.run(
            command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.stdout + result.stderr

    # -- multi-root workspace ------------------------------------------------

    def add_folder_to_workspace(self, folder: str) -> None:
        """Add a folder to the current multi-root workspace."""
        resolved = str(Path(folder).resolve())
        if resolved not in self._workspace_folders:
            self._workspace_folders.append(resolved)

        # Persist to the current project's workspace config if available.
        if self.current_project and self.current_project in self._projects:
            proj_path = self._projects[self.current_project].get("path")
            if proj_path:
                config = self.get_workspace_config(proj_path)
                if resolved not in config.folders:
                    config.folders.append(resolved)
                    self.save_workspace_config(proj_path, config)
