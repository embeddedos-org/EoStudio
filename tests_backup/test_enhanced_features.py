"""Tests for EoStudio v3.1 enhanced features.

Covers:
- MultiModelRouter
- InlineCompletionEngine
- AgenticCoder
- CollabSession / OTEngine
- WorkspaceIntelligence / SymbolIndex
- VoiceToCode / VoiceCommandParser
- LivePreviewEngine / FileWatcher
- PluginMarketplace
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockLLMRouter:
    """Mock router that returns preset responses."""

    def __init__(self, response: str = "mock response") -> None:
        self._response = response
        self.calls: List[Dict[str, Any]] = []

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        return self._response

    def stream(self, prompt: str, **kwargs: Any):
        yield self._response

    def select_model(self, task: Any, complexity: int = 5) -> str:
        return "gpt-4.1-mini"

    @property
    def config(self):
        cfg = MagicMock()
        cfg.primary_model = "gpt-4.1-mini"
        cfg.fallback_model = "gpt-4.1-nano"
        cfg.prefer_local = False
        cfg.max_tokens = 4096
        cfg.temperature = 0.2
        return cfg


# ---------------------------------------------------------------------------
# MultiModelRouter tests
# ---------------------------------------------------------------------------

class TestMultiModelRouter(unittest.TestCase):

    def test_model_registry_populated(self) -> None:
        from eostudio.core.ai.multi_model_router import MODEL_REGISTRY
        self.assertIn("gpt-4.1", MODEL_REGISTRY)
        self.assertIn("gpt-4.1-mini", MODEL_REGISTRY)
        self.assertIn("gpt-4.1-nano", MODEL_REGISTRY)
        self.assertIn("gemini-2.5-flash", MODEL_REGISTRY)
        self.assertIn("llama3", MODEL_REGISTRY)

    def test_select_model_code_completion(self) -> None:
        from eostudio.core.ai.multi_model_router import MultiModelRouter, RouterConfig, TaskType
        # Without API key, should fall back to local
        router = MultiModelRouter(RouterConfig(prefer_local=True))
        model = router.select_model(TaskType.CODE_COMPLETION)
        self.assertEqual(model, "llama3")

    def test_select_model_prefers_local(self) -> None:
        from eostudio.core.ai.multi_model_router import MultiModelRouter, RouterConfig, TaskType
        router = MultiModelRouter(RouterConfig(prefer_local=True))
        model = router.select_model(TaskType.AGENT_LOOP, complexity=9)
        self.assertEqual(model, "llama3")

    def test_stats_structure(self) -> None:
        from eostudio.core.ai.multi_model_router import MultiModelRouter
        router = MultiModelRouter()
        stats = router.stats()
        self.assertIn("models", stats)
        self.assertIn("config", stats)
        self.assertIn("gpt-4.1", stats["models"])

    def test_router_config_defaults(self) -> None:
        from eostudio.core.ai.multi_model_router import RouterConfig
        cfg = RouterConfig()
        self.assertEqual(cfg.primary_model, "gpt-4.1-mini")
        self.assertEqual(cfg.fallback_model, "gpt-4.1-nano")
        self.assertFalse(cfg.prefer_local)

    def test_get_router_singleton(self) -> None:
        from eostudio.core.ai.multi_model_router import get_router
        r1 = get_router()
        r2 = get_router()
        self.assertIs(r1, r2)

    def test_task_type_enum(self) -> None:
        from eostudio.core.ai.multi_model_router import TaskType
        self.assertTrue(hasattr(TaskType, "CODE_COMPLETION"))
        self.assertTrue(hasattr(TaskType, "AGENT_LOOP"))
        self.assertTrue(hasattr(TaskType, "DESIGN_BRIEF"))


# ---------------------------------------------------------------------------
# InlineCompletionEngine tests
# ---------------------------------------------------------------------------

class TestInlineCompletionEngine(unittest.TestCase):

    def _make_engine(self, response: str = "return x + y") -> Any:
        from eostudio.core.ai.inline_completion import InlineCompletionEngine
        engine = InlineCompletionEngine()
        engine._router = MockLLMRouter(response)
        return engine

    def test_complete_returns_result(self) -> None:
        from eostudio.core.ai.inline_completion import CompletionContext
        engine = self._make_engine("    return fibonacci(n-1) + fibonacci(n-2)")
        ctx = CompletionContext(
            prefix="def fibonacci(n):\n    if n <= 1:\n        return n\n    ",
            suffix="",
            language="python",
            filename="math.py",
            line_number=3,
            column=4,
        )
        result = engine.complete(ctx)
        self.assertIsNotNone(result)
        self.assertIsInstance(result.text, str)
        self.assertGreater(result.confidence, 0)

    def test_complete_short_prefix_returns_none(self) -> None:
        from eostudio.core.ai.inline_completion import CompletionContext
        engine = self._make_engine()
        ctx = CompletionContext(
            prefix="x",
            suffix="",
            language="python",
            filename="a.py",
            line_number=0,
            column=1,
        )
        result = engine.complete(ctx)
        self.assertIsNone(result)

    def test_cache_hit(self) -> None:
        from eostudio.core.ai.inline_completion import CompletionContext
        engine = self._make_engine("cached result")
        ctx = CompletionContext(
            prefix="def hello_world_function():\n    # greet the user\n    ",
            suffix="",
            language="python",
            filename="hello.py",
            line_number=2,
            column=4,
        )
        r1 = engine.complete(ctx)
        r2 = engine.complete(ctx)
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        # Second call should use cache (same result)
        self.assertEqual(r1.text, r2.text)

    def test_telemetry(self) -> None:
        engine = self._make_engine()
        engine.accept()
        engine.accept()
        engine.reject()
        self.assertAlmostEqual(engine.acceptance_rate, 2 / 3, places=2)

    def test_context_extractor_python(self) -> None:
        from eostudio.core.ai.inline_completion import ContextExtractor
        code = "import os\nimport sys\n\ndef hello():\n    pass\n"
        ctx = ContextExtractor.extract(code, len(code), "python", "test.py")
        self.assertEqual(ctx.language, "python")
        self.assertIn("os", ctx.imports)
        self.assertIn("sys", ctx.imports)

    def test_context_extractor_typescript(self) -> None:
        from eostudio.core.ai.inline_completion import ContextExtractor
        code = "import React from 'react';\nimport { useState } from 'react';\n\nfunction App() {\n"
        ctx = ContextExtractor.extract(code, len(code), "typescript", "App.tsx")
        self.assertIn("react", ctx.imports)


# ---------------------------------------------------------------------------
# AgenticCoder tests
# ---------------------------------------------------------------------------

class TestAgenticCoder(unittest.TestCase):

    def _make_agent(self, workspace: str, response: str = "") -> Any:
        from eostudio.core.ai.agentic_coder import AgenticCoder
        agent = AgenticCoder(workspace=workspace)
        agent._router = MockLLMRouter(response)
        return agent

    def test_dry_run_returns_result(self) -> None:
        plan_json = json.dumps({
            "language": "python",
            "estimated_files": 1,
            "subtasks": [
                {
                    "id": "step_1",
                    "description": "Create main module",
                    "action": "create_file",
                    "target": "main.py",
                    "content": "print('hello')",
                    "depends_on": [],
                }
            ],
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._make_agent(tmpdir, plan_json)
            result = agent.run("Create a hello world app", dry_run=True)
            self.assertIsNotNone(result)
            self.assertIsInstance(result.summary, str)

    def test_agent_status_initial(self) -> None:
        from eostudio.core.ai.agentic_coder import AgenticCoder, AgentStatus
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = AgenticCoder(workspace=tmpdir)
            self.assertEqual(agent.status, AgentStatus.IDLE)

    def test_subtask_dataclass(self) -> None:
        from eostudio.core.ai.agentic_coder import SubTask
        st = SubTask(
            id="step_1",
            description="Create file",
            action="create_file",
            target="app.py",
        )
        self.assertEqual(st.status, "pending")
        self.assertEqual(st.result, "")

    def test_strip_fences(self) -> None:
        from eostudio.core.ai.agentic_coder import AgenticCoder
        code = "```python\ndef hello():\n    pass\n```"
        stripped = AgenticCoder._strip_fences(code)
        self.assertNotIn("```", stripped)
        self.assertIn("def hello", stripped)

    def test_progress_callback(self) -> None:
        from eostudio.core.ai.agentic_coder import AgenticCoder, AgentStatus
        events: List[str] = []

        def on_progress(status, message, subtask):
            events.append(status.name)

        plan_json = json.dumps({
            "language": "python",
            "estimated_files": 0,
            "subtasks": [],
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = self._make_agent(tmpdir, plan_json)
            agent.run("Empty task", on_progress=on_progress, dry_run=True)
            self.assertIn("PLANNING", events)


# ---------------------------------------------------------------------------
# OTEngine / CollabSession tests
# ---------------------------------------------------------------------------

class TestOTEngine(unittest.TestCase):

    def test_insert_insert_no_overlap(self) -> None:
        from eostudio.core.collaboration.realtime_collab import OTEngine, Operation, OpType
        op_a = Operation(op_type=OpType.INSERT, position=0, content="hello ")
        op_b = Operation(op_type=OpType.INSERT, position=5, content="world")
        a2, b2 = OTEngine.transform(op_a, op_b)
        # b should shift right by len("hello ")
        self.assertEqual(b2.position, 5 + len("hello "))

    def test_apply_insert(self) -> None:
        from eostudio.core.collaboration.realtime_collab import OTEngine, Operation, OpType
        op = Operation(op_type=OpType.INSERT, position=5, content="WORLD")
        result = OTEngine.apply_to_text("hello ", op)
        self.assertEqual(result, "helloWORLD ")

    def test_apply_delete(self) -> None:
        from eostudio.core.collaboration.realtime_collab import OTEngine, Operation, OpType
        op = Operation(op_type=OpType.DELETE, position=0, length=5)
        result = OTEngine.apply_to_text("hello world", op)
        self.assertEqual(result, " world")

    def test_collab_session_join(self) -> None:
        from eostudio.core.collaboration.realtime_collab import CollabSession
        session = CollabSession("test-session", document="Hello World")
        presence = session.join("user1", "Alice", "#3B82F6")
        self.assertEqual(presence.name, "Alice")
        self.assertEqual(len(session.online_users), 1)

    def test_collab_session_apply_local(self) -> None:
        from eostudio.core.collaboration.realtime_collab import CollabSession, Operation, OpType
        session = CollabSession("test-session", document="Hello")
        session.join("user1", "Alice")
        ops = [Operation(op_type=OpType.INSERT, position=5, content=" World")]
        cs = session.apply_local("user1", ops)
        self.assertEqual(session.document, "Hello World")
        self.assertEqual(session.revision, 1)

    def test_collab_session_concurrent_inserts(self) -> None:
        from eostudio.core.collaboration.realtime_collab import CollabSession, Operation, OpType
        session = CollabSession("test-session", document="Hello")
        session.join("user1", "Alice")
        session.join("user2", "Bob")

        # Alice inserts at position 5
        ops_a = [Operation(op_type=OpType.INSERT, position=5, content=" Alice")]
        session.apply_local("user1", ops_a)

        # Bob inserts at position 5 (concurrent)
        ops_b = [Operation(op_type=OpType.INSERT, position=5, content=" Bob")]
        from eostudio.core.collaboration.realtime_collab import ChangeSet
        cs_b = ChangeSet(
            revision=0,  # Based on original revision
            author_id="user2",
            author_name="Bob",
            timestamp=time.time(),
            ops=ops_b,
        )
        session.apply_remote(cs_b)
        # Both insertions should be present
        self.assertIn("Alice", session.document)
        self.assertIn("Bob", session.document)

    def test_session_manager(self) -> None:
        from eostudio.core.collaboration.realtime_collab import CollabSessionManager
        mgr = CollabSessionManager()
        s1 = mgr.create_session("Hello")
        s2 = mgr.create_session("World")
        self.assertEqual(mgr.active_count, 2)
        mgr.close_session(s1.session_id)
        self.assertEqual(mgr.active_count, 1)


# ---------------------------------------------------------------------------
# WorkspaceIntelligence / SymbolIndex tests
# ---------------------------------------------------------------------------

class TestSymbolIndex(unittest.TestCase):

    def test_index_python_file(self) -> None:
        from eostudio.core.ai.workspace_intelligence import SymbolIndex
        idx = SymbolIndex()
        code = (
            "import os\nimport sys\n\n"
            "class MyClass:\n    pass\n\n"
            "def my_function(x, y):\n    return x + y\n"
        )
        file_idx = idx.index_file("/test/app.py", code, "python")
        self.assertEqual(file_idx.language, "python")
        self.assertIn("os", file_idx.imports)
        names = [s.name for s in file_idx.symbols]
        self.assertIn("MyClass", names)
        self.assertIn("my_function", names)

    def test_index_typescript_file(self) -> None:
        from eostudio.core.ai.workspace_intelligence import SymbolIndex
        idx = SymbolIndex()
        code = (
            "import React from 'react';\n\n"
            "export class UserService {\n  constructor() {}\n}\n\n"
            "export function getUser(id: string) {\n  return null;\n}\n"
        )
        file_idx = idx.index_file("/test/user.ts", code, "typescript")
        names = [s.name for s in file_idx.symbols]
        self.assertIn("UserService", names)
        self.assertIn("getUser", names)

    def test_search_by_name(self) -> None:
        from eostudio.core.ai.workspace_intelligence import SymbolIndex
        idx = SymbolIndex()
        code = "def authenticate_user(username, password):\n    pass\n"
        idx.index_file("/test/auth.py", code, "python")
        results = idx.search("authenticate")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].name, "authenticate_user")

    def test_workspace_health_score(self) -> None:
        from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file
            (Path(tmpdir) / "app.py").write_text("def hello():\n    pass\n")
            wi = WorkspaceIntelligence(tmpdir)
            wi.index()
            health = wi.analyze_health()
            self.assertIsInstance(health.score, int)
            self.assertGreaterEqual(health.score, 0)
            self.assertLessEqual(health.score, 100)

    def test_semantic_search(self) -> None:
        from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "auth.py").write_text(
                "def login(username, password):\n    pass\n"
                "def logout(user_id):\n    pass\n"
            )
            wi = WorkspaceIntelligence(tmpdir)
            wi.index()
            results = wi.semantic_search("login")
            self.assertTrue(len(results) > 0)

    def test_suggest_refactoring_rule_based(self) -> None:
        from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence
        with tempfile.TemporaryDirectory() as tmpdir:
            long_file = "def func():\n    pass\n" * 200  # > 300 lines
            (Path(tmpdir) / "big.py").write_text(long_file)
            wi = WorkspaceIntelligence(tmpdir)
            suggestions = wi.suggest_refactoring("big.py")
            self.assertTrue(len(suggestions) > 0)
            self.assertTrue(any("large" in s.lower() or "split" in s.lower() for s in suggestions))


# ---------------------------------------------------------------------------
# VoiceToCode tests
# ---------------------------------------------------------------------------

class TestVoiceToCode(unittest.TestCase):

    def test_parse_define_function(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceCommandParser, VoiceCommandType
        parser = VoiceCommandParser()
        cmd = parser.parse("define a function called calculate_total")
        self.assertEqual(cmd.command_type, VoiceCommandType.CODE_DICTATION)
        self.assertEqual(cmd.intent, "define_function")
        self.assertEqual(cmd.parameters.get("name"), "calculate_total")

    def test_parse_editor_undo(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceCommandParser, VoiceCommandType
        parser = VoiceCommandParser()
        cmd = parser.parse("undo")
        self.assertEqual(cmd.command_type, VoiceCommandType.EDITOR_ACTION)
        self.assertEqual(cmd.intent, "undo_redo")

    def test_parse_design_add_button(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceCommandParser, VoiceCommandType
        parser = VoiceCommandParser()
        cmd = parser.parse("add a button")
        self.assertEqual(cmd.command_type, VoiceCommandType.DESIGN_COMMAND)
        self.assertEqual(cmd.intent, "add_component")

    def test_parse_ai_query_fallback(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceCommandParser, VoiceCommandType
        parser = VoiceCommandParser()
        cmd = parser.parse("what is the best way to sort a list in Python")
        self.assertEqual(cmd.command_type, VoiceCommandType.AI_QUERY)

    def test_code_dictation_python(self) -> None:
        from eostudio.core.ai.voice_to_code import (
            CodeDictationConverter, VoiceCommand, VoiceCommandType
        )
        converter = CodeDictationConverter()
        cmd = VoiceCommand(
            raw_text="define a function called greet",
            command_type=VoiceCommandType.CODE_DICTATION,
            intent="define_function",
            parameters={"name": "greet"},
        )
        code = converter.convert(cmd, "python")
        self.assertIn("def greet", code)

    def test_code_dictation_typescript(self) -> None:
        from eostudio.core.ai.voice_to_code import (
            CodeDictationConverter, VoiceCommand, VoiceCommandType
        )
        converter = CodeDictationConverter()
        cmd = VoiceCommand(
            raw_text="create a class called UserManager",
            command_type=VoiceCommandType.CODE_DICTATION,
            intent="create_class",
            parameters={"name": "UserManager"},
        )
        code = converter.convert(cmd, "typescript")
        self.assertIn("UserManager", code)
        self.assertIn("class", code)

    def test_design_command_change_color(self) -> None:
        from eostudio.core.ai.voice_to_code import (
            DesignCommandExecutor, VoiceCommand, VoiceCommandType
        )
        executor = DesignCommandExecutor()
        cmd = VoiceCommand(
            raw_text="change color to blue",
            command_type=VoiceCommandType.DESIGN_COMMAND,
            intent="change_color",
            parameters={"target": "blue"},
        )
        action = executor.execute(cmd)
        self.assertEqual(action["action"], "set_property")
        self.assertEqual(action["value"], "#3B82F6")

    def test_voice_to_code_process_text(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceToCode
        vtc = VoiceToCode(language="python")
        result = vtc.process_text("define a function called hello_world")
        self.assertIn("def hello_world", result.generated_code)

    def test_supported_commands(self) -> None:
        from eostudio.core.ai.voice_to_code import VoiceToCode
        vtc = VoiceToCode()
        cmds = vtc.supported_commands()
        self.assertIn("Editor Actions", cmds)
        self.assertIn("Code Dictation", cmds)
        self.assertIn("Design Commands", cmds)


# ---------------------------------------------------------------------------
# LivePreviewEngine tests
# ---------------------------------------------------------------------------

class TestLivePreviewEngine(unittest.TestCase):

    def test_file_watcher_detects_changes(self) -> None:
        from eostudio.core.devtools.live_preview import FileWatcher
        changed_files: List[str] = []
        event = threading.Event()

        def on_change(files):
            changed_files.extend(files)
            event.set()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "app.py"
            test_file.write_text("x = 1\n")

            watcher = FileWatcher(tmpdir, on_change)
            watcher.start()
            time.sleep(0.2)

            # Modify the file
            test_file.write_text("x = 2\n")
            event.wait(timeout=2.0)
            watcher.stop()

            self.assertTrue(len(changed_files) > 0)

    def test_preview_session_creation(self) -> None:
        from eostudio.core.devtools.live_preview import (
            LivePreviewEngine, PreviewConfig, PreviewFramework
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = LivePreviewEngine()
            config = PreviewConfig(
                workspace=tmpdir,
                framework=PreviewFramework.HTML,
                port=18080,
            )
            session = engine.start(config)
            self.assertEqual(session.url, "http://localhost:18080")
            self.assertTrue(session.is_running)
            engine.stop(session.session_id)

    def test_device_presets(self) -> None:
        from eostudio.core.devtools.live_preview import DEVICE_PRESETS
        self.assertIn("desktop", DEVICE_PRESETS)
        self.assertIn("mobile_sm", DEVICE_PRESETS)
        self.assertIn("tablet", DEVICE_PRESETS)
        self.assertEqual(DEVICE_PRESETS["desktop"]["width"], 1440)


# ---------------------------------------------------------------------------
# PluginMarketplace tests
# ---------------------------------------------------------------------------

class TestPluginMarketplace(unittest.TestCase):

    def _make_marketplace(self) -> Any:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            return mp

    def test_catalog_not_empty(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace, BUILTIN_CATALOG
        self.assertGreater(len(BUILTIN_CATALOG), 10)

    def test_search_by_name(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            results = mp.search("git")
            self.assertTrue(len(results) > 0)
            self.assertTrue(any("git" in p.name.lower() or "git" in p.id for p in results))

    def test_search_by_category(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace, PluginCategory
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            results = mp.search(category=PluginCategory.THEME)
            self.assertTrue(len(results) > 0)
            self.assertTrue(all(p.category == PluginCategory.THEME for p in results))

    def test_get_featured(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            featured = mp.get_featured()
            self.assertTrue(len(featured) > 0)
            self.assertTrue(all(p.is_featured for p in featured))

    def test_install_builtin_plugin(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            result = mp.install("eostudio-copilot")
            self.assertTrue(result.success)
            self.assertEqual(result.plugin_id, "eostudio-copilot")

    def test_install_already_installed(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            mp.install("eostudio-copilot")
            result = mp.install("eostudio-copilot")
            self.assertTrue(result.success)
            self.assertIn("Already", result.message)

    def test_install_unknown_plugin(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            result = mp.install("nonexistent-plugin-xyz")
            self.assertFalse(result.success)

    def test_uninstall_plugin(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            mp.install("eostudio-copilot")
            success = mp.uninstall("eostudio-copilot")
            self.assertTrue(success)
            self.assertEqual(len(mp.list_installed()), 0)

    def test_list_installed(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            mp.install("eostudio-copilot")
            mp.install("eostudio-collab")
            installed = mp.list_installed()
            self.assertEqual(len(installed), 2)

    def test_verified_filter(self) -> None:
        from eostudio.plugins.marketplace import PluginMarketplace
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = PluginMarketplace(install_dir=tmpdir)
            results = mp.search(verified_only=True)
            self.assertTrue(all(p.is_verified for p in results))


if __name__ == "__main__":
    unittest.main()
