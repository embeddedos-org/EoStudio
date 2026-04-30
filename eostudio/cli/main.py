"""EoStudio CLI — Command-line interface for EoStudio."""

import click

from eostudio import __version__


@click.group()
@click.version_option(version=__version__, prog_name="EoStudio")
def cli():
    """EoStudio — Universal Development Platform with AI-Powered Code Editing."""


# ---------------------------------------------------------------------------
# Existing v1.0 Commands
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--editor",
    type=click.Choice([
        "3d", "cad", "paint", "game", "ui", "product", "interior",
        "uml", "simulation", "database", "ide", "promo", "all",
    ]),
    default="all",
    help="Editor to launch.",
)
@click.option("--theme", type=click.Choice(["dark", "light"]), default="dark")
def launch(editor: str, theme: str):
    """Launch the EoStudio GUI application."""
    from eostudio.gui.app import EoStudioApp

    app = EoStudioApp(editor=editor, theme=theme)
    app.run()


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["gltf", "obj", "stl", "fbx", "step", "svg", "png"]),
    default="gltf",
    help="Export format.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path.")
def export(path: str, fmt: str, output: str):
    """Export a project or scene to a target format."""
    from eostudio.core.exporter import Exporter

    exporter = Exporter()
    result = exporter.export(path, fmt=fmt, output=output)
    click.echo(f"Exported to {result}")


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("--lang", type=click.Choice(["python", "cpp", "rust", "js", "ts"]), default="python", help="Target language.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output directory.")
def codegen(spec: str, lang: str, output: str):
    """Generate code from a specification file."""
    from eostudio.core.codegen import CodeGenerator

    gen = CodeGenerator(language=lang)
    result = gen.generate(spec, output=output)
    click.echo(f"Generated {result.file_count} files in {result.output_dir}")


@cli.command()
@click.argument("topic", required=False)
@click.option("--interactive", "-i", is_flag=True, help="Interactive teaching mode.")
def teach(topic: str, interactive: bool):
    """Open the AI teaching assistant."""
    from eostudio.core.ai.tutor import Tutor

    tutor = Tutor()
    if interactive:
        tutor.interactive_session(topic)
    else:
        tutor.explain(topic)


@cli.command()
@click.argument("question")
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "anthropic", "local"]),
    default="ollama",
    help="LLM provider backend.",
)
@click.option("--model", default=None, help="Model name override.")
def ask(question: str, provider: str, model: str):
    """Ask the AI assistant a question."""
    from eostudio.core.ai.llm_client import LLMClient

    client = LLMClient.create(provider=provider, model=model)
    response = client.ask(question)
    click.echo(response)


@cli.command()
@click.argument("diagram", type=click.Path(exists=True))
@click.option("--lang", type=click.Choice(["python", "cpp", "java", "ts"]), default="python", help="Target language.")
@click.option("--output", "-o", type=click.Path(), default=None)
def uml_codegen(diagram: str, lang: str, output: str):
    """Generate code from a UML diagram."""
    from eostudio.core.uml.uml_codegen import UMLCodeGenerator

    gen = UMLCodeGenerator(language=lang)
    result = gen.generate(diagram, output=output)
    click.echo(f"Generated {result.file_count} files from UML diagram")


@cli.command()
@click.argument("model", type=click.Path(exists=True))
@click.option("--duration", type=float, default=10.0, help="Simulation duration in seconds.")
@click.option("--step", type=float, default=0.01, help="Time step.")
@click.option("--output", "-o", type=click.Path(), default=None)
def simulate(model: str, duration: float, step: float, output: str):
    """Run a simulation from a model file."""
    from eostudio.core.simulation.engine import SimulationEngine

    engine = SimulationEngine()
    result = engine.run(model, duration=duration, step=step)
    if output:
        result.save(output)
    click.echo(f"Simulation complete — {result.steps} steps, {result.duration:.2f}s")


@cli.command()
@click.argument("schema", type=click.Path(exists=True))
@click.option("--dialect", type=click.Choice(["sqlite", "postgresql", "mysql"]), default="sqlite", help="SQL dialect.")
@click.option("--output", "-o", type=click.Path(), default=None)
def dbgen(schema: str, dialect: str, output: str):
    """Generate database schema and migrations from a spec."""
    from eostudio.core.database.dbgen import DatabaseGenerator

    gen = DatabaseGenerator(dialect=dialect)
    result = gen.generate(schema, output=output)
    click.echo(f"Generated {result.table_count} tables, {result.migration_count} migrations")


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--port", type=int, default=8888, help="IDE server port.")
@click.option("--theme", type=click.Choice(["dark", "light"]), default="dark")
def ide(path: str, port: int, theme: str):
    """Launch the EoStudio IDE."""
    from eostudio.core.ide.ide_app import IDEApp

    app = IDEApp(workspace=path, port=port, theme=theme)
    click.echo(f"Starting EoStudio IDE on port {port}...")
    app.run()


@cli.command()
@click.argument("name")
@click.option(
    "--template",
    type=click.Choice([
        "python", "cpp", "rust", "js", "ts", "react", "vue", "svelte",
        "fastapi", "flask", "django", "express", "game", "cad", "empty",
    ]),
    default="empty",
    help="Project template.",
)
@click.option("--path", type=click.Path(), default=".", help="Parent directory.")
def new(name: str, template: str, path: str):
    """Create a new project from a template."""
    from eostudio.core.project import ProjectCreator

    creator = ProjectCreator()
    project_path = creator.create(name=name, template=template, parent=path)
    click.echo(f"Created project '{name}' at {project_path}")


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--framework", type=click.Choice(["react", "vue", "svelte"]), default="react")
def react_motion(spec: str, output: str, framework: str):
    """Generate animated React/Vue/Svelte components from a motion spec."""
    from eostudio.core.ui.motion_gen import MotionGenerator

    gen = MotionGenerator(framework=framework)
    result = gen.generate(spec, output=output)
    click.echo(f"Generated {result.component_count} animated components")


@cli.command()
@click.argument("description")
@click.option("--framework", type=click.Choice(["react", "vue", "svelte", "html"]), default="react")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--provider", type=click.Choice(["ollama", "openai", "anthropic", "local"]), default="ollama")
def generate_ui(description: str, framework: str, output: str, provider: str):
    """Generate UI components from a natural-language description."""
    from eostudio.core.ai.llm_client import LLMClient
    from eostudio.core.ui.ui_gen import UIGenerator

    client = LLMClient.create(provider=provider)
    gen = UIGenerator(llm=client, framework=framework)
    result = gen.generate(description, output=output)
    click.echo(f"Generated {result.file_count} UI files in {result.output_dir}")


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--format", "fmt", type=click.Choice(["css", "scss", "tailwind", "tokens"]), default="tokens")
def design_system(spec: str, output: str, fmt: str):
    """Generate a design-system package from a spec file."""
    from eostudio.core.ui.design_system_gen import DesignSystemGenerator

    gen = DesignSystemGenerator(fmt=fmt)
    result = gen.generate(spec, output=output)
    click.echo(f"Design system generated — {result.token_count} tokens, {result.component_count} components")


@cli.command()
@click.argument("image", type=click.Path(exists=True))
@click.option("--framework", type=click.Choice(["react", "vue", "svelte", "html"]), default="react")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--provider", type=click.Choice(["ollama", "openai", "anthropic", "local"]), default="ollama")
def screenshot_to_ui(image: str, framework: str, output: str, provider: str):
    """Convert a screenshot or mockup image to UI code."""
    from eostudio.core.ai.llm_client import LLMClient
    from eostudio.core.ui.screenshot_converter import ScreenshotConverter

    client = LLMClient.create(provider=provider)
    converter = ScreenshotConverter(llm=client, framework=framework)
    result = converter.convert(image, output=output)
    click.echo(f"Converted screenshot to {result.file_count} files")


@cli.command()
@click.argument("product")
@click.option("--style", type=click.Choice(["modern", "minimal", "bold", "playful"]), default="modern")
@click.option("--size", type=click.Choice(["instagram", "twitter", "linkedin", "banner", "custom"]), default="instagram")
@click.option("--output", "-o", type=click.Path(), default=None)
def promo(product: str, style: str, size: str, output: str):
    """Generate promotional graphics for a product."""
    from eostudio.core.promo.promo_gen import PromoGenerator

    gen = PromoGenerator(style=style, size=size)
    result = gen.generate(product, output=output)
    click.echo(f"Generated {result.image_count} promo images in {result.output_dir}")


@cli.command()
@click.argument("description")
@click.option("--framework", type=click.Choice(["react", "vue", "svelte", "html"]), default="react")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--fidelity", type=click.Choice(["low", "medium", "high"]), default="medium")
def prototype(description: str, framework: str, output: str, fidelity: str):
    """Generate a rapid UI prototype from a description."""
    from eostudio.core.ui.prototype_gen import PrototypeGenerator

    gen = PrototypeGenerator(framework=framework, fidelity=fidelity)
    result = gen.generate(description, output=output)
    click.echo(f"Prototype generated — {result.page_count} pages, {result.component_count} components")


@cli.command()
@click.argument("image", type=click.Path(exists=True))
@click.option("--count", type=int, default=5, help="Number of palette colours to extract.")
@click.option("--format", "fmt", type=click.Choice(["hex", "rgb", "hsl", "tokens"]), default="hex")
def palette(image: str, count: int, fmt: str):
    """Extract a colour palette from an image."""
    from eostudio.core.ui.palette_extractor import PaletteExtractor

    extractor = PaletteExtractor()
    colours = extractor.extract(image, count=count, fmt=fmt)
    for colour in colours:
        click.echo(colour)


@cli.command()
@click.argument("description")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--format", "fmt", type=click.Choice(["md", "pdf", "html"]), default="md")
def spec(description: str, output: str, fmt: str):
    """Generate a technical specification document from a description."""
    from eostudio.core.docs.spec_gen import SpecGenerator

    gen = SpecGenerator(fmt=fmt)
    result = gen.generate(description, output=output)
    click.echo(f"Specification generated at {result.path}")


@cli.command()
@click.argument("task")
@click.option("--provider", type=click.Choice(["ollama", "openai", "anthropic", "local"]), default="ollama")
@click.option("--model", default=None, help="Model name override.")
@click.option("--max-steps", type=int, default=10, help="Maximum agent steps.")
def agent(task: str, provider: str, model: str, max_steps: int):
    """Run an autonomous AI agent to complete a task."""
    from eostudio.core.ai.agent import Agent
    from eostudio.core.ai.llm_client import LLMClient

    client = LLMClient.create(provider=provider, model=model)
    ai_agent = Agent(llm=client, max_steps=max_steps)
    result = ai_agent.run(task)
    click.echo(result.summary)


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("--framework", type=click.Choice(["react", "vue", "svelte"]), default="react")
@click.option("--output", "-o", type=click.Path(), default=None)
def ui_kit(spec: str, framework: str, output: str):
    """Generate a reusable UI component kit from a design spec."""
    from eostudio.core.ui.ui_kit_gen import UIKitGenerator

    gen = UIKitGenerator(framework=framework)
    result = gen.generate(spec, output=output)
    click.echo(f"UI kit generated — {result.component_count} components in {result.output_dir}")


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--target", type=click.Choice(["vercel", "netlify", "docker", "aws", "gcp", "fly"]), default="docker", help="Deployment target.")
@click.option("--env", type=click.Choice(["dev", "staging", "production"]), default="production")
def deploy(path: str, target: str, env: str):
    """Deploy the project to a hosting target."""
    from eostudio.core.deploy.deployer import Deployer

    deployer = Deployer(target=target, env=env)
    result = deployer.deploy(path)
    click.echo(f"Deployed to {result.url}")


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--target", type=click.Choice(["debug", "release"]), default="debug")
@click.option("--clean", is_flag=True, help="Clean build artefacts before building.")
def build(path: str, target: str, clean: bool):
    """Build the project."""
    from eostudio.core.devtools.build_system import BuildSystemManager

    manager = BuildSystemManager()
    build_system = manager.detect(path)
    if clean:
        build_system.clean()
    result = build_system.build(target=target)
    click.echo(f"Build {result.status} — {result.artefact_count} artefacts")


# ---------------------------------------------------------------------------
# New v2.0 Commands
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--name", default=None, help="Project name (defaults to directory name).")
def init(path: str, name: str):
    """Initialize a workspace with automatic project detection."""
    import os

    from eostudio.core.ide.project_manager import ProjectManager

    pm = ProjectManager()
    info = pm.detect_project_type(path)
    click.echo(f"Detected language : {info.language}")
    click.echo(f"Detected framework: {info.framework}")
    click.echo(f"Detected build    : {info.build_system}")

    project_name = name or os.path.basename(os.path.abspath(path))
    project = pm.create(path, name=project_name)
    click.echo(f"Workspace '{project.name}' initialised at {project.path}")


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--coverage", is_flag=True, help="Collect code-coverage metrics.")
@click.option("--watch", is_flag=True, help="Re-run tests on file changes.")
@click.option("--file", "test_file", default=None, help="Run a single test file.")
def test(path: str, coverage: bool, watch: bool, test_file: str):
    """Run tests with auto-detected framework."""
    from eostudio.core.devtools.testing import TestRunner

    runner = TestRunner()
    framework = runner.detect_framework(path)
    click.echo(f"Test framework: {framework}")

    if watch:
        click.echo("Watching for changes... (Ctrl+C to stop)")
        runner.watch(path)
        return

    if test_file:
        result = runner.run_file(test_file)
    elif coverage:
        result = runner.run_with_coverage(path)
    else:
        result = runner.run_all(path)

    click.echo(f"Passed : {result.passed}")
    click.echo(f"Failed : {result.failed}")
    click.echo(f"Errors : {result.errors}")
    click.echo(f"Skipped: {result.skipped}")

    if coverage and hasattr(result, "coverage"):
        click.echo(f"Coverage: {result.coverage:.1f}%")

    raise SystemExit(0 if result.failed == 0 and result.errors == 0 else 1)


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--fix", is_flag=True, help="Auto-fix lint issues where possible.")
def lint(path: str, fix: bool):
    """Run linters on the project."""
    import subprocess

    from eostudio.core.devtools.build_system import BuildSystemManager

    manager = BuildSystemManager()
    info = manager.detect(path)
    click.echo(f"Build system: {info.name}")

    lint_cmd = info.lint_command(fix=fix)
    click.echo(f"Running: {' '.join(lint_cmd)}")
    result = subprocess.run(lint_cmd, cwd=path)
    raise SystemExit(result.returncode)


@cli.command()
@click.option(
    "--method",
    type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"]),
    default="GET",
    help="HTTP method.",
)
@click.argument("url")
@click.option("--data", "-d", default=None, help="Request body (JSON string).")
@click.option("--header", "-H", multiple=True, help="Request header (key:value). Repeatable.")
@click.option("--auth", default=None, help="Bearer token for Authorization header.")
def api(method: str, url: str, data: str, header: tuple, auth: str):
    """Send an HTTP request (REST API client)."""
    from eostudio.core.devtools.api_client import (
        APIClient,
        APIRequest,
        AuthConfig,
        AuthType,
        HTTPMethod,
    )

    headers = {}
    for h in header:
        key, _, value = h.partition(":")
        headers[key.strip()] = value.strip()

    auth_config = None
    if auth:
        auth_config = AuthConfig(type=AuthType.BEARER, token=auth)

    request = APIRequest(
        method=HTTPMethod[method],
        url=url,
        body=data,
        headers=headers,
        auth=auth_config,
    )

    client = APIClient()
    response = client.send(request)

    click.echo(f"Status : {response.status_code}")
    click.echo(f"Time   : {response.elapsed_ms:.0f} ms")
    click.echo(f"Body   :\n{response.text}")


@cli.command()
@click.option(
    "--type",
    "db_type",
    type=click.Choice(["sqlite", "postgresql", "mysql"]),
    default="sqlite",
    help="Database type.",
)
@click.option("--database", default=None, help="Database name or path.")
@click.option("--host", default="localhost", help="Database host.")
@click.option("--port", type=int, default=None, help="Database port.")
@click.option("--user", default=None, help="Database user.")
@click.option("--password", default=None, help="Database password.")
@click.argument("query")
def db(db_type: str, database: str, host: str, port: int, user: str, password: str, query: str):
    """Execute a database query."""
    from eostudio.core.devtools.database_client import (
        DatabaseClient,
        DatabaseConfig,
        DatabaseType,
    )

    config = DatabaseConfig(
        db_type=DatabaseType[db_type.upper()],
        database=database,
        host=host,
        port=port,
        user=user,
        password=password,
    )

    client = DatabaseClient(config)
    result = client.execute(query)

    if result.columns:
        # Print header
        header = " | ".join(f"{col:>15}" for col in result.columns)
        click.echo(header)
        click.echo("-" * len(header))
        for row in result.rows:
            click.echo(" | ".join(f"{str(v):>15}" for v in row))
        click.echo(f"\n({result.row_count} rows)")
    else:
        click.echo(f"Query OK — {result.affected_rows} rows affected")


@cli.command()
@click.option(
    "--action",
    type=click.Choice(["ps", "images", "build", "up", "down", "logs"]),
    default="ps",
    help="Docker action to perform.",
)
@click.option("--path", type=click.Path(), default=".", help="Path containing Dockerfile / docker-compose.")
@click.option("--tag", default=None, help="Image tag (for build).")
@click.option("--container", default=None, help="Container name (for logs).")
def docker(action: str, path: str, tag: str, container: str):
    """Manage Docker containers and images."""
    from eostudio.core.devtools.containers import ContainerManager

    mgr = ContainerManager()

    if action == "ps":
        containers = mgr.list_containers()
        for c in containers:
            click.echo(f"{c.id[:12]}  {c.name:30s}  {c.status}")
    elif action == "images":
        images = mgr.list_images()
        for img in images:
            click.echo(f"{img.id[:12]}  {img.tag:30s}  {img.size}")
    elif action == "build":
        result = mgr.build(path, tag=tag)
        click.echo(f"Built image: {result.tag}")
    elif action == "up":
        mgr.compose_up(path)
        click.echo("Services started.")
    elif action == "down":
        mgr.compose_down(path)
        click.echo("Services stopped.")
    elif action == "logs":
        logs = mgr.logs(container)
        click.echo(logs)


@cli.command()
@click.option("--host", required=True, help="Remote host.")
@click.option("--user", default=None, help="SSH user.")
@click.option("--port", type=int, default=22, help="SSH port.")
@click.option("--key", type=click.Path(exists=True), default=None, help="SSH private key path.")
@click.argument("command")
def remote(host: str, user: str, port: int, key: str, command: str):
    """Execute a command on a remote host via SSH."""
    from eostudio.core.devtools.remote import (
        RemoteConfig,
        RemoteConnection,
        RemoteType,
    )

    config = RemoteConfig(
        remote_type=RemoteType.SSH,
        host=host,
        user=user,
        port=port,
        key_path=key,
    )

    conn = RemoteConnection(config)
    result = conn.execute(command)

    if result.stdout:
        click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)
    raise SystemExit(result.exit_code)


@cli.command()
@click.argument("path", type=click.Path(), default=".")
@click.option(
    "--scan",
    type=click.Choice(["all", "deps", "code", "secrets"]),
    default="all",
    help="Type of security scan.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output report path.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json", "sarif"]),
    default="text",
    help="Report format.",
)
def security(path: str, scan: str, output: str, fmt: str):
    """Run security scans on the project."""
    from eostudio.core.devtools.security import SecurityScanner

    scanner = SecurityScanner()
    result = scanner.scan(path, scan_type=scan, output=output, fmt=fmt)

    click.echo(f"Scan complete — {result.issue_count} issues found")
    for issue in result.issues:
        icon = {"critical": "C", "high": "H", "medium": "M", "low": "L"}.get(
            issue.severity, "?"
        )
        click.echo(f"  [{icon}] [{issue.severity.upper()}] {issue.title}")
        click.echo(f"    {issue.location}")

    if output:
        click.echo(f"Report saved to {output}")

    raise SystemExit(1 if result.issue_count > 0 else 0)


@cli.command()
@click.argument("script", type=click.Path(exists=True))
@click.option(
    "--type",
    "profile_type",
    type=click.Choice(["cpu", "memory"]),
    default="cpu",
    help="Profiling mode.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file for the profile report.")
def profile(script: str, profile_type: str, output: str):
    """Profile a Python script for CPU or memory usage."""
    from eostudio.core.devtools.profiler import Profiler

    profiler = Profiler(mode=profile_type)
    result = profiler.run(script)

    click.echo(f"Profile type : {profile_type}")
    click.echo(f"Total time   : {result.total_time:.3f}s")
    click.echo(f"Peak memory  : {result.peak_memory_mb:.1f} MB")
    click.echo("\nTop functions:")
    for fn in result.top_functions[:10]:
        click.echo(f"  {fn.cumtime:8.3f}s  {fn.name}")

    if output:
        result.save(output)
        click.echo(f"\nFull report saved to {output}")


@cli.command()
@click.argument("template", required=False)
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory.")
@click.option("--name", default=None, help="Project / component name.")
@click.option("--list", "list_templates", is_flag=True, help="List all available templates.")
def scaffold(template: str, output: str, name: str, list_templates: bool):
    """Create a project or component from 40+ built-in templates."""
    from eostudio.core.scaffold import ScaffoldConfig, Scaffolder, TemplateRegistry

    registry = TemplateRegistry()

    if list_templates:
        templates = registry.list_all()
        click.echo(f"Available templates ({len(templates)}):\n")
        for t in templates:
            click.echo(f"  {t.name:25s}  {t.description}")
        return

    if not template:
        click.echo("Error: provide a TEMPLATE name or use --list.", err=True)
        raise SystemExit(1)

    config = ScaffoldConfig(template=template, output=output, name=name)
    scaffolder = Scaffolder(registry=registry)
    result = scaffolder.create(config)
    click.echo(f"Scaffolded '{result.name}' ({result.file_count} files) at {result.path}")


@cli.command()
@click.option(
    "--action",
    type=click.Choice(["start", "join", "list"]),
    default="list",
    help="Collaboration action.",
)
@click.option("--session", default=None, help="Session ID to join.")
@click.option("--port", type=int, default=9000, help="Server port (for start).")
@click.option("--user", default=None, help="Display name.")
def collab(action: str, session: str, port: int, user: str):
    """Real-time collaboration — start, join, or list sessions."""
    from eostudio.core.collaboration import CollabServer

    server = CollabServer()

    if action == "list":
        sessions = server.list_sessions()
        if not sessions:
            click.echo("No active sessions.")
            return
        for s in sessions:
            click.echo(f"  {s.id}  {s.owner:20s}  {s.participant_count} participants")

    elif action == "start":
        session_info = server.start(port=port, user=user)
        click.echo(f"Session started: {session_info.id}")
        click.echo(f"Share this ID with collaborators: {session_info.id}")
        click.echo("Waiting for connections... (Ctrl+C to stop)")
        server.serve_forever()

    elif action == "join":
        if not session:
            click.echo("Error: --session is required for join.", err=True)
            raise SystemExit(1)
        server.join(session, user=user)
        click.echo(f"Joined session {session}")


@cli.command()
@click.option(
    "--action",
    type=click.Choice(["chat", "review", "test-gen", "doc-gen", "explain", "fix"]),
    default="chat",
    help="AI action to perform.",
)
@click.option("--file", "file_path", type=click.Path(exists=True), default=None, help="Source file for context.")
@click.option("--provider", type=click.Choice(["ollama", "openai", "anthropic", "local"]), default="ollama", help="LLM provider.")
@click.option("--model", default=None, help="Model name override.")
@click.argument("prompt", required=False)
def ai(action: str, file_path: str, provider: str, model: str, prompt: str):
    """AI assistant — chat, code review, test & doc generation, explain, fix."""
    from eostudio.core.ai.llm_client import LLMClient

    client = LLMClient.create(provider=provider, model=model)

    if action == "chat":
        if not prompt:
            click.echo("Error: PROMPT is required for chat.", err=True)
            raise SystemExit(1)
        response = client.ask(prompt)
        click.echo(response)

    elif action == "review":
        from eostudio.core.ai.code_reviewer import CodeReviewer

        if not file_path:
            click.echo("Error: --file is required for review.", err=True)
            raise SystemExit(1)
        reviewer = CodeReviewer(llm=client)
        result = reviewer.review(file_path)
        click.echo(result.summary)
        for issue in result.issues:
            click.echo(f"  [{issue.severity}] L{issue.line}: {issue.message}")

    elif action == "test-gen":
        from eostudio.core.ai.test_generator import TestGenerator

        if not file_path:
            click.echo("Error: --file is required for test-gen.", err=True)
            raise SystemExit(1)
        gen = TestGenerator(llm=client)
        result = gen.generate(file_path)
        click.echo(f"Generated {result.test_count} tests in {result.output_path}")

    elif action == "doc-gen":
        from eostudio.core.ai.doc_generator import DocGenerator

        if not file_path:
            click.echo("Error: --file is required for doc-gen.", err=True)
            raise SystemExit(1)
        gen = DocGenerator(llm=client)
        result = gen.generate(file_path)
        click.echo(result.documentation)

    elif action == "explain":
        from eostudio.core.ai.code_assistant import CodeAssistant

        if not file_path:
            click.echo("Error: --file is required for explain.", err=True)
            raise SystemExit(1)
        assistant = CodeAssistant(llm=client)
        explanation = assistant.explain(file_path)
        click.echo(explanation)

    elif action == "fix":
        from eostudio.core.ai.code_assistant import CodeAssistant

        if not file_path:
            click.echo("Error: --file is required for fix.", err=True)
            raise SystemExit(1)
        assistant = CodeAssistant(llm=client)
        result = assistant.fix(file_path, hint=prompt)
        click.echo(f"Applied {result.fix_count} fixes to {file_path}")


@cli.command()
@click.option(
    "--action",
    type=click.Choice(["install", "uninstall", "list", "search", "update"]),
    default="list",
    help="Plugin action.",
)
@click.argument("name", required=False)
def plugin(action: str, name: str):
    """Manage EoStudio plugins / extensions."""
    from eostudio.core.ide.extensions import ExtensionManager

    mgr = ExtensionManager()

    if action == "list":
        extensions = mgr.list_installed()
        if not extensions:
            click.echo("No plugins installed.")
            return
        for ext in extensions:
            click.echo(f"  {ext.name:30s}  v{ext.version}  {ext.description}")

    elif action == "search":
        if not name:
            click.echo("Error: NAME is required for search.", err=True)
            raise SystemExit(1)
        results = mgr.search(name)
        for ext in results:
            click.echo(f"  {ext.name:30s}  v{ext.version}  {ext.description}")

    elif action == "install":
        if not name:
            click.echo("Error: NAME is required for install.", err=True)
            raise SystemExit(1)
        mgr.install(name)
        click.echo(f"Plugin '{name}' installed.")

    elif action == "uninstall":
        if not name:
            click.echo("Error: NAME is required for uninstall.", err=True)
            raise SystemExit(1)
        mgr.uninstall(name)
        click.echo(f"Plugin '{name}' uninstalled.")

    elif action == "update":
        if name:
            mgr.update(name)
            click.echo(f"Plugin '{name}' updated.")
        else:
            updated = mgr.update_all()
            click.echo(f"Updated {len(updated)} plugins.")


@cli.command()
@click.option(
    "--action",
    type=click.Choice(["get", "set", "list", "reset"]),
    default="list",
    help="Config action.",
)
@click.option(
    "--scope",
    type=click.Choice(["user", "workspace"]),
    default="user",
    help="Configuration scope.",
)
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(action: str, scope: str, key: str, value: str):
    """Manage EoStudio configuration."""
    from eostudio.core.ide.config_manager import ConfigManager, ConfigScope

    mgr = ConfigManager()
    cfg_scope = ConfigScope.USER if scope == "user" else ConfigScope.WORKSPACE

    if action == "list":
        entries = mgr.list(cfg_scope)
        for k, v in entries.items():
            click.echo(f"  {k} = {v}")

    elif action == "get":
        if not key:
            click.echo("Error: KEY is required for get.", err=True)
            raise SystemExit(1)
        val = mgr.get(key, scope=cfg_scope)
        if val is None:
            click.echo(f"Key '{key}' not set.")
        else:
            click.echo(f"{key} = {val}")

    elif action == "set":
        if not key or value is None:
            click.echo("Error: KEY and VALUE are required for set.", err=True)
            raise SystemExit(1)
        mgr.set(key, value, scope=cfg_scope)
        click.echo(f"Set {key} = {value} [{scope}]")

    elif action == "reset":
        if key:
            mgr.reset(key, scope=cfg_scope)
            click.echo(f"Reset '{key}' to default [{scope}].")
        else:
            mgr.reset_all(scope=cfg_scope)
            click.echo(f"All {scope} settings reset to defaults.")


@cli.command()
def update():
    """Update EoStudio to the latest version."""
    import subprocess

    click.echo(f"Current version: {__version__}")
    click.echo("Checking for updates...")
    result = subprocess.run(
        ["pip", "install", "--upgrade", "EoStudio"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("EoStudio updated successfully.")
        click.echo(result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "")
    else:
        click.echo(f"Update failed:\n{result.stderr}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    cli()


if __name__ == "__main__":
    main()
