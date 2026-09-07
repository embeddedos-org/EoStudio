"""Enhanced CLI commands for EoStudio — new features beyond v3.0.1.

New commands:
- agent: Run the agentic coder on a task
- complete: Get AI code completion for a file
- collab: Start/join a collaboration session
- preview: Start live preview for a project
- workspace: Workspace intelligence (search, health, docs)
- voice: Process a voice command
- plugin: Marketplace plugin management
- multi-model: Query with model selection
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click


# ---------------------------------------------------------------------------
# agent command
# ---------------------------------------------------------------------------


@click.command("agent")
@click.argument("task")
@click.option("--workspace", "-w", default=".", help="Workspace directory.")
@click.option("--dry-run", is_flag=True, help="Plan only, don't execute.")
@click.option("--auto-commit", is_flag=True, help="Auto-commit changes to git.")
@click.option("--model", default=None, help="Override model (e.g. gpt-4.1).")
def agent_cmd(task: str, workspace: str, dry_run: bool, auto_commit: bool, model: Optional[str]) -> None:
    """Run the agentic coder on a natural language TASK.

    \b
    Examples:
      EoStudio agent "Add JWT authentication to the Flask API"
      EoStudio agent "Write unit tests for all public functions" --workspace ./src
      EoStudio agent "Refactor database module to use async SQLAlchemy" --auto-commit
    """
    from eostudio.core.ai.agentic_coder import AgenticCoder, AgentStatus
    from eostudio.core.ai.multi_model_router import MultiModelRouter, RouterConfig

    router_config = RouterConfig()
    if model:
        router_config.primary_model = model

    router = MultiModelRouter(router_config)
    agent = AgenticCoder(workspace=workspace, router=router, auto_commit=auto_commit)

    def on_progress(status, message, subtask):
        icon = {
            AgentStatus.PLANNING: "🧠",
            AgentStatus.EXECUTING: "⚙️",
            AgentStatus.TESTING: "🧪",
            AgentStatus.FIXING: "🔧",
            AgentStatus.COMMITTING: "📦",
            AgentStatus.DONE: "✅",
            AgentStatus.FAILED: "❌",
        }.get(status, "•")
        click.echo(f"  {icon} [{status.name}] {message}")

    click.echo(f"\n🤖 EoStudio Agent — Task: {task}")
    click.echo(f"   Workspace: {os.path.abspath(workspace)}")
    if dry_run:
        click.echo("   Mode: DRY RUN (planning only)\n")
    else:
        click.echo()

    result = agent.run(task, on_progress=on_progress, dry_run=dry_run)

    click.echo(f"\n{'✅' if result.success else '❌'} {result.summary}")
    if result.files_created:
        click.echo(f"   Created: {', '.join(result.files_created)}")
    if result.files_modified:
        click.echo(f"   Modified: {', '.join(result.files_modified)}")
    if result.tests_passed or result.tests_failed:
        click.echo(f"   Tests: {result.tests_passed} passed, {result.tests_failed} failed")
    if result.commit_hash:
        click.echo(f"   Commit: {result.commit_hash}")
    click.echo(f"   Duration: {result.duration_seconds}s")

    sys.exit(0 if result.success else 1)


# ---------------------------------------------------------------------------
# complete command
# ---------------------------------------------------------------------------


@click.command("complete")
@click.argument("file")
@click.option("--line", "-l", default=None, type=int, help="Line number (1-indexed).")
@click.option("--multiline", "-m", is_flag=True, help="Request multi-line completion.")
@click.option("--language", default=None, help="Override language detection.")
def complete_cmd(file: str, line: Optional[int], multiline: bool, language: Optional[str]) -> None:
    """Get AI inline code completion for FILE at the specified line.

    \b
    Examples:
      EoStudio complete app.py --line 42
      EoStudio complete src/utils.ts --multiline
    """
    from eostudio.core.ai.inline_completion import InlineCompletionEngine, ContextExtractor

    path = Path(file)
    if not path.exists():
        click.echo(f"Error: File not found: {file}", err=True)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    ext_lang = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".cpp": "cpp",
        ".c": "c",
    }
    lang = language or ext_lang.get(path.suffix, "text")

    # Determine cursor offset
    if line:
        lines = content.split("\n")
        cursor_offset = sum(len(l) + 1 for l in lines[: line - 1]) + len(lines[line - 1])
    else:
        cursor_offset = len(content)

    ctx = ContextExtractor.extract(content, cursor_offset, lang, file)
    engine = InlineCompletionEngine()

    click.echo(f"Generating completion for {file} ({lang})...")
    result = engine.complete(ctx, multiline=multiline)

    if result:
        click.echo(f"\n--- Completion (confidence: {result.confidence:.0%}, model: {result.model}) ---")
        click.echo(result.text)
        click.echo(f"--- Latency: {result.latency_ms:.0f}ms ---")
    else:
        click.echo("No completion available.")


# ---------------------------------------------------------------------------
# workspace command
# ---------------------------------------------------------------------------


@click.group("workspace")
def workspace_group() -> None:
    """Workspace intelligence commands."""
    pass


@workspace_group.command("index")
@click.option("--path", "-p", default=".", help="Workspace path.")
def workspace_index(path: str) -> None:
    """Index the workspace for semantic search and analysis."""
    from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence

    wi = WorkspaceIntelligence(path)
    click.echo(f"Indexing {os.path.abspath(path)}...")
    count = wi.index()
    click.echo(f"✅ Indexed {count} files")


@workspace_group.command("search")
@click.argument("query")
@click.option("--path", "-p", default=".", help="Workspace path.")
@click.option("--kind", default=None, help="Symbol kind: function|class|variable")
def workspace_search(query: str, path: str, kind: Optional[str]) -> None:
    """Search the workspace by symbol name or text."""
    from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence

    wi = WorkspaceIntelligence(path)
    wi.index()
    results = wi.semantic_search(query)
    if not results:
        click.echo("No results found.")
        return
    click.echo(f"\nFound {len(results)} result(s) for '{query}':\n")
    for r in results:
        loc = f"{r.get('file', '')}:{r.get('line', '')}"
        click.echo(f"  [{r.get('kind', r.get('type', ''))}] {r.get('name', r.get('snippet', '')[:60])}")
        click.echo(f"    {loc}")
        if r.get("docstring"):
            click.echo(f"    {r['docstring'][:80]}")
        click.echo()


@workspace_group.command("health")
@click.option("--path", "-p", default=".", help="Workspace path.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def workspace_health(path: str, as_json: bool) -> None:
    """Analyze workspace architecture health."""
    from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence

    wi = WorkspaceIntelligence(path)
    wi.index()
    health = wi.analyze_health()

    if as_json:
        click.echo(
            json.dumps(
                {
                    "score": health.score,
                    "circular_deps": len(health.circular_deps),
                    "dead_code": len(health.dead_code),
                    "large_files": health.large_files,
                    "missing_tests": health.missing_tests,
                    "suggestions": health.suggestions,
                },
                indent=2,
            )
        )
        return

    score_icon = "🟢" if health.score >= 80 else "🟡" if health.score >= 60 else "🔴"
    click.echo(f"\n{score_icon} Architecture Health Score: {health.score}/100\n")

    if health.suggestions:
        click.echo("Suggestions:")
        for s in health.suggestions:
            click.echo(f"  • {s}")

    if health.circular_deps:
        click.echo(f"\nCircular Dependencies ({len(health.circular_deps)}):")
        for a, b in health.circular_deps[:5]:
            click.echo(f"  {Path(a).name} ↔ {Path(b).name}")

    if health.large_files:
        click.echo(f"\nLarge Files (>500 LOC):")
        for f in health.large_files[:5]:
            click.echo(f"  {f}")


@workspace_group.command("docs")
@click.argument("file")
@click.option("--output", "-o", default=None, help="Output file path.")
def workspace_docs(file: str, output: Optional[str]) -> None:
    """Generate documentation for a source file."""
    from eostudio.core.ai.workspace_intelligence import WorkspaceIntelligence
    from eostudio.core.ai.multi_model_router import MultiModelRouter

    router = MultiModelRouter()
    wi = WorkspaceIntelligence(".", router=router)
    click.echo(f"Generating docs for {file}...")
    docs = wi.generate_docs(file)
    if output:
        Path(output).write_text(docs, encoding="utf-8")
        click.echo(f"✅ Docs written to {output}")
    else:
        click.echo(docs)


# ---------------------------------------------------------------------------
# plugin marketplace command
# ---------------------------------------------------------------------------


@click.group("plugin")
def plugin_group() -> None:
    """Plugin marketplace commands."""
    pass


@plugin_group.command("search")
@click.argument("query", default="")
@click.option("--category", "-c", default=None, help="Category filter.")
@click.option("--verified", is_flag=True, help="Verified plugins only.")
def plugin_search(query: str, category: Optional[str], verified: bool) -> None:
    """Search the plugin marketplace."""
    from eostudio.plugins.marketplace import PluginMarketplace, PluginCategory

    mp = PluginMarketplace()
    cat = PluginCategory(category) if category else None
    results = mp.search(query=query, category=cat, verified_only=verified)
    if not results:
        click.echo("No plugins found.")
        return
    click.echo(f"\nFound {len(results)} plugin(s):\n")
    for p in results:
        verified_badge = " ✓" if p.is_verified else ""
        featured_badge = " ⭐" if p.is_featured else ""
        click.echo(f"  {p.id}{verified_badge}{featured_badge}")
        click.echo(f"    {p.name} v{p.version} by {p.author}")
        click.echo(f"    {p.description}")
        click.echo(f"    ⭐ {p.stars:,}  ↓ {p.downloads:,}  [{p.category.value}]")
        click.echo()


@plugin_group.command("install")
@click.argument("plugin_id")
def plugin_install(plugin_id: str) -> None:
    """Install a plugin from the marketplace."""
    from eostudio.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    click.echo(f"Installing {plugin_id}...")
    result = mp.install(plugin_id)
    if result.success:
        click.echo(f"✅ {result.message}")
    else:
        click.echo(f"❌ {result.message}", err=True)
        sys.exit(1)


@plugin_group.command("list")
def plugin_list() -> None:
    """List installed plugins."""
    from eostudio.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    installed = mp.list_installed()
    if not installed:
        click.echo("No plugins installed.")
        return
    click.echo(f"\nInstalled plugins ({len(installed)}):\n")
    for p in installed:
        click.echo(f"  {p.id} v{p.version} — {p.name}")


@plugin_group.command("update")
@click.argument("plugin_id", default="")
def plugin_update(plugin_id: str) -> None:
    """Update a plugin (or all plugins if no ID given)."""
    from eostudio.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    if plugin_id:
        result = mp.update(plugin_id)
        click.echo(f"{'✅' if result.success else '❌'} {result.message}")
    else:
        updates = mp.check_updates()
        if not updates:
            click.echo("All plugins are up to date.")
            return
        for pid in updates:
            result = mp.update(pid)
            click.echo(f"  {'✅' if result.success else '❌'} {pid}: {result.message}")


@plugin_group.command("uninstall")
@click.argument("plugin_id")
def plugin_uninstall(plugin_id: str) -> None:
    """Uninstall a plugin."""
    from eostudio.plugins.marketplace import PluginMarketplace

    mp = PluginMarketplace()
    if mp.uninstall(plugin_id):
        click.echo(f"✅ Uninstalled {plugin_id}")
    else:
        click.echo(f"❌ Plugin {plugin_id} is not installed", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# voice command
# ---------------------------------------------------------------------------


@click.command("voice")
@click.argument("text", required=False)
@click.option("--audio", "-a", default=None, help="Audio file to transcribe and process.")
@click.option("--language", "-l", default="python", help="Target programming language.")
@click.option("--ai", is_flag=True, help="Use AI for richer code generation.")
def voice_cmd(text: Optional[str], audio: Optional[str], language: str, ai: bool) -> None:
    """Process a voice command or dictation.

    \b
    Examples:
      EoStudio voice "define a function called calculate total"
      EoStudio voice "add a button labeled Submit" --language typescript
      EoStudio voice --audio recording.wav --ai
    """
    from eostudio.core.ai.voice_to_code import VoiceToCode

    vtc = VoiceToCode(language=language)

    if audio:
        click.echo(f"Transcribing {audio}...")
        result = vtc.process_audio_file(audio, use_ai=ai)
    elif text:
        result = vtc.process_text(text, use_ai=ai)
    else:
        click.echo("Provide TEXT or --audio FILE", err=True)
        sys.exit(1)

    click.echo(f"\nCommand type: {result.command_type.name}")
    click.echo(f"Intent: {result.intent}")
    click.echo(f"Confidence: {result.confidence:.0%}")

    if result.generated_code:
        click.echo(f"\nGenerated code:\n{result.generated_code}")

    if result.parameters.get("action"):
        click.echo(f"\nEditor action: {json.dumps(result.parameters['action'], indent=2)}")

    if result.parameters.get("response"):
        click.echo(f"\nAI response: {result.parameters['response']}")


# ---------------------------------------------------------------------------
# multi-model query command
# ---------------------------------------------------------------------------


@click.command("query")
@click.argument("prompt")
@click.option("--model", "-m", default=None, help="Model to use (gpt-4.1, gpt-4.1-mini, gemini-2.5-flash, etc.)")
@click.option(
    "--task",
    "-t",
    default="chat",
    type=click.Choice(["chat", "code", "review", "design", "agent", "docs"]),
    help="Task type for model selection.",
)
@click.option("--stream", "-s", is_flag=True, help="Stream the response.")
@click.option("--system", default=None, help="System prompt.")
def query_cmd(prompt: str, model: Optional[str], task: str, stream: bool, system: Optional[str]) -> None:
    """Query an AI model with automatic model selection.

    \b
    Examples:
      EoStudio query "Write a Python function to validate email addresses"
      EoStudio query "Review this code for security issues" --task review --model gpt-4.1
      EoStudio query "Design a login screen" --task design --stream
    """
    from eostudio.core.ai.multi_model_router import MultiModelRouter, TaskType

    task_map = {
        "chat": TaskType.CHAT,
        "code": TaskType.CODE_GENERATION,
        "review": TaskType.CODE_REVIEW,
        "design": TaskType.DESIGN_BRIEF,
        "agent": TaskType.AGENT_LOOP,
        "docs": TaskType.DOCUMENTATION,
    }

    router = MultiModelRouter()
    selected_model = model or router.select_model(task_map[task])
    click.echo(f"Using model: {selected_model}\n", err=True)

    if stream:
        for chunk in router.stream(prompt, task=task_map[task], system=system, model_override=model):
            click.echo(chunk, nl=False)
        click.echo()
    else:
        response = router.complete(prompt, task=task_map[task], system=system, model_override=model)
        click.echo(response)
