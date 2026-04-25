"""Spec Engine — Requirements → Design Spec → Tech Spec → Tasks, like Kiro.dev."""

from eostudio.core.specs.requirement import Requirement, RequirementType, RequirementPriority
from eostudio.core.specs.design_spec import DesignSpec, DesignSection
from eostudio.core.specs.tech_spec import TechSpec, TechComponent, TechAPI, TechDataModel
from eostudio.core.specs.task_breakdown import TaskBreakdown, Task, TaskStatus
from eostudio.core.specs.spec_engine import SpecEngine

__all__ = [
    "Requirement", "RequirementType", "RequirementPriority",
    "DesignSpec", "DesignSection",
    "TechSpec", "TechComponent", "TechAPI", "TechDataModel",
    "TaskBreakdown", "Task", "TaskStatus",
    "SpecEngine",
]
