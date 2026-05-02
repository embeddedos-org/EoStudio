"""Tech Spec — components, APIs, data models, implementation details."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TechDataModel:
    """A data model/entity in the tech spec."""
    name: str
    fields: List[Dict[str, str]] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "fields": self.fields,
                "relationships": self.relationships, "description": self.description}

    def to_markdown(self) -> str:
        lines = [f"#### {self.name}", self.description, ""]
        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for f in self.fields:
            lines.append(f"| {f.get('name','')} | {f.get('type','')} | {f.get('description','')} |")
        return "\n".join(lines)


@dataclass
class TechAPI:
    """An API endpoint in the tech spec."""
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str = ""
    request_body: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    rate_limit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.method, "path": self.path, "description": self.description,
                "request_body": self.request_body, "response": self.response,
                "auth_required": self.auth_required}

    def to_markdown(self) -> str:
        auth = "Auth required" if self.auth_required else "Public"
        return f"- `{self.method} {self.path}` — {self.description} ({auth})"


@dataclass
class TechComponent:
    """A system component (service, module, package)."""
    name: str
    description: str = ""
    tech_stack: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    apis: List[TechAPI] = field(default_factory=list)
    data_models: List[TechDataModel] = field(default_factory=list)
    file_structure: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "description": self.description,
            "tech_stack": self.tech_stack, "responsibilities": self.responsibilities,
            "dependencies": self.dependencies,
            "apis": [a.to_dict() for a in self.apis],
            "data_models": [d.to_dict() for d in self.data_models],
            "file_structure": self.file_structure,
        }

    def to_markdown(self) -> str:
        lines = [f"### {self.name}", self.description, "",
                 f"**Stack:** {', '.join(self.tech_stack)}", "",
                 "**Responsibilities:**", *[f"- {r}" for r in self.responsibilities]]
        if self.apis:
            lines.extend(["", "**APIs:**", *[a.to_markdown() for a in self.apis]])
        if self.data_models:
            lines.extend(["", "**Data Models:**", *[d.to_markdown() for d in self.data_models]])
        if self.file_structure:
            lines.extend(["", "**Files:**", "```", *self.file_structure, "```"])
        return "\n".join(lines)


@dataclass
class TechSpec:
    """Complete technical specification."""
    project_name: str
    version: str = "1.0"
    architecture_overview: str = ""
    tech_stack: Dict[str, List[str]] = field(default_factory=dict)
    components: List[TechComponent] = field(default_factory=list)
    infrastructure: Dict[str, Any] = field(default_factory=dict)
    security: List[str] = field(default_factory=list)
    performance_targets: Dict[str, str] = field(default_factory=dict)
    testing_strategy: Dict[str, str] = field(default_factory=dict)
    deployment: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, name: str, description: str = "", **kwargs: Any) -> TechComponent:
        comp = TechComponent(name=name, description=description, **kwargs)
        self.components.append(comp)
        return comp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name, "version": self.version,
            "architecture_overview": self.architecture_overview,
            "tech_stack": self.tech_stack,
            "components": [c.to_dict() for c in self.components],
            "infrastructure": self.infrastructure, "security": self.security,
            "performance_targets": self.performance_targets,
            "testing_strategy": self.testing_strategy, "deployment": self.deployment,
        }

    def to_markdown(self) -> str:
        lines = [f"# Tech Spec: {self.project_name} v{self.version}", "",
                 "## Architecture", self.architecture_overview, ""]
        if self.tech_stack:
            lines.append("## Tech Stack")
            for cat, items in self.tech_stack.items():
                lines.append(f"- **{cat}:** {', '.join(items)}")
            lines.append("")
        lines.append("## Components")
        for comp in self.components:
            lines.append(comp.to_markdown())
            lines.append("")
        if self.security:
            lines.extend(["## Security", *[f"- {s}" for s in self.security], ""])
        if self.performance_targets:
            lines.append("## Performance Targets")
            for k, v in self.performance_targets.items():
                lines.append(f"- **{k}:** {v}")
        if self.testing_strategy:
            lines.extend(["", "## Testing Strategy"])
            for k, v in self.testing_strategy.items():
                lines.append(f"- **{k}:** {v}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TechSpec":
        spec = cls(project_name=data["project_name"], version=data.get("version", "1.0"),
                   architecture_overview=data.get("architecture_overview", ""),
                   tech_stack=data.get("tech_stack", {}),
                   infrastructure=data.get("infrastructure", {}),
                   security=data.get("security", []),
                   performance_targets=data.get("performance_targets", {}),
                   testing_strategy=data.get("testing_strategy", {}),
                   deployment=data.get("deployment", {}))
        for c in data.get("components", []):
            comp = TechComponent(name=c["name"], description=c.get("description", ""),
                                 tech_stack=c.get("tech_stack", []),
                                 responsibilities=c.get("responsibilities", []),
                                 file_structure=c.get("file_structure", []))
            spec.components.append(comp)
        return spec
