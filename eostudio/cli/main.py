"""EoStudio CLI — Command-line interface for EoStudio."""

import click

from eostudio import __version__


@click.group()
@click.version_option(version=__version__, prog_name="EoStudio")
def cli():
    """EoStudio — Cross-Platform Design Suite with LLM Integration."""


@cli.command()
@click.option(
    "--editor",
    type=click.Choice([
        "3d", "cad", "paint", "game", "ui", "product",
        "interior", "uml", "simulation", "database", "ide", "promo", "all",
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
@click.argument("project_file")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["stl", "obj", "svg", "gltf", "dxf", "png"]),
    required=True,
)
@click.option("--output", "-o", required=True, help="Output file path.")
def export(project_file: str, fmt: str, output: str):
    """Export a design project to a specific format."""
    from eostudio.formats.project import EoStudioProject

    project = EoStudioProject.load(project_file)
    project.export(fmt, output)
    click.echo(f"Exported {project_file} -> {output} ({fmt})")


@cli.command()
@click.argument("project_file")
@click.option(
    "--framework",
    type=click.Choice([
        "html", "flutter", "compose", "react", "openscad",
        "react-framer-motion", "react-gsap", "react-css-animations",
        "mobile-flutter", "mobile-react-native", "mobile-kotlin", "mobile-swift",
        "desktop-electron", "desktop-tauri", "desktop-tkinter", "desktop-qt",
        "webapp-react-fastapi", "webapp-vue-flask", "webapp-angular-express",
        "database-sql", "database-sqlalchemy", "database-prisma", "database-django",
    ]),
    required=True,
)
@click.option("--output", "-o", required=True, help="Output directory.")
def codegen(project_file: str, framework: str, output: str):
    """Generate code from a UI/3D design project."""
    from eostudio.codegen import generate_code

    generate_code(project_file, framework, output)
    click.echo(f"Generated {framework} code -> {output}")


@cli.command()
@click.option(
    "--lesson",
    type=click.Choice([
        "shapes", "colors", "3d-basics", "simple-game",
        "build-robot", "design-house",
    ]),
    default="shapes",
)
@click.option(
    "--difficulty",
    type=click.Choice(["beginner", "intermediate", "advanced"]),
    default="beginner",
)
def teach(lesson: str, difficulty: str):
    """Launch LLM-powered kids learning mode."""
    from eostudio.core.ai.tutor import KidsTutor

    tutor = KidsTutor(lesson=lesson, difficulty=difficulty)
    tutor.start_interactive()


@cli.command()
@click.option("--endpoint", default="http://localhost:11434", help="LLM API endpoint.")
@click.option("--model", default="llama3", help="LLM model name.")
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai"]),
    default="ollama",
    help="LLM provider backend.",
)
@click.option("--api-key", default="", help="API key (required for OpenAI).")
@click.option(
    "--domain",
    type=click.Choice([
        "general", "cad", "ui", "3d", "game",
        "hardware", "simulation", "database", "uml",
    ]),
    default="general",
    help="Design domain for context-aware prompts.",
)
@click.argument("prompt")
def ask(endpoint: str, model: str, provider: str, api_key: str, domain: str, prompt: str):
    """Ask the AI design agent a question."""
    from eostudio.core.ai.agent import DesignAgent

    agent = DesignAgent(
        endpoint=endpoint, model=model,
        provider=provider, api_key=api_key, domain=domain,
    )
    response = agent.ask(prompt)
    click.echo(response)


@cli.command()
@click.argument("diagram_file")
@click.option(
    "--language",
    type=click.Choice(["python", "java", "kotlin", "typescript", "cpp", "csharp"]),
    required=True,
)
@click.option("--output", "-o", required=True, help="Output directory.")
def uml_codegen(diagram_file: str, language: str, output: str):
    """Generate code from a UML class diagram."""
    import json
    import os
    from eostudio.core.uml.diagrams import ClassDiagram
    from eostudio.core.uml.code_gen import UMLCodeGen

    with open(diagram_file) as f:
        data = json.load(f)
    diagram = ClassDiagram.from_dict(data)
    gen = UMLCodeGen()
    generators = {
        "python": gen.generate_python,
        "java": gen.generate_java,
        "kotlin": gen.generate_kotlin,
        "typescript": gen.generate_typescript,
        "cpp": gen.generate_cpp,
        "csharp": gen.generate_csharp,
    }
    files = generators[language](diagram)
    os.makedirs(output, exist_ok=True)
    for filename, content in files.items():
        filepath = os.path.join(output, filename)
        with open(filepath, "w") as f:
            f.write(content)
    click.echo(f"Generated {language} code from UML -> {output} ({len(files)} files)")


@cli.command()
@click.option("--dt", default=0.01, help="Simulation time step.")
@click.option("--duration", default=10.0, help="Simulation duration in seconds.")
@click.argument("model_file")
def simulate(model_file: str, dt: float, duration: float):
    """Run a MATLAB-style simulation model."""
    import json
    from eostudio.core.simulation.engine import SimulationModel

    with open(model_file) as f:
        data = json.load(f)
    model = SimulationModel.from_dict(data)
    model.dt = dt
    model.duration = duration
    results = model.run()
    click.echo(f"Simulation complete: {len(results)} signals captured over {duration}s")
    for name, signal in results.items():
        click.echo(f"  {name}: {signal.num_samples()} samples, "
                    f"mean={signal.mean():.4f}, rms={signal.rms():.4f}")


@cli.command()
@click.argument("schema_file")
@click.option(
    "--dialect",
    type=click.Choice(["sqlite", "postgresql", "mysql", "sqlalchemy", "prisma", "django"]),
    default="sqlite",
)
@click.option("--output", "-o", required=True, help="Output file path.")
def dbgen(schema_file: str, dialect: str, output: str):
    """Generate database code from a schema design."""
    import json
    from eostudio.codegen.database import (
        DatabaseSchema, generate_sql, generate_sqlalchemy,
        generate_prisma, generate_django_models,
    )

    with open(schema_file) as f:
        data = json.load(f)
    schema = DatabaseSchema.from_dict(data)
    generators = {
        "sqlite": lambda s: generate_sql(s, "sqlite"),
        "postgresql": lambda s: generate_sql(s, "postgresql"),
        "mysql": lambda s: generate_sql(s, "mysql"),
        "sqlalchemy": generate_sqlalchemy,
        "prisma": generate_prisma,
        "django": generate_django_models,
    }
    result = generators[dialect](schema)
    with open(output, "w") as f:
        f.write(result)
    click.echo(f"Generated {dialect} schema -> {output}")


@cli.command()
@click.argument("path", default=".")
@click.option("--theme", type=click.Choice(["dark", "light"]), default="dark")
def ide(path: str, theme: str):
    """Launch the EoStudio IDE (code editor with Git, extensions, terminal)."""
    from eostudio.gui.app import EoStudioApp

    app = EoStudioApp(editor="ide", theme=theme)
    app.run()


@cli.command()
@click.option(
    "--template",
    type=click.Choice([
        "todo-app", "mechanical-part", "game-platformer",
        "iot-dashboard", "simulation-pid",
    ]),
    required=True,
    help="Project template to use.",
)
@click.option("--output", "-o", required=True, help="Output directory.")
@click.option("--list-templates", "show_list", is_flag=True, help="List available templates.")
def new(template: str, output: str, show_list: bool):
    """Create a new project from a template."""
    from eostudio.templates.samples import list_templates, create_project_from_template

    if show_list:
        for tmpl in list_templates():
            click.echo(f"  {tmpl.name:20s} — {tmpl.description}")
        return

    project_path = create_project_from_template(template, output)
    click.echo(f"Created project from '{template}' template -> {project_path}")


@cli.command()
@click.argument("project_file")
@click.option(
    "--framework",
    type=click.Choice(["react-framer-motion", "react-gsap", "react-css"]),
    default="react-framer-motion",
    help="Animation library to target.",
)
@click.option("--output", "-o", required=True, help="Output directory.")
def react_motion(project_file: str, framework: str, output: str):
    """Generate React code with animations (Framer Motion / GSAP / CSS)."""
    from eostudio.formats.project import EoStudioProject
    from eostudio.codegen.react_motion import ReactMotionGenerator
    from eostudio.core.animation.timeline import AnimationTimeline

    project = EoStudioProject.load(project_file)
    scene_data = project.scenes.get(project.active_scene, {})
    components = scene_data.get("components", [])
    screens = scene_data.get("screens", [])

    lib_map = {"react-framer-motion": "framer-motion", "react-gsap": "gsap", "react-css": "css"}
    timeline_data = scene_data.get("animation_timeline")
    timeline = AnimationTimeline.from_dict(timeline_data) if timeline_data else AnimationTimeline()

    gen = ReactMotionGenerator(library=lib_map[framework])
    files = gen.generate(timeline, components, screens)

    import os
    os.makedirs(output, exist_ok=True)
    for fname, content in files.items():
        path = os.path.join(output, fname)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    click.echo(f"Generated {framework} app ({len(files)} files) -> {output}")


@cli.command()
@click.argument("prompt")
@click.option("--style", default="modern", help="Design style (modern, minimal, bold, playful).")
@click.option("--output", "-o", default=None, help="Output JSON file.")
def generate_ui(prompt: str, style: str, output: str):
    """AI-generate a UI design with animations from a text prompt."""
    from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
    import json

    gen = AIDesignGeneratorPro()
    result = gen.text_to_animated_ui(prompt, style=style)

    formatted = json.dumps(result, indent=2)
    if output:
        with open(output, "w") as f:
            f.write(formatted)
        click.echo(f"Generated animated UI design -> {output}")
    else:
        click.echo(formatted)


@cli.command()
@click.argument("prompt")
@click.option("--output", "-o", default=None, help="Output JSON file.")
def design_system(prompt: str, output: str):
    """AI-generate a design system (tokens, colors, typography) from a brand description."""
    from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
    import json

    gen = AIDesignGeneratorPro()
    result = gen.text_to_design_system(prompt)

    formatted = json.dumps(result, indent=2)
    if output:
        with open(output, "w") as f:
            f.write(formatted)
        click.echo(f"Generated design system -> {output}")
    else:
        click.echo(formatted)


@cli.command()
@click.argument("image_path")
@click.option("--output", "-o", default=None, help="Output JSON file.")
def screenshot_to_ui(image_path: str, output: str):
    """Convert a screenshot/image to UI component structure using AI vision."""
    from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
    import json

    gen = AIDesignGeneratorPro()
    result = gen.screenshot_to_ui(image_path)

    formatted = json.dumps(result, indent=2)
    if output:
        with open(output, "w") as f:
            f.write(formatted)
        click.echo(f"Extracted UI from screenshot -> {output}")
    else:
        click.echo(formatted)


@cli.command()
@click.argument("project_file")
@click.option(
    "--template",
    type=click.Choice([
        "app_store_preview", "social_square", "product_launch",
        "twitter_card", "linkedin_post", "product_hunt",
    ]),
    default="social_square",
    help="Promo template to use.",
)
@click.option("--output", "-o", required=True, help="Output directory for rendered frames.")
@click.option("--product-name", default="My Product", help="Product name for the promo.")
@click.option("--tagline", default="The next big thing", help="Tagline text.")
def promo(project_file: str, template: str, output: str, product_name: str, tagline: str):
    """Generate promotional content (App Store, social media, product launch)."""
    from eostudio.core.video.promo_templates import get_template
    import json, os

    tmpl = get_template(template)
    if not tmpl:
        click.echo(f"Unknown template: {template}")
        return

    compositor = tmpl.create_compositor(
        product_name=product_name, tagline=tagline,
        app_name=product_name, product=product_name,
    )

    frames = compositor.render_all_frames()
    os.makedirs(output, exist_ok=True)

    manifest_path = os.path.join(output, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({
            "template": template,
            "width": compositor.width,
            "height": compositor.height,
            "fps": compositor.fps,
            "duration": compositor.duration,
            "total_frames": len(frames),
            "ffmpeg_command": compositor.generate_ffmpeg_command(
                os.path.join(output, "output.mp4"), output
            ),
        }, f, indent=2)

    click.echo(f"Promo '{template}' ({compositor.width}x{compositor.height}) -> {output}")
    click.echo(f"  {len(frames)} frames, {compositor.duration}s duration")
    click.echo(f"  Run ffmpeg command in manifest.json to render video")


@cli.command()
@click.argument("project_file")
@click.option("--output", "-o", required=True, help="Output HTML file.")
@click.option("--device", default="iphone_14", help="Device frame for prototype.")
def prototype(project_file: str, output: str, device: str):
    """Export an interactive HTML prototype from a design project."""
    from eostudio.formats.project import EoStudioProject
    from eostudio.core.prototyping.player import PrototypePlayer, PrototypeScreen

    project = EoStudioProject.load(project_file)
    scene_data = project.scenes.get(project.active_scene, {})
    screens = scene_data.get("screens", [{"name": "Home", "components": scene_data.get("components", [])}])

    player = PrototypePlayer()
    for screen in screens:
        player.add_screen(PrototypeScreen(
            id=screen.get("name", "screen").lower().replace(" ", "_"),
            name=screen.get("name", "Screen"),
            components=screen.get("components", []),
            device_frame=device,
        ))

    html = player.export_html()
    with open(output, "w") as f:
        f.write(html)
    click.echo(f"Interactive prototype ({len(screens)} screens, {device}) -> {output}")


@cli.command()
@click.argument("brand_color")
@click.option("--style", default="modern", help="Palette style.")
@click.option("--output", "-o", default=None, help="Output JSON file.")
def palette(brand_color: str, style: str, output: str):
    """Generate a full color palette from a brand color (e.g. #2563eb)."""
    from eostudio.core.ai.generator_pro import AIDesignGeneratorPro
    import json

    gen = AIDesignGeneratorPro()
    result = gen.generate_palette(brand_color, style=style)

    formatted = json.dumps(result, indent=2)
    if output:
        with open(output, "w") as f:
            f.write(formatted)
        click.echo(f"Generated palette from {brand_color} -> {output}")
    else:
        click.echo(formatted)


@cli.command()
@click.argument("prompt")
@click.option("--framework", default="react", help="Target framework.")
@click.option("--output", "-o", default=None, help="Output markdown/JSON file.")
def spec(prompt: str, framework: str, output: str):
    """Generate full spec: requirements → design → tech → tasks (like Kiro.dev)."""
    from eostudio.core.specs.spec_engine import SpecEngine
    import json

    engine = SpecEngine()
    result = engine.generate_full_spec(prompt, framework)

    if output and output.endswith(".md"):
        md = engine.export_markdown(result)
        with open(output, "w") as f:
            f.write(md)
        click.echo(f"Full spec exported to {output}")
    elif output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        click.echo(f"Full spec JSON exported to {output}")
    else:
        md = engine.export_markdown(result)
        click.echo(md)


@cli.command()
@click.argument("spec_file")
@click.option("--framework", default="react", help="Target framework.")
@click.option("--output", "-o", required=True, help="Output directory.")
@click.option("--max-iterations", default=5, help="Max agent iterations.")
def agent(spec_file: str, framework: str, output: str, max_iterations: int):
    """Run agentic AI loop: generate → test → fix → refine (like Kiro.dev)."""
    import json
    from eostudio.core.ai.agent_loop import AgenticAILoop, AgentConfig

    with open(spec_file) as f:
        spec_data = json.load(f)

    config = AgentConfig(framework=framework, output_dir=output,
                         max_iterations=max_iterations)
    agent_loop = AgenticAILoop(config=config)

    def on_progress(state, msg):
        click.echo(f"  [{state.value}] {msg}")

    agent_loop.on_progress(on_progress)
    result = agent_loop.run(spec_data)
    click.echo(f"\nAgent completed: {result['state']} ({result['iterations']} iterations, {len(result['files'])} files)")


@cli.command()
@click.option("--output", "-o", required=True, help="Output directory.")
@click.option("--components", "-c", multiple=True, help="Specific components to generate.")
def ui_kit(output: str, components: tuple):
    """Generate production UI kit (30+ React components like shadcn/ui)."""
    import os
    from eostudio.codegen.ui_kit import UIKitGenerator

    gen = UIKitGenerator()
    if components:
        files = {}
        for name in components:
            code = gen.generate_component(name)
            if code:
                files[f"src/components/ui/{name.lower()}.tsx"] = code
    else:
        files = gen.generate_all()

    os.makedirs(output, exist_ok=True)
    for fname, content in files.items():
        path = os.path.join(output, fname)
        os.makedirs(os.path.dirname(path) or output, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
    click.echo(f"Generated {len(files)} UI kit files -> {output}")


@cli.command()
@click.argument("project_dir")
@click.option("--target", type=click.Choice(["docker", "vercel", "netlify", "github_pages", "fly_io", "railway"]),
              default="docker")
@click.option("--name", default="my-app", help="Project name.")
def deploy(project_dir: str, target: str, name: str):
    """Generate deployment configs (Docker, Vercel, Netlify, GitHub Pages)."""
    from eostudio.core.deploy import Deployer, DeployTarget, DeployConfig

    config = DeployConfig(target=DeployTarget(target), project_name=name)
    deployer = Deployer()
    result = deployer.deploy(config)
    written = deployer.write_files(result, project_dir)

    click.echo(f"Generated {target} deployment config:")
    for f in written:
        click.echo(f"  {f}")
    if result.commands:
        click.echo("\nDeploy commands:")
        for cmd in result.commands:
            click.echo(f"  $ {cmd}")


@cli.command()
@click.argument("prompt")
@click.option("--framework", default="react", help="Target framework.")
@click.option("--output", "-o", required=True, help="Output directory.")
@click.option("--deploy-to", default="docker", help="Deployment target.")
def build(prompt: str, framework: str, output: str, deploy_to: str):
    """Full pipeline: prompt → spec → code → tests → deploy config (end-to-end)."""
    import json, os
    from eostudio.core.specs.spec_engine import SpecEngine
    from eostudio.core.ai.agent_loop import AgenticAILoop, AgentConfig
    from eostudio.codegen.ui_kit import UIKitGenerator
    from eostudio.core.deploy import Deployer, DeployTarget, DeployConfig

    click.echo("Step 1/4: Generating spec...")
    engine = SpecEngine()
    spec_data = engine.generate_full_spec(prompt, framework)

    spec_path = os.path.join(output, "spec.json")
    os.makedirs(output, exist_ok=True)
    with open(spec_path, "w") as f:
        json.dump(spec_data, f, indent=2)
    click.echo(f"  Spec: {spec_path}")

    md_path = os.path.join(output, "SPEC.md")
    with open(md_path, "w") as f:
        f.write(engine.export_markdown(spec_data))
    click.echo(f"  Markdown: {md_path}")

    click.echo("Step 2/4: Generating code...")
    config = AgentConfig(framework=framework, output_dir=output, auto_test=False)
    agent_loop = AgenticAILoop(config=config)
    result = agent_loop.run(spec_data)
    click.echo(f"  Generated {len(result['files'])} files")

    click.echo("Step 3/4: Adding UI kit...")
    ui_files = UIKitGenerator().generate_all()
    for fname, content in ui_files.items():
        path = os.path.join(output, fname)
        os.makedirs(os.path.dirname(path) or output, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
    click.echo(f"  Added {len(ui_files)} UI components")

    click.echo("Step 4/4: Generating deploy config...")
    deploy_config = DeployConfig(target=DeployTarget(deploy_to),
                                  project_name=prompt[:20].lower().replace(" ", "-"))
    deployer = Deployer()
    deploy_result = deployer.deploy(deploy_config)
    deployer.write_files(deploy_result, output)
    click.echo(f"  Deploy target: {deploy_to}")

    click.echo(f"\nDone! Full project at: {output}")
    click.echo(f"  {len(result['files']) + len(ui_files)} total files")


def main():
    cli()


if __name__ == "__main__":
    main()
