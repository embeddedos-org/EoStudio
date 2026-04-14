"""UML diagram model — classes, relations, diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UMLClass:
    name: str = ""
    attributes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    stereotype: str = ""
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "attributes": self.attributes,
            "methods": self.methods,
            "stereotype": self.stereotype,
            "x": self.x,
            "y": self.y,
        }


@dataclass
class UMLRelation:
    source: str = ""
    target: str = ""
    relation_type: str = "association"
    label: str = ""
    source_multiplicity: str = ""
    target_multiplicity: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "label": self.label,
            "source_multiplicity": self.source_multiplicity,
            "target_multiplicity": self.target_multiplicity,
        }


@dataclass
class UMLDiagram:
    name: str = ""
    diagram_type: str = "class"
    classes: List[UMLClass] = field(default_factory=list)
    relations: List[UMLRelation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "diagram_type": self.diagram_type,
            "classes": [c.to_dict() for c in self.classes],
            "relations": [r.to_dict() for r in self.relations],
        }


class ClassDiagram(UMLDiagram):
    def __init__(self, name: str = "", **kwargs: Any) -> None:
        super().__init__(name=name, diagram_type="class", **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClassDiagram:
        diagram = cls(name=data.get("name", ""))
        for c in data.get("classes", []):
            diagram.classes.append(UMLClass(
                name=c.get("name", ""),
                attributes=c.get("attributes", []),
                methods=c.get("methods", []),
                stereotype=c.get("stereotype", ""),
                x=c.get("x", 0.0),
                y=c.get("y", 0.0),
            ))
        for r in data.get("relations", []):
            diagram.relations.append(UMLRelation(
                source=r.get("source", ""),
                target=r.get("target", ""),
                relation_type=r.get("relation_type", "association"),
                label=r.get("label", ""),
            ))
        return diagram
