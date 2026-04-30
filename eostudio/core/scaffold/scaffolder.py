"""
EoStudio Scaffolder — template engine for project scaffolding.

Phase 3: Cross-Platform Universal Support.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from eostudio.core.scaffold.templates import ProjectTemplate, TemplateRegistry


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScaffoldConfig:
    """Configuration for creating a new project from a template."""

    name: str
    template: str
    output_dir: str
    variables: Dict[str, str] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)


@dataclass
class TemplateFile:
    """A single file produced by a template."""

    path: str
    content: str
    executable: bool = False


# ---------------------------------------------------------------------------
# Scaffolder
# ---------------------------------------------------------------------------

class Scaffolder:
    """Create projects from registered templates."""

    def __init__(self) -> None:
        self._registry = TemplateRegistry()

    # -- public API ---------------------------------------------------------

    def create(self, config: ScaffoldConfig) -> str:
        """Create a project from *config* and return the output directory."""

        template = self._registry.get(config.template)
        if template is None:
            raise ValueError(f"Unknown template: {config.template!r}")

        project_dir = os.path.join(config.output_dir, config.name)
        os.makedirs(project_dir, exist_ok=True)

        variables = {
            "project_name": config.name,
            "project_slug": _slugify(config.name),
            **config.variables,
        }

        for rel_path, content_template in template.files.items():
            rendered = self.render_template(content_template, variables)
            dest = os.path.join(project_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(rendered)

        self.post_scaffold(project_dir, config)
        return project_dir

    @staticmethod
    def render_template(content: str, variables: Dict[str, str]) -> str:
        """Replace ``{{var}}`` placeholders in *content*."""

        def _replace(match: re.Match) -> str:
            key = match.group(1).strip()
            return variables.get(key, match.group(0))

        return re.sub(r"\{\{(.+?)\}\}", _replace, content)

    @staticmethod
    def post_scaffold(output_dir: str, config: ScaffoldConfig) -> None:
        """Run post-creation hooks (git init, dependency install, etc.)."""

        # git init
        if shutil.which("git"):
            subprocess.run(
                ["git", "init"],
                cwd=output_dir,
                capture_output=True,
                check=False,
            )

        # Language-specific dependency installation
        project_path = Path(output_dir)

        if (project_path / "package.json").exists() and shutil.which("npm"):
            subprocess.run(
                ["npm", "install"],
                cwd=output_dir,
                capture_output=True,
                check=False,
            )
        elif (project_path / "requirements.txt").exists() and shutil.which("pip"):
            subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=output_dir,
                capture_output=True,
                check=False,
            )
        elif (project_path / "Cargo.toml").exists() and shutil.which("cargo"):
            subprocess.run(
                ["cargo", "build"],
                cwd=output_dir,
                capture_output=True,
                check=False,
            )
        elif (project_path / "go.mod").exists() and shutil.which("go"):
            subprocess.run(
                ["go", "mod", "tidy"],
                cwd=output_dir,
                capture_output=True,
                check=False,
            )

    def list_templates(self) -> List[str]:
        """Return names of all registered templates."""
        return [t.name for t in self._registry.list()]

    def get_template(self, name: str) -> Optional[ProjectTemplate]:
        """Look up a template by *name*."""
        return self._registry.get(name)

    def create_custom_template(self, path: str, name: str) -> None:
        """Save a directory tree rooted at *path* as a reusable template."""

        files: Dict[str, str] = {}
        root = Path(path)
        for file in root.rglob("*"):
            if file.is_file() and ".git" not in file.parts:
                rel = str(file.relative_to(root))
                try:
                    files[rel] = file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue  # skip binary files

        template = ProjectTemplate(
            name=name,
            description=f"Custom template created from {path}",
            category="custom",
            language="mixed",
            framework="custom",
            files=files,
        )
        self._registry.register(template)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(value: str) -> str:
    """Convert *value* to a filesystem-safe slug."""
    slug = value.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")
