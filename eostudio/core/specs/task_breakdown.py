"""Task Breakdown — converts specs into actionable implementation tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass
class Task:
    """A single implementation task."""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    requirement_id: str = ""
    component: str = ""
    files_to_create: List[str] = field(default_factory=list)
    files_to_modify: List[str] = field(default_factory=list)
    tests_needed: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    assignee: str = ""
    effort: str = "M"  # S, M, L, XL
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def complete(self) -> None:
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "status": self.status.value, "requirement_id": self.requirement_id,
            "component": self.component, "files_to_create": self.files_to_create,
            "files_to_modify": self.files_to_modify, "tests_needed": self.tests_needed,
            "depends_on": self.depends_on, "effort": self.effort,
        }

    def to_markdown(self) -> str:
        check = "x" if self.status == TaskStatus.DONE else " "
        lines = [f"- [{check}] **{self.id}**: {self.title} [{self.effort}]"]
        if self.files_to_create:
            lines.append(f"  - Create: {', '.join(self.files_to_create)}")
        if self.files_to_modify:
            lines.append(f"  - Modify: {', '.join(self.files_to_modify)}")
        if self.tests_needed:
            lines.append(f"  - Tests: {', '.join(self.tests_needed)}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**{k: TaskStatus(v) if k == "status" else v
                      for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TaskBreakdown:
    """A collection of tasks derived from specs."""
    project_name: str
    tasks: List[Task] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)

    def add_task(self, title: str, **kwargs: Any) -> Task:
        task_id = f"T-{len(self.tasks) + 1:03d}"
        task = Task(id=task_id, title=title, **kwargs)
        self.tasks.append(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return next((t for t in self.tasks if t.id == task_id), None)

    def by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.tasks if t.status == status]

    def by_component(self, component: str) -> List[Task]:
        return [t for t in self.tasks if t.component == component]

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        done = len([t for t in self.tasks if t.status == TaskStatus.DONE])
        return done / len(self.tasks) * 100

    def next_tasks(self) -> List[Task]:
        """Get tasks that are ready to work on (no unmet dependencies)."""
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        return [t for t in self.tasks if t.status == TaskStatus.TODO
                and all(d in done_ids for d in t.depends_on)]

    def add_milestone(self, name: str, task_ids: List[str], deadline: str = "") -> None:
        self.milestones.append({"name": name, "tasks": task_ids, "deadline": deadline})

    def to_dict(self) -> Dict[str, Any]:
        return {"project": self.project_name,
                "tasks": [t.to_dict() for t in self.tasks],
                "milestones": self.milestones,
                "progress": self.progress}

    def to_markdown(self) -> str:
        lines = [f"# Task Breakdown: {self.project_name}",
                 f"\nProgress: {self.progress:.0f}% ({len(self.by_status(TaskStatus.DONE))}/{len(self.tasks)})\n"]
        components = sorted(set(t.component for t in self.tasks if t.component))
        for comp in components:
            lines.append(f"\n## {comp}")
            for task in self.by_component(comp):
                lines.append(task.to_markdown())
        uncategorized = [t for t in self.tasks if not t.component]
        if uncategorized:
            lines.append("\n## Other")
            for task in uncategorized:
                lines.append(task.to_markdown())
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskBreakdown":
        tb = cls(project_name=data.get("project", ""))
        for t in data.get("tasks", []):
            tb.tasks.append(Task.from_dict(t))
        tb.milestones = data.get("milestones", [])
        return tb
