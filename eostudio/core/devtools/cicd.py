"""CI/CD pipeline builder — GitHub Actions, GitLab CI, and release video pipelines."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StepType(Enum):
    RUN = "run"
    CHECKOUT = "checkout"
    SETUP_PYTHON = "setup_python"
    INSTALL = "install"
    TEST = "test"
    BUILD = "build"
    PUBLISH = "publish"
    RELEASE_VIDEO = "release_video"
    UPLOAD_ARTIFACT = "upload_artifact"


@dataclass
class PipelineStep:
    """A single step in a CI/CD pipeline."""
    name: str
    step_type: StepType = StepType.RUN
    command: str = ""
    uses: str = ""
    with_params: Dict[str, str] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    condition: str = ""


@dataclass
class PipelineStage:
    """A stage grouping multiple steps."""
    name: str
    steps: List[PipelineStep] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    runs_on: str = "ubuntu-latest"


@dataclass
class Pipeline:
    """A complete CI/CD pipeline."""
    name: str
    stages: List[PipelineStage] = field(default_factory=list)
    triggers: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)


class PipelineTemplate(Enum):
    BASIC = "basic"
    TEST_AND_DEPLOY = "test_and_deploy"
    RELEASE_WITH_VIDEO = "release_with_video"


class PipelineBuilder:
    """Build CI/CD pipeline configurations."""

    def __init__(self, name: str = "CI/CD Pipeline") -> None:
        self.pipeline = Pipeline(name=name)

    def add_trigger(self, event: str, config: Any = None) -> "PipelineBuilder":
        self.pipeline.triggers[event] = config or {}
        return self

    def add_env(self, key: str, value: str) -> "PipelineBuilder":
        self.pipeline.env[key] = value
        return self

    def add_stage(self, stage: PipelineStage) -> "PipelineBuilder":
        self.pipeline.stages.append(stage)
        return self

    def add_release_video_step(self, stage_name: str = "Generate Release Video") -> "PipelineBuilder":
        """Add a release video generation stage to the pipeline."""
        stage = PipelineStage(
            name=stage_name,
            steps=[
                PipelineStep(
                    name="Install Manim and ffmpeg",
                    step_type=StepType.RUN,
                    command="sudo apt-get update && sudo apt-get install -y ffmpeg\n"
                            "pip install manim edge-tts",
                ),
                PipelineStep(
                    name="Generate release video",
                    step_type=StepType.RELEASE_VIDEO,
                    command='python -c "\n'
                            "from eostudio.core.video.release_video import (\n"
                            "    ChangelogParser, ReleaseVideoConfig, ReleaseVideoGenerator\n"
                            ")\n"
                            "parser = ChangelogParser()\n"
                            "changelog = parser.parse_latest_release()\n"
                            "config = ReleaseVideoConfig(\n"
                            "    version=changelog.version,\n"
                            "    changelog=changelog,\n"
                            "    output_dir='./release-artifacts/video',\n"
                            ")\n"
                            "gen = ReleaseVideoGenerator(config)\n"
                            "result = gen.generate()\n"
                            "print(f'Video: {result[\"final_video_path\"]}')\n"
                            '"',
                ),
                PipelineStep(
                    name="Upload video artifact",
                    step_type=StepType.UPLOAD_ARTIFACT,
                    uses="actions/upload-artifact@v4",
                    with_params={
                        "name": "release-video",
                        "path": "release-artifacts/video/*.mp4",
                    },
                ),
            ],
        )
        self.pipeline.stages.append(stage)
        return self

    def build(self) -> Pipeline:
        return self.pipeline

    def to_github_actions_yaml(self) -> str:
        """Generate GitHub Actions YAML from the pipeline."""
        lines = [f"name: {self.pipeline.name}", ""]

        # Triggers
        if self.pipeline.triggers:
            lines.append("on:")
            for event, config in self.pipeline.triggers.items():
                if isinstance(config, dict) and config:
                    lines.append(f"  {event}:")
                    for key, val in config.items():
                        if isinstance(val, list):
                            lines.append(f"    {key}:")
                            for item in val:
                                lines.append(f'      - "{item}"')
                        else:
                            lines.append(f"    {key}: {val}")
                else:
                    lines.append(f"  {event}:")
            lines.append("")

        # Env
        if self.pipeline.env:
            lines.append("env:")
            for k, v in self.pipeline.env.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        # Jobs
        lines.append("jobs:")
        for stage in self.pipeline.stages:
            job_id = stage.name.lower().replace(" ", "-").replace("/", "-")
            lines.append(f"  {job_id}:")
            lines.append(f"    name: {stage.name}")
            lines.append(f"    runs-on: {stage.runs_on}")

            if stage.depends_on:
                needs = ", ".join(
                    n.lower().replace(" ", "-") for n in stage.depends_on
                )
                lines.append(f"    needs: [{needs}]")

            lines.append("    steps:")
            lines.append("      - uses: actions/checkout@v4")
            lines.append("      - uses: actions/setup-python@v5")
            lines.append("        with:")
            lines.append("          python-version: '3.11'")

            for step in stage.steps:
                lines.append(f"      - name: {step.name}")
                if step.uses:
                    lines.append(f"        uses: {step.uses}")
                    if step.with_params:
                        lines.append("        with:")
                        for k, v in step.with_params.items():
                            lines.append(f"          {k}: {v}")
                elif step.command:
                    lines.append(f"        run: |")
                    for cmd_line in step.command.splitlines():
                        lines.append(f"          {cmd_line}")

                if step.env:
                    lines.append("        env:")
                    for k, v in step.env.items():
                        lines.append(f"          {k}: {v}")

                if step.condition:
                    lines.append(f"        if: {step.condition}")

            lines.append("")

        return "\n".join(lines)


# ── Pre-built Templates ─────────────────────────────────────────────────────

def create_release_with_video_pipeline(product_name: str = "EoStudio") -> PipelineBuilder:
    """Create a complete release pipeline with video generation."""
    builder = PipelineBuilder(name=f"{product_name} Release with Video")
    builder.add_trigger("push", {"tags": ["v*"]})

    # Stage 1: Test
    builder.add_stage(PipelineStage(
        name="Test",
        steps=[
            PipelineStep(name="Install dependencies", command="pip install -e '.[dev]'"),
            PipelineStep(name="Run tests", step_type=StepType.TEST, command="pytest"),
        ],
    ))

    # Stage 2: Build
    builder.add_stage(PipelineStage(
        name="Build",
        depends_on=["Test"],
        steps=[
            PipelineStep(name="Build package", step_type=StepType.BUILD, command="python -m build"),
        ],
    ))

    # Stage 3: Release Video
    builder.add_release_video_step()
    builder.pipeline.stages[-1].depends_on = ["Build"]

    # Stage 4: Publish
    builder.add_stage(PipelineStage(
        name="Publish",
        depends_on=["Build", "Generate Release Video"],
        steps=[
            PipelineStep(
                name="Publish to PyPI",
                step_type=StepType.PUBLISH,
                command="twine upload dist/*",
                env={"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": "${{ secrets.PYPI_TOKEN }}"},
            ),
            PipelineStep(
                name="Create GitHub Release",
                command='gh release create "${{ github.ref_name }}" dist/* --generate-notes',
                env={"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"},
            ),
            PipelineStep(
                name="Upload release video",
                command='gh release upload "${{ github.ref_name }}" release-artifacts/video/*.mp4',
                env={"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"},
            ),
        ],
    ))

    return builder
