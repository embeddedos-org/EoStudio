"""Design Spec — high-level architecture, user flows, wireframes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DesignSection:
    """A section of the design spec (e.g., Architecture, User Flows, Data Model)."""
    title: str
    content: str
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    wireframes: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "content": self.content,
                "diagrams": self.diagrams, "wireframes": self.wireframes, "notes": self.notes}

    def to_markdown(self) -> str:
        lines = [f"## {self.title}", "", self.content]
        for note in self.notes:
            lines.append(f"\n> {note}")
        return "\n".join(lines)


@dataclass
class DesignSpec:
    """Complete design specification document."""
    project_name: str
    version: str = "1.0"
    overview: str = ""
    goals: List[str] = field(default_factory=list)
    non_goals: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)
    sections: List[DesignSection] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    risks: List[Dict[str, str]] = field(default_factory=list)

    def add_section(self, title: str, content: str) -> DesignSection:
        section = DesignSection(title=title, content=content)
        self.sections.append(section)
        return section

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name, "version": self.version,
            "overview": self.overview, "goals": self.goals,
            "non_goals": self.non_goals, "target_users": self.target_users,
            "sections": [s.to_dict() for s in self.sections],
            "open_questions": self.open_questions, "risks": self.risks,
        }

    def to_markdown(self) -> str:
        lines = [f"# Design Spec: {self.project_name} v{self.version}", "",
                 "## Overview", self.overview, "",
                 "## Goals", *[f"- {g}" for g in self.goals], "",
                 "## Non-Goals", *[f"- {g}" for g in self.non_goals], "",
                 "## Target Users", *[f"- {u}" for u in self.target_users], ""]
        for section in self.sections:
            lines.append(section.to_markdown())
            lines.append("")
        if self.open_questions:
            lines.extend(["## Open Questions", *[f"- [ ] {q}" for q in self.open_questions]])
        if self.risks:
            lines.extend(["", "## Risks"])
            for r in self.risks:
                lines.append(f"- **{r.get('risk', '')}** — Mitigation: {r.get('mitigation', 'TBD')}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignSpec":
        spec = cls(project_name=data["project_name"], version=data.get("version", "1.0"),
                   overview=data.get("overview", ""), goals=data.get("goals", []),
                   non_goals=data.get("non_goals", []), target_users=data.get("target_users", []),
                   open_questions=data.get("open_questions", []), risks=data.get("risks", []))
        for s in data.get("sections", []):
            spec.sections.append(DesignSection(**{k: v for k, v in s.items() if k in DesignSection.__dataclass_fields__}))
        return spec
