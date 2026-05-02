"""Requirements specification — user stories, acceptance criteria, priorities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RequirementType(Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    USER_STORY = "user_story"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"


class RequirementPriority(Enum):
    MUST = "must"         # P0 — must have
    SHOULD = "should"     # P1 — should have
    COULD = "could"       # P2 — nice to have
    WONT = "wont"         # P3 — won't have this release


@dataclass
class AcceptanceCriteria:
    """A single acceptance criterion for a requirement."""
    description: str
    test_method: str = "manual"  # manual, unit, integration, e2e
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"description": self.description, "test_method": self.test_method, "verified": self.verified}


@dataclass
class Requirement:
    """A single requirement/user story in the spec."""
    id: str
    title: str
    description: str
    req_type: RequirementType = RequirementType.USER_STORY
    priority: RequirementPriority = RequirementPriority.SHOULD
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: str = "draft"  # draft, approved, in_progress, done
    assignee: str = ""
    estimated_effort: str = ""  # S, M, L, XL

    def add_criteria(self, description: str, test_method: str = "manual") -> AcceptanceCriteria:
        ac = AcceptanceCriteria(description=description, test_method=test_method)
        self.acceptance_criteria.append(ac)
        return ac

    @property
    def is_complete(self) -> bool:
        return all(ac.verified for ac in self.acceptance_criteria)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "type": self.req_type.value, "priority": self.priority.value,
            "acceptance_criteria": [ac.to_dict() for ac in self.acceptance_criteria],
            "dependencies": self.dependencies, "tags": self.tags,
            "status": self.status, "assignee": self.assignee,
            "estimated_effort": self.estimated_effort,
        }

    def to_markdown(self) -> str:
        lines = [f"### {self.id}: {self.title}", "",
                 f"**Type:** {self.req_type.value} | **Priority:** {self.priority.value} | **Effort:** {self.estimated_effort}", "",
                 self.description, "", "**Acceptance Criteria:**"]
        for i, ac in enumerate(self.acceptance_criteria, 1):
            check = "x" if ac.verified else " "
            lines.append(f"- [{check}] {ac.description} ({ac.test_method})")
        if self.dependencies:
            lines.append(f"\n**Dependencies:** {', '.join(self.dependencies)}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Requirement":
        req = cls(
            id=data["id"], title=data["title"], description=data["description"],
            req_type=RequirementType(data.get("type", "user_story")),
            priority=RequirementPriority(data.get("priority", "should")),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []), status=data.get("status", "draft"),
            assignee=data.get("assignee", ""),
            estimated_effort=data.get("estimated_effort", ""),
        )
        for ac in data.get("acceptance_criteria", []):
            req.acceptance_criteria.append(AcceptanceCriteria(**ac))
        return req
