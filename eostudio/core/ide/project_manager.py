"""Project manager (stub)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ProjectManager:
    def __init__(self) -> None:
        self._projects: Dict[str, Any] = {}
        self.current_project: Optional[str] = None

    def create(self, name: str, path: str) -> Dict[str, Any]:
        project = {"name": name, "path": path}
        self._projects[name] = project
        return project

    def open(self, name: str) -> bool:
        if name in self._projects:
            self.current_project = name
            return True
        return False

    def list_projects(self) -> List[str]:
        return list(self._projects.keys())
