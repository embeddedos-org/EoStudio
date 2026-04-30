"""
EoStudio Project Templates — 40+ starter templates across all major languages.

Phase 3: Cross-Platform Universal Support.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProjectTemplate:
    """A complete project template with all starter files."""

    name: str
    description: str
    category: str
    language: str
    framework: str
    files: Dict[str, str] = field(default_factory=dict)


class TemplateRegistry:
    """Registry of all built-in and custom project templates."""

    def __init__(self) -> None:
        self._templates: Dict[str, ProjectTemplate] = {}
        self._register_builtins()

    def get(self, name: str) -> Optional[ProjectTemplate]:
        return self._templates.get(name)

    def list(self) -> List[ProjectTemplate]:
        return list(self._templates.values())

    def search(self, query: str) -> List[ProjectTemplate]:
        q = query.lower()
        return [
            t for t in self._templates.values()
            if q in t.name.lower()
            or q in t.description.lower()
            or q in t.category.lower()
            or q in t.language.lower()
            or q in t.framework.lower()
        ]

    def register(self, template: ProjectTemplate) -> None:
        self._templates[template.name] = template

    # ------------------------------------------------------------------
    # Built-in templates
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        for t in _ALL_TEMPLATES:
            self._templates[t.name] = t


# ======================================================================
# Helper to shorten repetitive gitignore / readme content
# ======================================================================

def _gitignore(extras: str = "") -> str:
    base = (
        "# OS\n.DS_Store\nThumbs.db\n\n"
        "# IDE\n.idea/\n.vscode/\n*.swp\n*.swo\n"
    )
    return base + extras


def _readme(name: str, desc: str, run: str) -> str:
    return (
        f"# {{{{project_name}}}}\n\n"
        f"{desc}\n\n"
        f"## Getting Started\n\n"
        f"```bash\n{run}\n```\n"
    )


# ======================================================================
# PYTHON TEMPLATES
# ======================================================================

_fastapi = ProjectTemplate(
    name="fastapi",
    description="FastAPI REST API with uvicorn",
    category="python",
    language="python",
    framework="fastapi",
    files={
        "app/__init__.py": "",
        "app/main.py": (
            'from __future__ import annotations\n\n'
            'from fastapi import FastAPI\n\n'
            'app = FastAPI(title="{{project_name}}")\n\n\n'
            '@app.get("/")\n'
            'async def root() -> dict:\n'
            '    return {"message": "Hello from {{project_name}}"}\n\n\n'
            '@app.get("/health")\n'
            'async def health() -> dict:\n'
            '    return {"status": "ok"}\n'
        ),
        "app/config.py": (
            'from __future__ import annotations\n\n'
            'import os\n\n\n'
            'DEBUG = os.getenv("DEBUG", "false").lower() == "true"\n'
            'HOST = os.getenv("HOST", "0.0.0.0")\n'
            'PORT = int(os.getenv("PORT", "8000"))\n'
        ),
        "tests/__init__.py": "",
        "tests/test_main.py": (
            'from __future__ import annotations\n\n'
            'from fastapi.testclient import TestClient\n\n'
            'from app.main import app\n\n'
            'client = TestClient(app)\n\n\n'
            'def test_root():\n'
            '    resp = client.get("/")\n'
            '    assert resp.status_code == 200\n'
            '    assert resp.json()["message"] == "Hello from {{project_name}}"\n\n\n'
            'def test_health():\n'
            '    resp = client.get("/health")\n'
            '    assert resp.status_code == 200\n'
        ),
        "pyproject.toml": (
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'description = "{{project_name}}"\nrequires-python = ">=3.11"\n'
            'dependencies = ["fastapi>=0.110", "uvicorn[standard]>=0.29"]\n\n'
            '[project.optional-dependencies]\ndev = ["pytest", "httpx"]\n'
        ),
        "requirements.txt": "fastapi>=0.110\nuvicorn[standard]>=0.29\n",
        "README.md": _readme("fastapi", "A FastAPI REST API.", "uvicorn app.main:app --reload"),
        ".gitignore": _gitignore("\n# Python\n__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n"),
    },
)

_flask = ProjectTemplate(
    name="flask",
    description="Flask web application",
    category="python",
    language="python",
    framework="flask",
    files={
        "app/__init__.py": (
            'from __future__ import annotations\n\n'
            'from flask import Flask\n\n\n'
            'def create_app() -> Flask:\n'
            '    app = Flask(__name__)\n'
            '    from app.routes import bp\n'
            '    app.register_blueprint(bp)\n'
            '    return app\n'
        ),
        "app/routes.py": (
            'from __future__ import annotations\n\n'
            'from flask import Blueprint, jsonify\n\n'
            'bp = Blueprint("main", __name__)\n\n\n'
            '@bp.route("/")\n'
            'def index():\n'
            '    return jsonify(message="Hello from {{project_name}}")\n'
        ),
        "tests/__init__.py": "",
        "tests/test_app.py": (
            'from __future__ import annotations\n\n'
            'from app import create_app\n\n\n'
            'def test_index():\n'
            '    app = create_app()\n'
            '    client = app.test_client()\n'
            '    resp = client.get("/")\n'
            '    assert resp.status_code == 200\n'
        ),
        "pyproject.toml": (
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'requires-python = ">=3.11"\n'
            'dependencies = ["flask>=3.0"]\n\n'
            '[project.optional-dependencies]\ndev = ["pytest"]\n'
        ),
        "requirements.txt": "flask>=3.0\n",
        "README.md": _readme("flask", "A Flask web application.", "flask run --debug"),
        ".gitignore": _gitignore("\n# Python\n__pycache__/\n*.pyc\n.venv/\n"),
    },
)

_django = ProjectTemplate(
    name="django",
    description="Django web application",
    category="python",
    language="python",
    framework="django",
    files={
        "manage.py": (
            '#!/usr/bin/env python\n'
            'import os\nimport sys\n\n\n'
            'def main():\n'
            '    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")\n'
            '    from django.core.management import execute_from_command_line\n'
            '    execute_from_command_line(sys.argv)\n\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        ),
        "config/__init__.py": "",
        "config/settings.py": (
            'from pathlib import Path\n\n'
            'BASE_DIR = Path(__file__).resolve().parent.parent\n'
            'SECRET_KEY = "change-me"\n'
            'DEBUG = True\n'
            'ALLOWED_HOSTS = ["*"]\n'
            'INSTALLED_APPS = [\n'
            '    "django.contrib.admin",\n'
            '    "django.contrib.auth",\n'
            '    "django.contrib.contenttypes",\n'
            '    "django.contrib.sessions",\n'
            '    "django.contrib.messages",\n'
            '    "django.contrib.staticfiles",\n'
            ']\n'
            'ROOT_URLCONF = "config.urls"\n'
            'DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}\n'
        ),
        "config/urls.py": (
            'from django.contrib import admin\n'
            'from django.urls import path\n\n'
            'urlpatterns = [path("admin/", admin.site.urls)]\n'
        ),
        "tests/__init__.py": "",
        "tests/test_basic.py": (
            'from django.test import TestCase\n\n\n'
            'class SmokeTest(TestCase):\n'
            '    def test_homepage(self):\n'
            '        resp = self.client.get("/")\n'
            '        self.assertIn(resp.status_code, (200, 301, 404))\n'
        ),
        "pyproject.toml": (
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'dependencies = ["django>=5.0"]\n'
        ),
        "requirements.txt": "django>=5.0\n",
        "README.md": _readme("django", "A Django web application.", "python manage.py runserver"),
        ".gitignore": _gitignore("\n# Python\n__pycache__/\n*.pyc\n.venv/\ndb.sqlite3\n"),
    },
)

_cli_click = ProjectTemplate(
    name="cli-click",
    description="Python CLI with Click",
    category="python",
    language="python",
    framework="click",
    files={
        "{{project_slug}}/__init__.py": "",
        "{{project_slug}}/cli.py": (
            'from __future__ import annotations\n\n'
            'import click\n\n\n'
            '@click.group()\n'
            '@click.version_option()\n'
            'def cli():\n'
            '    """{{project_name}} command-line interface."""\n\n\n'
            '@cli.command()\n'
            '@click.argument("name", default="World")\n'
            'def hello(name: str):\n'
            '    """Say hello."""\n'
            '    click.echo(f"Hello, {name}!")\n\n\n'
            'if __name__ == "__main__":\n'
            '    cli()\n'
        ),
        "tests/__init__.py": "",
        "tests/test_cli.py": (
            'from click.testing import CliRunner\n'
            'from {{project_slug}}.cli import cli\n\n\n'
            'def test_hello():\n'
            '    runner = CliRunner()\n'
            '    result = runner.invoke(cli, ["hello"])\n'
            '    assert result.exit_code == 0\n'
            '    assert "Hello, World!" in result.output\n'
        ),
        "pyproject.toml": (
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'dependencies = ["click>=8.1"]\n\n'
            '[project.scripts]\n{{project_slug}} = "{{project_slug}}.cli:cli"\n'
        ),
        "README.md": _readme("cli-click", "A Python CLI built with Click.", "{{project_slug}} hello"),
        ".gitignore": _gitignore("\n__pycache__/\n*.pyc\n.venv/\ndist/\n"),
    },
)

_cli_typer = ProjectTemplate(
    name="cli-typer",
    description="Python CLI with Typer",
    category="python",
    language="python",
    framework="typer",
    files={
        "{{project_slug}}/__init__.py": "",
        "{{project_slug}}/main.py": (
            'from __future__ import annotations\n\n'
            'import typer\n\n'
            'app = typer.Typer(help="{{project_name}} CLI")\n\n\n'
            '@app.command()\n'
            'def hello(name: str = "World"):\n'
            '    """Say hello."""\n'
            '    typer.echo(f"Hello, {name}!")\n\n\n'
            'if __name__ == "__main__":\n'
            '    app()\n'
        ),
        "tests/__init__.py": "",
        "tests/test_main.py": (
            'from typer.testing import CliRunner\n'
            'from {{project_slug}}.main import app\n\n\n'
            'runner = CliRunner()\n\n\n'
            'def test_hello():\n'
            '    result = runner.invoke(app, ["hello"])\n'
            '    assert result.exit_code == 0\n'
        ),
        "pyproject.toml": (
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'dependencies = ["typer>=0.12"]\n\n'
            '[project.scripts]\n{{project_slug}} = "{{project_slug}}.main:app"\n'
        ),
        "README.md": _readme("cli-typer", "A Python CLI built with Typer.", "{{project_slug}} hello"),
        ".gitignore": _gitignore("\n__pycache__/\n*.pyc\n.venv/\ndist/\n"),
    },
)

_library_setuptools = ProjectTemplate(
    name="library-setuptools",
    description="Python library with setuptools",
    category="python",
    language="python",
    framework="setuptools",
    files={
        "src/{{project_slug}}/__init__.py": '__version__ = "0.1.0"\n',
        "src/{{project_slug}}/core.py": (
            'from __future__ import annotations\n\n\n'
            'def greet(name: str) -> str:\n'
            '    return f"Hello, {name}!"\n'
        ),
        "tests/__init__.py": "",
        "tests/test_core.py": (
            'from {{project_slug}}.core import greet\n\n\n'
            'def test_greet():\n'
            '    assert greet("World") == "Hello, World!"\n'
        ),
        "pyproject.toml": (
            '[build-system]\nrequires = ["setuptools>=69", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'requires-python = ">=3.11"\n\n'
            '[tool.setuptools.packages.find]\nwhere = ["src"]\n'
        ),
        "README.md": _readme("library", "A Python library.", "pip install -e ."),
        ".gitignore": _gitignore("\n__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n"),
    },
)

_library_poetry = ProjectTemplate(
    name="library-poetry",
    description="Python library with Poetry",
    category="python",
    language="python",
    framework="poetry",
    files={
        "{{project_slug}}/__init__.py": '__version__ = "0.1.0"\n',
        "{{project_slug}}/core.py": (
            'from __future__ import annotations\n\n\n'
            'def greet(name: str) -> str:\n'
            '    return f"Hello, {name}!"\n'
        ),
        "tests/__init__.py": "",
        "tests/test_core.py": (
            'from {{project_slug}}.core import greet\n\n\n'
            'def test_greet():\n'
            '    assert greet("World") == "Hello, World!"\n'
        ),
        "pyproject.toml": (
            '[tool.poetry]\nname = "{{project_slug}}"\nversion = "0.1.0"\n'
            'description = "{{project_name}}"\nauthors = ["Your Name <you@example.com>"]\n\n'
            '[tool.poetry.dependencies]\npython = "^3.11"\n\n'
            '[tool.poetry.group.dev.dependencies]\npytest = "^8.0"\n\n'
            '[build-system]\nrequires = ["poetry-core"]\n'
            'build-backend = "poetry.core.masonry.api"\n'
        ),
        "README.md": _readme("library-poetry", "A Python library managed with Poetry.", "poetry install"),
        ".gitignore": _gitignore("\n__pycache__/\n*.pyc\n.venv/\ndist/\n"),
    },
)

# ======================================================================
# JAVASCRIPT / TYPESCRIPT TEMPLATES
# ======================================================================

_js_gitignore = "\n# JS/TS\nnode_modules/\ndist/\nbuild/\n.env\ncoverage/\n"

_react = ProjectTemplate(
    name="react",
    description="React 18 with TypeScript and Vite",
    category="javascript",
    language="typescript",
    framework="react",
    files={
        "src/App.tsx": (
            'import React from "react";\n\n'
            'export default function App() {\n'
            '  return (\n'
            '    <div>\n'
            '      <h1>{{project_name}}</h1>\n'
            '      <p>Welcome to your React app.</p>\n'
            '    </div>\n'
            '  );\n'
            '}\n'
        ),
        "src/main.tsx": (
            'import React from "react";\n'
            'import ReactDOM from "react-dom/client";\n'
            'import App from "./App";\n\n'
            'ReactDOM.createRoot(document.getElementById("root")!).render(\n'
            '  <React.StrictMode>\n'
            '    <App />\n'
            '  </React.StrictMode>\n'
            ');\n'
        ),
        "index.html": (
            '<!doctype html>\n<html lang="en">\n<head>\n'
            '  <meta charset="UTF-8" />\n'
            '  <title>{{project_name}}</title>\n'
            '</head>\n<body>\n'
            '  <div id="root"></div>\n'
            '  <script type="module" src="/src/main.tsx"></script>\n'
            '</body>\n</html>\n'
        ),
        "src/__tests__/App.test.tsx": (
            'import { render, screen } from "@testing-library/react";\n'
            'import App from "../App";\n\n'
            'test("renders heading", () => {\n'
            '  render(<App />);\n'
            '  expect(screen.getByText("{{project_name}}")).toBeInTheDocument();\n'
            '});\n'
        ),
        "package.json": (
            '{\n  "name": "{{project_slug}}",\n  "version": "0.1.0",\n  "private": true,\n'
            '  "type": "module",\n'
            '  "scripts": {\n    "dev": "vite",\n    "build": "tsc && vite build",\n'
            '    "test": "vitest"\n  },\n'
            '  "dependencies": {\n    "react": "^18.3",\n    "react-dom": "^18.3"\n  },\n'
            '  "devDependencies": {\n    "@types/react": "^18.3",\n'
            '    "typescript": "^5.4",\n    "vite": "^5.4",\n'
            '    "@vitejs/plugin-react": "^4.3",\n    "vitest": "^1.6"\n  }\n}\n'
        ),
        "tsconfig.json": (
            '{\n  "compilerOptions": {\n    "target": "ES2020",\n'
            '    "module": "ESNext",\n    "jsx": "react-jsx",\n'
            '    "strict": true,\n    "moduleResolution": "bundler"\n  },\n'
            '  "include": ["src"]\n}\n'
        ),
        "vite.config.ts": (
            'import { defineConfig } from "vite";\n'
            'import react from "@vitejs/plugin-react";\n\n'
            'export default defineConfig({ plugins: [react()] });\n'
        ),
        "README.md": _readme("react", "React + TypeScript + Vite.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore),
    },
)

_nextjs = ProjectTemplate(
    name="nextjs",
    description="Next.js 14 App Router with TypeScript",
    category="javascript",
    language="typescript",
    framework="nextjs",
    files={
        "app/page.tsx": (
            'export default function Home() {\n'
            '  return <h1>{{project_name}}</h1>;\n'
            '}\n'
        ),
        "app/layout.tsx": (
            'export const metadata = { title: "{{project_name}}" };\n\n'
            'export default function RootLayout({ children }: { children: React.ReactNode }) {\n'
            '  return (\n'
            '    <html lang="en"><body>{children}</body></html>\n'
            '  );\n'
            '}\n'
        ),
        "__tests__/page.test.tsx": (
            'import { render, screen } from "@testing-library/react";\n'
            'import Home from "../app/page";\n\n'
            'test("renders heading", () => {\n'
            '  render(<Home />);\n'
            '  expect(screen.getByText("{{project_name}}")).toBeInTheDocument();\n'
            '});\n'
        ),
        "package.json": (
            '{\n  "name": "{{project_slug}}",\n  "version": "0.1.0",\n  "private": true,\n'
            '  "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},\n'
            '  "dependencies": {"next": "^14.2", "react": "^18.3", "react-dom": "^18.3"},\n'
            '  "devDependencies": {"typescript": "^5.4", "@types/react": "^18.3"}\n}\n'
        ),
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2017", "jsx": "preserve", "strict": true,\n    "moduleResolution": "bundler", "plugins": [{"name": "next"}]},\n  "include": ["**/*.ts", "**/*.tsx"]\n}\n',
        "README.md": _readme("nextjs", "Next.js 14 App Router.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore + ".next/\n"),
    },
)

_vue = ProjectTemplate(
    name="vue",
    description="Vue 3 with TypeScript and Vite",
    category="javascript",
    language="typescript",
    framework="vue",
    files={
        "src/App.vue": (
            '<script setup lang="ts">\n'
            'const title = "{{project_name}}";\n'
            '</script>\n\n'
            '<template>\n  <h1>{{ title }}</h1>\n</template>\n'
        ),
        "src/main.ts": 'import { createApp } from "vue";\nimport App from "./App.vue";\n\ncreateApp(App).mount("#app");\n',
        "index.html": '<!doctype html>\n<html lang="en">\n<head><meta charset="UTF-8" /><title>{{project_name}}</title></head>\n<body>\n  <div id="app"></div>\n  <script type="module" src="/src/main.ts"></script>\n</body>\n</html>\n',
        "src/__tests__/App.spec.ts": (
            'import { mount } from "@vue/test-utils";\n'
            'import App from "../App.vue";\n\n'
            'test("renders title", () => {\n'
            '  const wrapper = mount(App);\n'
            '  expect(wrapper.text()).toContain("{{project_name}}");\n'
            '});\n'
        ),
        "package.json": '{\n  "name": "{{project_slug}}",\n  "version": "0.1.0",\n  "private": true,\n  "type": "module",\n  "scripts": {"dev": "vite", "build": "vite build"},\n  "dependencies": {"vue": "^3.4"},\n  "devDependencies": {"typescript": "^5.4", "vite": "^5.4", "@vitejs/plugin-vue": "^5.0"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2020", "module": "ESNext", "strict": true, "moduleResolution": "bundler"},\n  "include": ["src"]\n}\n',
        "README.md": _readme("vue", "Vue 3 + TypeScript + Vite.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore),
    },
)

_nuxt = ProjectTemplate(
    name="nuxt",
    description="Nuxt 3 fullstack Vue framework",
    category="javascript",
    language="typescript",
    framework="nuxt",
    files={
        "app.vue": '<template>\n  <NuxtPage />\n</template>\n',
        "pages/index.vue": '<template>\n  <h1>{{project_name}}</h1>\n</template>\n',
        "tests/index.spec.ts": 'import { describe, it, expect } from "vitest";\n\ndescribe("app", () => {\n  it("exists", () => {\n    expect(true).toBe(true);\n  });\n});\n',
        "nuxt.config.ts": 'export default defineNuxtConfig({ devtools: { enabled: true } });\n',
        "package.json": '{\n  "name": "{{project_slug}}",\n  "private": true,\n  "scripts": {"dev": "nuxt dev", "build": "nuxt build"},\n  "devDependencies": {"nuxt": "^3.11"}\n}\n',
        "tsconfig.json": '{"extends": "./.nuxt/tsconfig.json"}\n',
        "README.md": _readme("nuxt", "Nuxt 3 fullstack app.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore + ".nuxt/\n.output/\n"),
    },
)

_svelte = ProjectTemplate(
    name="svelte",
    description="SvelteKit with TypeScript",
    category="javascript",
    language="typescript",
    framework="svelte",
    files={
        "src/routes/+page.svelte": '<h1>{{project_name}}</h1>\n<p>Welcome to SvelteKit.</p>\n',
        "src/app.html": '<!doctype html>\n<html lang="en">\n<head><meta charset="utf-8" /><title>{{project_name}}</title></head>\n<body>%sveltekit.body%</body>\n</html>\n',
        "tests/page.test.ts": 'import { describe, it, expect } from "vitest";\n\ndescribe("page", () => {\n  it("placeholder", () => expect(true).toBe(true));\n});\n',
        "svelte.config.js": 'import adapter from "@sveltejs/adapter-auto";\nexport default { kit: { adapter: adapter() } };\n',
        "package.json": '{\n  "name": "{{project_slug}}",\n  "private": true,\n  "scripts": {"dev": "vite dev", "build": "vite build"},\n  "devDependencies": {"@sveltejs/kit": "^2.5", "svelte": "^4.2", "vite": "^5.4"}\n}\n',
        "README.md": _readme("svelte", "SvelteKit app.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore + ".svelte-kit/\n"),
    },
)

_angular = ProjectTemplate(
    name="angular",
    description="Angular 17+ standalone components",
    category="javascript",
    language="typescript",
    framework="angular",
    files={
        "src/app/app.component.ts": (
            'import { Component } from "@angular/core";\n\n'
            '@Component({\n  selector: "app-root",\n  standalone: true,\n'
            '  template: `<h1>{{project_name}}</h1>`,\n})\n'
            'export class AppComponent {}\n'
        ),
        "src/main.ts": 'import { bootstrapApplication } from "@angular/platform-browser";\nimport { AppComponent } from "./app/app.component";\n\nbootstrapApplication(AppComponent);\n',
        "src/app/app.component.spec.ts": (
            'import { TestBed } from "@angular/core/testing";\n'
            'import { AppComponent } from "./app.component";\n\n'
            'describe("AppComponent", () => {\n'
            '  it("should create", () => {\n'
            '    const fixture = TestBed.createComponent(AppComponent);\n'
            '    expect(fixture.componentInstance).toBeTruthy();\n'
            '  });\n'
            '});\n'
        ),
        "package.json": '{\n  "name": "{{project_slug}}",\n  "private": true,\n  "scripts": {"start": "ng serve", "build": "ng build", "test": "ng test"},\n  "dependencies": {"@angular/core": "^17.3", "@angular/platform-browser": "^17.3"},\n  "devDependencies": {"typescript": "^5.4"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2022", "module": "ES2022", "strict": true, "experimentalDecorators": true}\n}\n',
        "README.md": _readme("angular", "Angular 17+ app.", "ng serve"),
        ".gitignore": _gitignore(_js_gitignore + ".angular/\n"),
    },
)

_express = ProjectTemplate(
    name="express",
    description="Express.js REST API with TypeScript",
    category="javascript",
    language="typescript",
    framework="express",
    files={
        "src/index.ts": (
            'import express from "express";\n\n'
            'const app = express();\n'
            'const PORT = process.env.PORT || 3000;\n\n'
            'app.use(express.json());\n\n'
            'app.get("/", (_req, res) => {\n'
            '  res.json({ message: "Hello from {{project_name}}" });\n'
            '});\n\n'
            'app.get("/health", (_req, res) => {\n'
            '  res.json({ status: "ok" });\n'
            '});\n\n'
            'app.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n'
        ),
        "src/__tests__/index.test.ts": (
            'import request from "supertest";\n'
            'import express from "express";\n\n'
            'const app = express();\n'
            'app.get("/", (_req, res) => res.json({ message: "ok" }));\n\n'
            'test("GET /", async () => {\n'
            '  const res = await request(app).get("/");\n'
            '  expect(res.status).toBe(200);\n'
            '});\n'
        ),
        "package.json": '{\n  "name": "{{project_slug}}",\n  "version": "0.1.0",\n  "scripts": {"dev": "ts-node-dev src/index.ts", "build": "tsc", "test": "jest"},\n  "dependencies": {"express": "^4.19"},\n  "devDependencies": {"@types/express": "^4.17", "typescript": "^5.4", "ts-node-dev": "^2.0", "jest": "^29.7", "supertest": "^7.0"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2020", "module": "commonjs", "outDir": "dist", "strict": true, "esModuleInterop": true},\n  "include": ["src"]\n}\n',
        "README.md": _readme("express", "Express.js REST API with TypeScript.", "npm run dev"),
        ".gitignore": _gitignore(_js_gitignore),
    },
)

_nestjs = ProjectTemplate(
    name="nestjs",
    description="NestJS API with TypeScript",
    category="javascript",
    language="typescript",
    framework="nestjs",
    files={
        "src/main.ts": 'import { NestFactory } from "@nestjs/core";\nimport { AppModule } from "./app.module";\n\nasync function bootstrap() {\n  const app = await NestFactory.create(AppModule);\n  await app.listen(3000);\n}\nbootstrap();\n',
        "src/app.module.ts": 'import { Module } from "@nestjs/common";\nimport { AppController } from "./app.controller";\n\n@Module({ controllers: [AppController] })\nexport class AppModule {}\n',
        "src/app.controller.ts": 'import { Controller, Get } from "@nestjs/common";\n\n@Controller()\nexport class AppController {\n  @Get()\n  getHello(): string {\n    return "Hello from {{project_name}}";\n  }\n}\n',
        "src/app.controller.spec.ts": 'import { Test } from "@nestjs/testing";\nimport { AppController } from "./app.controller";\n\ndescribe("AppController", () => {\n  let ctrl: AppController;\n  beforeEach(async () => {\n    const module = await Test.createTestingModule({ controllers: [AppController] }).compile();\n    ctrl = module.get(AppController);\n  });\n  it("returns hello", () => expect(ctrl.getHello()).toContain("Hello"));\n});\n',
        "package.json": '{\n  "name": "{{project_slug}}",\n  "scripts": {"start:dev": "nest start --watch", "build": "nest build", "test": "jest"},\n  "dependencies": {"@nestjs/common": "^10.3", "@nestjs/core": "^10.3", "@nestjs/platform-express": "^10.3"},\n  "devDependencies": {"@nestjs/cli": "^10.3", "@nestjs/testing": "^10.3", "typescript": "^5.4", "jest": "^29.7"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2021", "module": "commonjs", "strict": true, "experimentalDecorators": true, "emitDecoratorMetadata": true}\n}\n',
        "README.md": _readme("nestjs", "NestJS API.", "npm run start:dev"),
        ".gitignore": _gitignore(_js_gitignore),
    },
)

_electron = ProjectTemplate(
    name="electron",
    description="Electron desktop app with TypeScript",
    category="javascript",
    language="typescript",
    framework="electron",
    files={
        "src/main.ts": (
            'import { app, BrowserWindow } from "electron";\nimport path from "path";\n\n'
            'function createWindow() {\n'
            '  const win = new BrowserWindow({ width: 800, height: 600 });\n'
            '  win.loadFile(path.join(__dirname, "../index.html"));\n'
            '}\n\n'
            'app.whenReady().then(createWindow);\n'
            'app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });\n'
        ),
        "index.html": '<!doctype html>\n<html>\n<head><title>{{project_name}}</title></head>\n<body><h1>{{project_name}}</h1></body>\n</html>\n',
        "tests/main.test.ts": 'test("placeholder", () => expect(true).toBe(true));\n',
        "package.json": '{\n  "name": "{{project_slug}}",\n  "main": "dist/main.js",\n  "scripts": {"start": "electron .", "build": "tsc"},\n  "devDependencies": {"electron": "^30.0", "typescript": "^5.4"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ES2020", "module": "commonjs", "outDir": "dist", "strict": true}\n}\n',
        "README.md": _readme("electron", "Electron desktop app.", "npm start"),
        ".gitignore": _gitignore(_js_gitignore),
    },
)

_react_native = ProjectTemplate(
    name="react-native",
    description="React Native mobile app with TypeScript",
    category="javascript",
    language="typescript",
    framework="react-native",
    files={
        "App.tsx": (
            'import React from "react";\n'
            'import { View, Text, StyleSheet } from "react-native";\n\n'
            'export default function App() {\n'
            '  return (\n'
            '    <View style={styles.container}>\n'
            '      <Text style={styles.title}>{{project_name}}</Text>\n'
            '    </View>\n'
            '  );\n'
            '}\n\n'
            'const styles = StyleSheet.create({\n'
            '  container: { flex: 1, justifyContent: "center", alignItems: "center" },\n'
            '  title: { fontSize: 24, fontWeight: "bold" },\n'
            '});\n'
        ),
        "__tests__/App.test.tsx": 'import React from "react";\nimport { render } from "@testing-library/react-native";\nimport App from "../App";\n\ntest("renders title", () => {\n  const { getByText } = render(<App />);\n  expect(getByText("{{project_name}}")).toBeTruthy();\n});\n',
        "package.json": '{\n  "name": "{{project_slug}}",\n  "version": "0.1.0",\n  "scripts": {"start": "react-native start", "test": "jest"},\n  "dependencies": {"react": "^18.3", "react-native": "^0.74"},\n  "devDependencies": {"@types/react": "^18.3", "typescript": "^5.4", "jest": "^29.7"}\n}\n',
        "tsconfig.json": '{\n  "compilerOptions": {"target": "ESNext", "module": "commonjs", "jsx": "react-native", "strict": true}\n}\n',
        "README.md": _readme("react-native", "React Native mobile app.", "npx react-native start"),
        ".gitignore": _gitignore(_js_gitignore + "ios/\nandroid/\n"),
    },
)

# ======================================================================
# RUST TEMPLATES
# ======================================================================

_rust_gitignore = "\n# Rust\ntarget/\nCargo.lock\n"

_rust_binary = ProjectTemplate(
    name="rust-binary",
    description="Rust binary application",
    category="rust",
    language="rust",
    framework="cargo",
    files={
        "src/main.rs": 'fn main() {\n    println!("Hello from {{project_name}}!");\n}\n',
        "tests/integration_test.rs": '#[test]\nfn it_works() {\n    assert_eq!(2 + 2, 4);\n}\n',
        "Cargo.toml": '[package]\nname = "{{project_slug}}"\nversion = "0.1.0"\nedition = "2021"\n',
        "README.md": _readme("rust-binary", "A Rust binary application.", "cargo run"),
        ".gitignore": _gitignore(_rust_gitignore),
    },
)

_rust_library = ProjectTemplate(
    name="rust-library",
    description="Rust library crate",
    category="rust",
    language="rust",
    framework="cargo",
    files={
        "src/lib.rs": '/// Greet someone by name.\npub fn greet(name: &str) -> String {\n    format!("Hello, {name}!")\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n\n    #[test]\n    fn test_greet() {\n        assert_eq!(greet("World"), "Hello, World!");\n    }\n}\n',
        "Cargo.toml": '[package]\nname = "{{project_slug}}"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\nname = "{{project_slug}}"\npath = "src/lib.rs"\n',
        "README.md": _readme("rust-library", "A Rust library crate.", "cargo test"),
        ".gitignore": _gitignore(_rust_gitignore),
    },
)

_actix_web = ProjectTemplate(
    name="actix-web",
    description="Actix-web REST API",
    category="rust",
    language="rust",
    framework="actix-web",
    files={
        "src/main.rs": (
            'use actix_web::{get, web, App, HttpServer, HttpResponse};\n\n'
            '#[get("/")]\nasync fn index() -> HttpResponse {\n'
            '    HttpResponse::Ok().json(serde_json::json!({"message": "Hello from {{project_name}}"}))\n'
            '}\n\n'
            '#[actix_web::main]\nasync fn main() -> std::io::Result<()> {\n'
            '    HttpServer::new(|| App::new().service(index))\n'
            '        .bind("127.0.0.1:8080")?\n'
            '        .run().await\n'
            '}\n'
        ),
        "tests/api_test.rs": '#[test]\nfn placeholder() {\n    assert!(true);\n}\n',
        "Cargo.toml": '[package]\nname = "{{project_slug}}"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nactix-web = "4"\nserde_json = "1"\n',
        "README.md": _readme("actix-web", "Actix-web REST API.", "cargo run"),
        ".gitignore": _gitignore(_rust_gitignore),
    },
)

_axum = ProjectTemplate(
    name="axum",
    description="Axum web framework API",
    category="rust",
    language="rust",
    framework="axum",
    files={
        "src/main.rs": (
            'use axum::{routing::get, Json, Router};\nuse serde_json::{json, Value};\n\n'
            'async fn root() -> Json<Value> {\n'
            '    Json(json!({"message": "Hello from {{project_name}}"}))\n'
            '}\n\n'
            '#[tokio::main]\nasync fn main() {\n'
            '    let app = Router::new().route("/", get(root));\n'
            '    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();\n'
            '    axum::serve(listener, app).await.unwrap();\n'
            '}\n'
        ),
        "tests/api_test.rs": '#[test]\nfn placeholder() {\n    assert!(true);\n}\n',
        "Cargo.toml": '[package]\nname = "{{project_slug}}"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\naxum = "0.7"\ntokio = { version = "1", features = ["full"] }\nserde_json = "1"\n',
        "README.md": _readme("axum", "Axum web API.", "cargo run"),
        ".gitignore": _gitignore(_rust_gitignore),
    },
)

_tauri = ProjectTemplate(
    name="tauri",
    description="Tauri desktop app (Rust + web frontend)",
    category="rust",
    language="rust",
    framework="tauri",
    files={
        "src-tauri/src/main.rs": (
            '#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]\n\n'
            'fn main() {\n'
            '    tauri::Builder::default()\n'
            '        .run(tauri::generate_context!())\n'
            '        .expect("error while running tauri application");\n'
            '}\n'
        ),
        "src-tauri/Cargo.toml": '[package]\nname = "{{project_slug}}"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\ntauri = { version = "1", features = [] }\n\n[build-dependencies]\ntauri-build = { version = "1", features = [] }\n',
        "src/index.html": '<!doctype html>\n<html>\n<head><title>{{project_name}}</title></head>\n<body><h1>{{project_name}}</h1></body>\n</html>\n',
        "tests/placeholder.rs": '#[test]\nfn it_works() { assert!(true); }\n',
        "README.md": _readme("tauri", "Tauri desktop application.", "cargo tauri dev"),
        ".gitignore": _gitignore(_rust_gitignore + _js_gitignore),
    },
)

# ======================================================================
# GO TEMPLATES
# ======================================================================

_go_gitignore = "\n# Go\nbin/\nvendor/\n"

_go_cli = ProjectTemplate(
    name="go-cli",
    description="Go CLI application",
    category="go",
    language="go",
    framework="cobra",
    files={
        "main.go": 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Hello from {{project_name}}")\n}\n',
        "main_test.go": 'package main\n\nimport "testing"\n\nfunc TestPlaceholder(t *testing.T) {\n\tif false {\n\t\tt.Fail()\n\t}\n}\n',
        "go.mod": 'module {{project_slug}}\n\ngo 1.22\n',
        "README.md": _readme("go-cli", "A Go CLI application.", "go run ."),
        ".gitignore": _gitignore(_go_gitignore),
    },
)

_go_api_gin = ProjectTemplate(
    name="go-api-gin",
    description="Go REST API with Gin",
    category="go",
    language="go",
    framework="gin",
    files={
        "main.go": (
            'package main\n\nimport "github.com/gin-gonic/gin"\n\n'
            'func main() {\n'
            '\tr := gin.Default()\n'
            '\tr.GET("/", func(c *gin.Context) {\n'
            '\t\tc.JSON(200, gin.H{"message": "Hello from {{project_name}}"})\n'
            '\t})\n'
            '\tr.Run()\n'
            '}\n'
        ),
        "main_test.go": 'package main\n\nimport "testing"\n\nfunc TestPlaceholder(t *testing.T) {\n\tif false {\n\t\tt.Fail()\n\t}\n}\n',
        "go.mod": 'module {{project_slug}}\n\ngo 1.22\n\nrequire github.com/gin-gonic/gin v1.9.1\n',
        "README.md": _readme("go-api-gin", "Go REST API with Gin.", "go run ."),
        ".gitignore": _gitignore(_go_gitignore),
    },
)

_go_api_echo = ProjectTemplate(
    name="go-api-echo",
    description="Go REST API with Echo",
    category="go",
    language="go",
    framework="echo",
    files={
        "main.go": (
            'package main\n\nimport (\n\t"net/http"\n\t"github.com/labstack/echo/v4"\n)\n\n'
            'func main() {\n'
            '\te := echo.New()\n'
            '\te.GET("/", func(c echo.Context) error {\n'
            '\t\treturn c.JSON(http.StatusOK, map[string]string{"message": "Hello from {{project_name}}"})\n'
            '\t})\n'
            '\te.Logger.Fatal(e.Start(":1323"))\n'
            '}\n'
        ),
        "main_test.go": 'package main\n\nimport "testing"\n\nfunc TestPlaceholder(t *testing.T) {\n\tif false {\n\t\tt.Fail()\n\t}\n}\n',
        "go.mod": 'module {{project_slug}}\n\ngo 1.22\n\nrequire github.com/labstack/echo/v4 v4.12.0\n',
        "README.md": _readme("go-api-echo", "Go REST API with Echo.", "go run ."),
        ".gitignore": _gitignore(_go_gitignore),
    },
)

_go_grpc = ProjectTemplate(
    name="go-grpc",
    description="Go gRPC service",
    category="go",
    language="go",
    framework="grpc",
    files={
        "main.go": (
            'package main\n\nimport (\n\t"fmt"\n\t"log"\n\t"net"\n\t"google.golang.org/grpc"\n)\n\n'
            'func main() {\n'
            '\tlis, err := net.Listen("tcp", ":50051")\n'
            '\tif err != nil {\n\t\tlog.Fatalf("failed to listen: %v", err)\n\t}\n'
            '\ts := grpc.NewServer()\n'
            '\tfmt.Println("gRPC server listening on :50051")\n'
            '\tif err := s.Serve(lis); err != nil {\n\t\tlog.Fatalf("failed to serve: %v", err)\n\t}\n'
            '}\n'
        ),
        "main_test.go": 'package main\n\nimport "testing"\n\nfunc TestPlaceholder(t *testing.T) {\n\tif false {\n\t\tt.Fail()\n\t}\n}\n',
        "proto/service.proto": 'syntax = "proto3";\npackage {{project_slug}};\n\nservice Greeter {\n  rpc SayHello (HelloRequest) returns (HelloReply);\n}\n\nmessage HelloRequest { string name = 1; }\nmessage HelloReply { string message = 1; }\n',
        "go.mod": 'module {{project_slug}}\n\ngo 1.22\n\nrequire google.golang.org/grpc v1.63.2\n',
        "README.md": _readme("go-grpc", "Go gRPC service.", "go run ."),
        ".gitignore": _gitignore(_go_gitignore),
    },
)

# ======================================================================
# JAVA / KOTLIN TEMPLATES
# ======================================================================

_spring_boot = ProjectTemplate(
    name="spring-boot",
    description="Spring Boot REST API (Java)",
    category="java",
    language="java",
    framework="spring-boot",
    files={
        "src/main/java/com/example/app/Application.java": (
            'package com.example.app;\n\n'
            'import org.springframework.boot.SpringApplication;\n'
            'import org.springframework.boot.autoconfigure.SpringBootApplication;\n\n'
            '@SpringBootApplication\n'
            'public class Application {\n'
            '    public static void main(String[] args) {\n'
            '        SpringApplication.run(Application.class, args);\n'
            '    }\n'
            '}\n'
        ),
        "src/main/java/com/example/app/HelloController.java": (
            'package com.example.app;\n\n'
            'import org.springframework.web.bind.annotation.GetMapping;\n'
            'import org.springframework.web.bind.annotation.RestController;\n\n'
            '@RestController\n'
            'public class HelloController {\n'
            '    @GetMapping("/")\n'
            '    public String index() {\n'
            '        return "Hello from {{project_name}}";\n'
            '    }\n'
            '}\n'
        ),
        "src/test/java/com/example/app/ApplicationTests.java": (
            'package com.example.app;\n\n'
            'import org.junit.jupiter.api.Test;\n'
            'import org.springframework.boot.test.context.SpringBootTest;\n\n'
            '@SpringBootTest\n'
            'class ApplicationTests {\n'
            '    @Test\n'
            '    void contextLoads() {}\n'
            '}\n'
        ),
        "pom.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project xmlns="http://maven.apache.org/POM/4.0.0"\n'
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">\n'
            '    <modelVersion>4.0.0</modelVersion>\n'
            '    <parent>\n'
            '        <groupId>org.springframework.boot</groupId>\n'
            '        <artifactId>spring-boot-starter-parent</artifactId>\n'
            '        <version>3.2.5</version>\n'
            '    </parent>\n'
            '    <groupId>com.example</groupId>\n'
            '    <artifactId>{{project_slug}}</artifactId>\n'
            '    <version>0.1.0</version>\n'
            '    <dependencies>\n'
            '        <dependency>\n'
            '            <groupId>org.springframework.boot</groupId>\n'
            '            <artifactId>spring-boot-starter-web</artifactId>\n'
            '        </dependency>\n'
            '        <dependency>\n'
            '            <groupId>org.springframework.boot</groupId>\n'
            '            <artifactId>spring-boot-starter-test</artifactId>\n'
            '            <scope>test</scope>\n'
            '        </dependency>\n'
            '    </dependencies>\n'
            '</project>\n'
        ),
        "README.md": _readme("spring-boot", "Spring Boot REST API.", "mvn spring-boot:run"),
        ".gitignore": _gitignore("\n# Java\ntarget/\n*.class\n*.jar\n.gradle/\n"),
    },
)

_android_kotlin = ProjectTemplate(
    name="android-kotlin",
    description="Android app with Kotlin and Jetpack Compose",
    category="kotlin",
    language="kotlin",
    framework="android",
    files={
        "app/src/main/java/com/example/app/MainActivity.kt": (
            'package com.example.app\n\n'
            'import android.os.Bundle\n'
            'import androidx.activity.ComponentActivity\n'
            'import androidx.activity.compose.setContent\n'
            'import androidx.compose.material3.Text\n\n'
            'class MainActivity : ComponentActivity() {\n'
            '    override fun onCreate(savedInstanceState: Bundle?) {\n'
            '        super.onCreate(savedInstanceState)\n'
            '        setContent { Text("Hello from {{project_name}}") }\n'
            '    }\n'
            '}\n'
        ),
        "app/src/test/java/com/example/app/ExampleUnitTest.kt": (
            'package com.example.app\n\nimport org.junit.Test\nimport org.junit.Assert.*\n\n'
            'class ExampleUnitTest {\n'
            '    @Test\n'
            '    fun addition_isCorrect() {\n'
            '        assertEquals(4, 2 + 2)\n'
            '    }\n'
            '}\n'
        ),
        "app/build.gradle.kts": (
            'plugins {\n    id("com.android.application")\n    id("org.jetbrains.kotlin.android")\n}\n\n'
            'android {\n    namespace = "com.example.app"\n    compileSdk = 34\n'
            '    defaultConfig {\n        applicationId = "com.example.{{project_slug}}"\n'
            '        minSdk = 26\n        targetSdk = 34\n    }\n}\n\n'
            'dependencies {\n'
            '    implementation("androidx.activity:activity-compose:1.9.0")\n'
            '    implementation("androidx.compose.material3:material3:1.2.1")\n'
            '    testImplementation("junit:junit:4.13.2")\n'
            '}\n'
        ),
        "settings.gradle.kts": 'rootProject.name = "{{project_name}}"\ninclude(":app")\n',
        "README.md": _readme("android-kotlin", "Android app with Kotlin + Compose.", "./gradlew assembleDebug"),
        ".gitignore": _gitignore("\n# Android\nbuild/\n.gradle/\nlocal.properties\n*.apk\n"),
    },
)

_compose_desktop = ProjectTemplate(
    name="compose-desktop",
    description="Compose Multiplatform desktop app (Kotlin)",
    category="kotlin",
    language="kotlin",
    framework="compose-desktop",
    files={
        "src/main/kotlin/Main.kt": (
            'import androidx.compose.material.Text\n'
            'import androidx.compose.ui.window.Window\n'
            'import androidx.compose.ui.window.application\n\n'
            'fun main() = application {\n'
            '    Window(onCloseRequest = ::exitApplication, title = "{{project_name}}") {\n'
            '        Text("Hello from {{project_name}}")\n'
            '    }\n'
            '}\n'
        ),
        "src/test/kotlin/MainTest.kt": 'import org.junit.Test\nimport kotlin.test.assertTrue\n\nclass MainTest {\n    @Test\n    fun placeholder() {\n        assertTrue(true)\n    }\n}\n',
        "build.gradle.kts": (
            'plugins {\n    kotlin("jvm") version "1.9.23"\n'
            '    id("org.jetbrains.compose") version "1.6.2"\n}\n\n'
            'dependencies {\n    implementation(compose.desktop.currentOs)\n'
            '    testImplementation(kotlin("test"))\n}\n\n'
            'compose.desktop {\n    application {\n'
            '        mainClass = "MainKt"\n    }\n}\n'
        ),
        "settings.gradle.kts": 'rootProject.name = "{{project_name}}"\n',
        "README.md": _readme("compose-desktop", "Compose Multiplatform desktop app.", "./gradlew run"),
        ".gitignore": _gitignore("\nbuild/\n.gradle/\n"),
    },
)

# ======================================================================
# C / C++ TEMPLATES
# ======================================================================

_cmake_project = ProjectTemplate(
    name="cmake-project",
    description="C/C++ project with CMake",
    category="c-cpp",
    language="c++",
    framework="cmake",
    files={
        "src/main.cpp": '#include <iostream>\n\nint main() {\n    std::cout << "Hello from {{project_name}}" << std::endl;\n    return 0;\n}\n',
        "tests/test_main.cpp": '#include <cassert>\n\nint main() {\n    assert(1 + 1 == 2);\n    return 0;\n}\n',
        "CMakeLists.txt": (
            'cmake_minimum_required(VERSION 3.20)\n'
            'project({{project_slug}} VERSION 0.1.0 LANGUAGES CXX)\n\n'
            'set(CMAKE_CXX_STANDARD 20)\n'
            'set(CMAKE_CXX_STANDARD_REQUIRED ON)\n\n'
            'add_executable(${PROJECT_NAME} src/main.cpp)\n\n'
            'enable_testing()\n'
            'add_executable(tests tests/test_main.cpp)\n'
            'add_test(NAME tests COMMAND tests)\n'
        ),
        "README.md": _readme("cmake-project", "C++ project with CMake.", "cmake -B build && cmake --build build"),
        ".gitignore": _gitignore("\n# C/C++\nbuild/\n*.o\n*.a\n*.so\n*.dylib\n"),
    },
)

_arduino = ProjectTemplate(
    name="arduino",
    description="Arduino sketch project",
    category="c-cpp",
    language="c++",
    framework="arduino",
    files={
        "src/main.ino": (
            'void setup() {\n'
            '    Serial.begin(115200);\n'
            '    Serial.println("{{project_name}} started");\n'
            '    pinMode(LED_BUILTIN, OUTPUT);\n'
            '}\n\n'
            'void loop() {\n'
            '    digitalWrite(LED_BUILTIN, HIGH);\n'
            '    delay(1000);\n'
            '    digitalWrite(LED_BUILTIN, LOW);\n'
            '    delay(1000);\n'
            '}\n'
        ),
        "tests/test_placeholder.cpp": '#include <cassert>\n\nint main() {\n    assert(true);\n    return 0;\n}\n',
        "platformio.ini": '[env:uno]\nplatform = atmelavr\nboard = uno\nframework = arduino\nmonitor_speed = 115200\n',
        "README.md": _readme("arduino", "Arduino sketch project.", "pio run --target upload"),
        ".gitignore": _gitignore("\n.pio/\n.vscode/\n"),
    },
)

_embedded_zephyr = ProjectTemplate(
    name="embedded-zephyr",
    description="Zephyr RTOS embedded project",
    category="c-cpp",
    language="c",
    framework="zephyr",
    files={
        "src/main.c": (
            '#include <zephyr/kernel.h>\n'
            '#include <zephyr/sys/printk.h>\n\n'
            'int main(void) {\n'
            '    printk("{{project_name}} started\\n");\n'
            '    while (1) {\n'
            '        k_msleep(1000);\n'
            '    }\n'
            '    return 0;\n'
            '}\n'
        ),
        "tests/test_placeholder.c": '#include <assert.h>\n\nint main(void) {\n    assert(1);\n    return 0;\n}\n',
        "CMakeLists.txt": 'cmake_minimum_required(VERSION 3.20.0)\nfind_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})\nproject({{project_slug}})\n\ntarget_sources(app PRIVATE src/main.c)\n',
        "prj.conf": '# Zephyr project configuration\nCONFIG_PRINTK=y\nCONFIG_LOG=y\n',
        "README.md": _readme("embedded-zephyr", "Zephyr RTOS embedded project.", "west build -b <board>"),
        ".gitignore": _gitignore("\nbuild/\n"),
    },
)

# ======================================================================
# SWIFT TEMPLATES
# ======================================================================

_ios_swiftui = ProjectTemplate(
    name="ios-swiftui",
    description="iOS app with SwiftUI",
    category="swift",
    language="swift",
    framework="swiftui",
    files={
        "Sources/App.swift": (
            'import SwiftUI\n\n'
            '@main\n'
            'struct MainApp: App {\n'
            '    var body: some Scene {\n'
            '        WindowGroup {\n'
            '            ContentView()\n'
            '        }\n'
            '    }\n'
            '}\n'
        ),
        "Sources/ContentView.swift": (
            'import SwiftUI\n\n'
            'struct ContentView: View {\n'
            '    var body: some View {\n'
            '        VStack {\n'
            '            Text("{{project_name}}")\n'
            '                .font(.largeTitle)\n'
            '        }\n'
            '        .padding()\n'
            '    }\n'
            '}\n'
        ),
        "Tests/ContentViewTests.swift": (
            'import XCTest\n'
            '@testable import {{project_slug}}\n\n'
            'final class ContentViewTests: XCTestCase {\n'
            '    func testPlaceholder() {\n'
            '        XCTAssertTrue(true)\n'
            '    }\n'
            '}\n'
        ),
        "Package.swift": (
            '// swift-tools-version: 5.9\n'
            'import PackageDescription\n\n'
            'let package = Package(\n'
            '    name: "{{project_name}}",\n'
            '    platforms: [.iOS(.v17)],\n'
            '    targets: [\n'
            '        .executableTarget(name: "{{project_slug}}", path: "Sources"),\n'
            '        .testTarget(name: "{{project_slug}}Tests", dependencies: ["{{project_slug}}"], path: "Tests"),\n'
            '    ]\n'
            ')\n'
        ),
        "README.md": _readme("ios-swiftui", "iOS app with SwiftUI.", "open in Xcode and run"),
        ".gitignore": _gitignore("\n# Swift\n.build/\n*.xcodeproj/\nDerivedData/\n"),
    },
)

_macos_app = ProjectTemplate(
    name="macos-app",
    description="macOS app with SwiftUI",
    category="swift",
    language="swift",
    framework="swiftui",
    files={
        "Sources/App.swift": (
            'import SwiftUI\n\n'
            '@main\nstruct MainApp: App {\n'
            '    var body: some Scene {\n'
            '        WindowGroup {\n'
            '            Text("{{project_name}}")\n'
            '                .frame(width: 400, height: 300)\n'
            '        }\n'
            '    }\n'
            '}\n'
        ),
        "Tests/AppTests.swift": 'import XCTest\n\nfinal class AppTests: XCTestCase {\n    func testPlaceholder() {\n        XCTAssertTrue(true)\n    }\n}\n',
        "Package.swift": (
            '// swift-tools-version: 5.9\nimport PackageDescription\n\n'
            'let package = Package(\n'
            '    name: "{{project_name}}",\n'
            '    platforms: [.macOS(.v14)],\n'
            '    targets: [\n'
            '        .executableTarget(name: "{{project_slug}}", path: "Sources"),\n'
            '        .testTarget(name: "{{project_slug}}Tests", path: "Tests"),\n'
            '    ]\n'
            ')\n'
        ),
        "README.md": _readme("macos-app", "macOS app with SwiftUI.", "swift run"),
        ".gitignore": _gitignore("\n.build/\nDerivedData/\n"),
    },
)

_vapor = ProjectTemplate(
    name="vapor",
    description="Vapor server-side Swift API",
    category="swift",
    language="swift",
    framework="vapor",
    files={
        "Sources/App/configure.swift": 'import Vapor\n\npublic func configure(_ app: Application) throws {\n    try routes(app)\n}\n',
        "Sources/App/routes.swift": (
            'import Vapor\n\n'
            'func routes(_ app: Application) throws {\n'
            '    app.get { req in\n'
            '        return "Hello from {{project_name}}"\n'
            '    }\n'
            '    app.get("health") { req in\n'
            '        return ["status": "ok"]\n'
            '    }\n'
            '}\n'
        ),
        "Sources/Run/main.swift": 'import App\nimport Vapor\n\nvar env = try Environment.detect()\nlet app = Application(env)\ndefer { app.shutdown() }\ntry configure(app)\ntry app.run()\n',
        "Tests/AppTests/RouteTests.swift": 'import XCTest\n@testable import App\nimport XCTVapor\n\nfinal class RouteTests: XCTestCase {\n    func testIndex() throws {\n        let app = Application(.testing)\n        defer { app.shutdown() }\n        try configure(app)\n        try app.test(.GET, "/") { res in\n            XCTAssertEqual(res.status, .ok)\n        }\n    }\n}\n',
        "Package.swift": (
            '// swift-tools-version: 5.9\nimport PackageDescription\n\n'
            'let package = Package(\n'
            '    name: "{{project_name}}",\n'
            '    platforms: [.macOS(.v13)],\n'
            '    dependencies: [\n'
            '        .package(url: "https://github.com/vapor/vapor.git", from: "4.92.0"),\n'
            '    ],\n'
            '    targets: [\n'
            '        .target(name: "App", dependencies: [.product(name: "Vapor", package: "vapor")], path: "Sources/App"),\n'
            '        .executableTarget(name: "Run", dependencies: ["App"], path: "Sources/Run"),\n'
            '        .testTarget(name: "AppTests", dependencies: ["App", .product(name: "XCTVapor", package: "vapor")], path: "Tests/AppTests"),\n'
            '    ]\n'
            ')\n'
        ),
        "README.md": _readme("vapor", "Vapor server-side Swift API.", "swift run Run"),
        ".gitignore": _gitignore("\n.build/\nPackage.resolved\n"),
    },
)

# ======================================================================
# C# / .NET TEMPLATES
# ======================================================================

_dotnet_api = ProjectTemplate(
    name="dotnet-api",
    description=".NET 8 minimal API",
    category="csharp",
    language="c#",
    framework="dotnet",
    files={
        "Program.cs": (
            'var builder = WebApplication.CreateBuilder(args);\n'
            'var app = builder.Build();\n\n'
            'app.MapGet("/", () => new { Message = "Hello from {{project_name}}" });\n'
            'app.MapGet("/health", () => new { Status = "ok" });\n\n'
            'app.Run();\n'
        ),
        "Tests/ApiTests.cs": (
            'using Xunit;\n\n'
            'public class ApiTests\n'
            '{\n'
            '    [Fact]\n'
            '    public void Placeholder()\n'
            '    {\n'
            '        Assert.True(true);\n'
            '    }\n'
            '}\n'
        ),
        "{{project_slug}}.csproj": (
            '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
            '  <PropertyGroup>\n'
            '    <TargetFramework>net8.0</TargetFramework>\n'
            '  </PropertyGroup>\n'
            '</Project>\n'
        ),
        "README.md": _readme("dotnet-api", ".NET 8 minimal API.", "dotnet run"),
        ".gitignore": _gitignore("\n# .NET\nbin/\nobj/\n*.user\n"),
    },
)

_blazor = ProjectTemplate(
    name="blazor",
    description="Blazor WebAssembly app",
    category="csharp",
    language="c#",
    framework="blazor",
    files={
        "Pages/Index.razor": '@page "/"\n\n<h1>{{project_name}}</h1>\n<p>Welcome to Blazor.</p>\n',
        "Program.cs": 'using Microsoft.AspNetCore.Components.WebAssembly.Hosting;\n\nvar builder = WebAssemblyHostBuilder.CreateDefault(args);\nawait builder.Build().RunAsync();\n',
        "Tests/IndexTests.cs": 'using Xunit;\n\npublic class IndexTests\n{\n    [Fact]\n    public void Placeholder() => Assert.True(true);\n}\n',
        "{{project_slug}}.csproj": '<Project Sdk="Microsoft.NET.Sdk.BlazorWebAssembly">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n',
        "README.md": _readme("blazor", "Blazor WebAssembly app.", "dotnet run"),
        ".gitignore": _gitignore("\nbin/\nobj/\n"),
    },
)

_unity = ProjectTemplate(
    name="unity",
    description="Unity game project stub",
    category="csharp",
    language="c#",
    framework="unity",
    files={
        "Assets/Scripts/GameManager.cs": (
            'using UnityEngine;\n\n'
            'public class GameManager : MonoBehaviour\n'
            '{\n'
            '    void Start()\n'
            '    {\n'
            '        Debug.Log("{{project_name}} started");\n'
            '    }\n\n'
            '    void Update() { }\n'
            '}\n'
        ),
        "Assets/Tests/EditMode/GameManagerTests.cs": (
            'using NUnit.Framework;\n\n'
            'public class GameManagerTests\n'
            '{\n'
            '    [Test]\n'
            '    public void Placeholder()\n'
            '    {\n'
            '        Assert.IsTrue(true);\n'
            '    }\n'
            '}\n'
        ),
        "ProjectSettings/ProjectVersion.txt": 'm_EditorVersion: 2023.2.0f1\n',
        "README.md": _readme("unity", "Unity game project.", "Open in Unity Editor"),
        ".gitignore": _gitignore("\n# Unity\n[Ll]ibrary/\n[Tt]emp/\n[Oo]bj/\n[Bb]uild/\n*.csproj\n*.sln\n*.pidb\n*.userprefs\n"),
    },
)

# ======================================================================
# DART / FLUTTER TEMPLATES
# ======================================================================

_flutter_app = ProjectTemplate(
    name="flutter-app",
    description="Flutter cross-platform app",
    category="dart",
    language="dart",
    framework="flutter",
    files={
        "lib/main.dart": (
            'import \'package:flutter/material.dart\';\n\n'
            'void main() => runApp(const MyApp());\n\n'
            'class MyApp extends StatelessWidget {\n'
            '  const MyApp({super.key});\n\n'
            '  @override\n'
            '  Widget build(BuildContext context) {\n'
            '    return MaterialApp(\n'
            '      title: \'{{project_name}}\',\n'
            '      home: const Scaffold(\n'
            '        body: Center(child: Text(\'{{project_name}}\')),\n'
            '      ),\n'
            '    );\n'
            '  }\n'
            '}\n'
        ),
        "test/widget_test.dart": (
            'import \'package:flutter_test/flutter_test.dart\';\n'
            'import \'package:{{project_slug}}/main.dart\';\n\n'
            'void main() {\n'
            '  testWidgets(\'app renders\', (WidgetTester tester) async {\n'
            '    await tester.pumpWidget(const MyApp());\n'
            '    expect(find.text(\'{{project_name}}\'), findsOneWidget);\n'
            '  });\n'
            '}\n'
        ),
        "pubspec.yaml": (
            'name: {{project_slug}}\n'
            'description: {{project_name}}\n'
            'version: 0.1.0\n\n'
            'environment:\n  sdk: ">=3.3.0 <4.0.0"\n\n'
            'dependencies:\n  flutter:\n    sdk: flutter\n\n'
            'dev_dependencies:\n  flutter_test:\n    sdk: flutter\n'
        ),
        "README.md": _readme("flutter-app", "Flutter cross-platform app.", "flutter run"),
        ".gitignore": _gitignore("\n# Flutter\nbuild/\n.dart_tool/\n.flutter-plugins\n.packages\n"),
    },
)

_dart_package = ProjectTemplate(
    name="dart-package",
    description="Dart library package",
    category="dart",
    language="dart",
    framework="dart",
    files={
        "lib/{{project_slug}}.dart": (
            '/// {{project_name}} library.\n'
            'library {{project_slug}};\n\n'
            'String greet(String name) => \'Hello, $name!\';\n'
        ),
        "test/{{project_slug}}_test.dart": (
            'import \'package:test/test.dart\';\n'
            'import \'package:{{project_slug}}/{{project_slug}}.dart\';\n\n'
            'void main() {\n'
            '  test(\'greet\', () {\n'
            '    expect(greet(\'World\'), equals(\'Hello, World!\'));\n'
            '  });\n'
            '}\n'
        ),
        "pubspec.yaml": 'name: {{project_slug}}\ndescription: {{project_name}}\nversion: 0.1.0\n\nenvironment:\n  sdk: ">=3.3.0 <4.0.0"\n\ndev_dependencies:\n  test: ^1.25.0\n',
        "README.md": _readme("dart-package", "Dart library package.", "dart test"),
        ".gitignore": _gitignore("\n.dart_tool/\n.packages\nbuild/\npubspec.lock\n"),
    },
)


# ======================================================================
# Master list
# ======================================================================

_ALL_TEMPLATES: list[ProjectTemplate] = [
    # Python (7)
    _fastapi, _flask, _django, _cli_click, _cli_typer, _library_setuptools, _library_poetry,
    # JavaScript/TypeScript (10)
    _react, _nextjs, _vue, _nuxt, _svelte, _angular, _express, _nestjs, _electron, _react_native,
    # Rust (5)
    _rust_binary, _rust_library, _actix_web, _axum, _tauri,
    # Go (4)
    _go_cli, _go_api_gin, _go_api_echo, _go_grpc,
    # Java/Kotlin (3)
    _spring_boot, _android_kotlin, _compose_desktop,
    # C/C++ (3)
    _cmake_project, _arduino, _embedded_zephyr,
    # Swift (3)
    _ios_swiftui, _macos_app, _vapor,
    # C# (3)
    _dotnet_api, _blazor, _unity,
    # Dart (2)
    _flutter_app, _dart_package,
]
