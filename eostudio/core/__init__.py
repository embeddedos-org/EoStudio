"""EoStudio core modules — geometry, simulation, AI, UML, IDE."""

from eostudio.core.geometry.primitives import (
    Vec2, Vec3, Vec4, Matrix4, BoundingBox, Face, Mesh,
    create_cube, create_sphere, create_cylinder, create_cone, create_torus, create_plane,
)
from eostudio.core.geometry.transforms import Quaternion, Transform
from eostudio.core.geometry.curves import BezierCurve, BSplineCurve

from eostudio.core.simulation.engine import (
    Signal, Block, SourceBlock, GainBlock, SumBlock, PIDBlock, ScopeBlock, SimulationModel,
)

from eostudio.core.ai.llm_client import LLMClient, LLMConfig
from eostudio.core.ai.agent import DesignAgent
from eostudio.core.ai.smart_chat import SmartChat, EditorContext, ChatResponse
from eostudio.core.ai.generator import AIDesignGenerator
from eostudio.core.ai.simulator import AISimulator

from eostudio.core.uml.diagrams import UMLClass, UMLRelation, UMLDiagram, ClassDiagram
from eostudio.core.uml.code_gen import UMLCodeGen

__all__ = [
    "Vec2", "Vec3", "Vec4", "Matrix4", "BoundingBox", "Face", "Mesh",
    "create_cube", "create_sphere", "create_cylinder", "create_cone", "create_torus", "create_plane",
    "Quaternion", "Transform", "BezierCurve", "BSplineCurve",
    "Signal", "Block", "SourceBlock", "GainBlock", "SumBlock", "PIDBlock", "ScopeBlock", "SimulationModel",
    "LLMClient", "LLMConfig", "DesignAgent", "SmartChat", "EditorContext", "ChatResponse",
    "AIDesignGenerator", "AISimulator",
    "UMLClass", "UMLRelation", "UMLDiagram", "ClassDiagram", "UMLCodeGen",
]
