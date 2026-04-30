"""AI subpackage — LLM client, design agent, smart chat, generator, simulator, and AI dev tools."""

from eostudio.core.ai.llm_client import LLMClient, LLMConfig
from eostudio.core.ai.agent import DesignAgent
from eostudio.core.ai.smart_chat import SmartChat, EditorContext, ChatResponse
from eostudio.core.ai.generator import AIDesignGenerator
from eostudio.core.ai.simulator import AISimulator
from eostudio.core.ai.tutor import KidsTutor
from eostudio.core.ai.code_assistant import CodeAssistant, CodeSuggestion
from eostudio.core.ai.chat_panel import ChatPanel, ChatMessage, ChatSession
from eostudio.core.ai.code_review import CodeReviewer, ReviewResult, ReviewComment
from eostudio.core.ai.test_generator import TestGenerator, TestCase
from eostudio.core.ai.doc_generator import DocGenerator

__all__ = [
    "LLMClient", "LLMConfig", "DesignAgent",
    "SmartChat", "EditorContext", "ChatResponse",
    "AIDesignGenerator", "AISimulator", "KidsTutor",
    "CodeAssistant", "CodeSuggestion",
    "ChatPanel", "ChatMessage", "ChatSession",
    "CodeReviewer", "ReviewResult", "ReviewComment",
    "TestGenerator", "TestCase",
    "DocGenerator",
]