"""AI subpackage — LLM client, design agent, smart chat, generator, simulator."""

from eostudio.core.ai.llm_client import LLMClient, LLMConfig
from eostudio.core.ai.agent import DesignAgent
from eostudio.core.ai.smart_chat import SmartChat, EditorContext, ChatResponse
from eostudio.core.ai.generator import AIDesignGenerator
from eostudio.core.ai.simulator import AISimulator
from eostudio.core.ai.tutor import KidsTutor

__all__ = [
    "LLMClient", "LLMConfig", "DesignAgent",
    "SmartChat", "EditorContext", "ChatResponse",
    "AIDesignGenerator", "AISimulator", "KidsTutor",
]
