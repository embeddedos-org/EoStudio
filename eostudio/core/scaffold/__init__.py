"""Scaffolding subpackage — project templates and scaffolder."""

from eostudio.core.scaffold.scaffolder import Scaffolder, ScaffoldConfig
from eostudio.core.scaffold.templates import TemplateRegistry, ProjectTemplate

__all__ = ["Scaffolder", "ScaffoldConfig", "TemplateRegistry", "ProjectTemplate"]
