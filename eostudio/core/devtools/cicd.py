"""CI/CD pipeline builder and monitor."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class CIProvider(Enum):
    """Supported CI/CD providers."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    CIRCLECI = "circleci"
    AZURE_PIPELINES = "azure_pipelines"


@dataclass
class PipelineStep:
    """A single step within a pipeline stage."""
    name: str
    command: str
    image: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None
    timeout: int = 0
    artifacts: List[str] = field(default_factory=list)
    cache: List[str] = field(default_factory=list)


@dataclass
class PipelineStage:
    """A stage containing one or more pipeline steps."""
    name: str
    steps: List[PipelineStep] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    parallel: bool = False


@dataclass
class Pipeline:
    """A complete CI/CD pipeline definition."""
    name: str
    stages: List[PipelineStage] = field(default_factory=list)
    triggers: Dict[str, object] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    provider: CIProvider = CIProvider.GITHUB_ACTIONS


@dataclass
class PipelineTemplate:
    """A reusable pipeline template."""
    name: str
    description: str
    provider: CIProvider
    pipeline: Pipeline


class PipelineBuilder:
    """Builds CI/CD pipeline configurations for various providers."""

    def __init__(self, provider: CIProvider = CIProvider.GITHUB_ACTIONS) -> None:
        self.provider = provider
        self._stages: Dict[str, PipelineStage] = {}
        self._triggers: Dict[str, object] = {}
        self._env: Dict[str, str] = {}
        self._name: str = "pipeline"

    def add_stage(self, name: str) -> PipelineStage:
        """Add a new stage to the pipeline."""
        stage = PipelineStage(name=name)
        self._stages[name] = stage
        return stage

    def add_step(self, stage: str, step: PipelineStep) -> None:
        """Add a step to an existing stage."""
        if stage not in self._stages:
            self.add_stage(stage)
        self._stages[stage].steps.append(step)

    def set_trigger(self, event: str, branches: Optional[List[str]] = None) -> None:
        """Set a trigger event for the pipeline."""
        if branches:
            self._triggers[event] = {"branches": branches}
        else:
            self._triggers[event] = {}

    def build(self) -> Pipeline:
        """Build and return the pipeline object."""
        return Pipeline(
            name=self._name,
            stages=list(self._stages.values()),
            triggers=dict(self._triggers),
            env=dict(self._env),
            provider=self.provider,
        )

    def validate(self) -> List[str]:
        """Validate the pipeline configuration. Returns a list of errors."""
        errors: List[str] = []
        if not self._stages:
            errors.append("Pipeline has no stages defined")
        for stage_name, stage in self._stages.items():
            if not stage.steps:
                errors.append(f"Stage '{stage_name}' has no steps")
            for step in stage.steps:
                if not step.command:
                    errors.append(
                        f"Step '{step.name}' in stage '{stage_name}' has no command"
                    )
            for dep in stage.depends_on:
                if dep not in self._stages:
                    errors.append(
                        f"Stage '{stage_name}' depends on unknown stage '{dep}'"
                    )
        if not self._triggers:
            errors.append("Pipeline has no triggers defined")
        return errors

    def to_yaml(self) -> str:
        """Generate YAML configuration for the selected provider."""
        pipeline = self.build()
        if self.provider == CIProvider.GITHUB_ACTIONS:
            return self._to_github_actions(pipeline)
        elif self.provider == CIProvider.GITLAB_CI:
            return self._to_gitlab_ci(pipeline)
        else:
            return self._to_github_actions(pipeline)

    def _to_github_actions(self, pipeline: Pipeline) -> str:
        """Generate GitHub Actions workflow YAML."""
        lines: List[str] = []
        lines.append(f"name: {pipeline.name}")
        lines.append("")

        # Triggers
        if pipeline.triggers:
            lines.append("on:")
            for event, config in pipeline.triggers.items():
                if isinstance(config, dict) and config:
                    lines.append(f"  {event}:")
                    if "branches" in config:
                        lines.append("    branches:")
                        for branch in config["branches"]:
                            lines.append(f"      - {branch}")
                else:
                    lines.append(f"  {event}:")
        lines.append("")

        # Environment
        if pipeline.env:
            lines.append("env:")
            for key, value in pipeline.env.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Jobs
        lines.append("jobs:")
        for stage in pipeline.stages:
            job_id = stage.name.replace(" ", "-").replace("/", "-").lower()
            lines.append(f"  {job_id}:")
            lines.append(f"    name: {stage.name}")
            lines.append("    runs-on: ubuntu-latest")

            if stage.depends_on:
                needs = [
                    d.replace(" ", "-").replace("/", "-").lower()
                    for d in stage.depends_on
                ]
                needs_str = ", ".join(needs)
                lines.append(f"    needs: [{needs_str}]")

            lines.append("    steps:")
            lines.append("      - uses: actions/checkout@v4")

            for step in stage.steps:
                lines.append(f"      - name: {step.name}")
                if step.condition:
                    lines.append(f"        if: {step.condition}")
                if step.timeout:
                    lines.append(f"        timeout-minutes: {step.timeout}")
                lines.append(f"        run: {step.command}")
                if step.env:
                    lines.append("        env:")
                    for ek, ev in step.env.items():
                        lines.append(f"          {ek}: {ev}")

            # Cache
            cache_paths: List[str] = []
            for step in stage.steps:
                cache_paths.extend(step.cache)
            if cache_paths:
                lines.append("      - uses: actions/cache@v3")
                lines.append("        with:")
                lines.append("          path: |")
                for cp in cache_paths:
                    lines.append(f"            {cp}")
                lines.append(
                    "          key: ${{ runner.os }}-cache-${{ hashFiles('**/*') }}"
                )

            # Artifacts
            artifact_paths: List[str] = []
            for step in stage.steps:
                artifact_paths.extend(step.artifacts)
            if artifact_paths:
                lines.append("      - uses: actions/upload-artifact@v3")
                lines.append("        with:")
                lines.append(f"          name: {job_id}-artifacts")
                lines.append("          path: |")
                for ap in artifact_paths:
                    lines.append(f"            {ap}")

            lines.append("")

        return "\n".join(lines)

    def _to_gitlab_ci(self, pipeline: Pipeline) -> str:
        """Generate GitLab CI YAML."""
        lines: List[str] = []

        # Stages declaration
        lines.append("stages:")
        for stage in pipeline.stages:
            lines.append(f"  - {stage.name}")
        lines.append("")

        # Variables
        if pipeline.env:
            lines.append("variables:")
            for key, value in pipeline.env.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Jobs
        for stage in pipeline.stages:
            for step in stage.steps:
                job_name = (
                    f"{stage.name}:{step.name}"
                    .replace(" ", "_")
                    .replace("/", "_")
                    .lower()
                )
                lines.append(f"{job_name}:")
                lines.append(f"  stage: {stage.name}")

                if step.image:
                    lines.append(f"  image: {step.image}")

                lines.append("  script:")
                for cmd_line in step.command.split("\n"):
                    lines.append(f"    - {cmd_line.strip()}")

                if step.env:
                    lines.append("  variables:")
                    for ek, ev in step.env.items():
                        lines.append(f"    {ek}: {ev}")

                if stage.depends_on:
                    lines.append("  needs:")
                    for dep in stage.depends_on:
                        lines.append(f"    - {dep}")

                if step.condition:
                    lines.append("  rules:")
                    lines.append(f"    - if: {step.condition}")

                if step.timeout:
                    lines.append(f"  timeout: {step.timeout}m")

                if step.artifacts:
                    lines.append("  artifacts:")
                    lines.append("    paths:")
                    for ap in step.artifacts:
                        lines.append(f"      - {ap}")

                if step.cache:
                    lines.append("  cache:")
                    lines.append("    paths:")
                    for cp in step.cache:
                        lines.append(f"      - {cp}")

                lines.append("")

        return "\n".join(lines)

    def from_yaml(self, yaml_str: str) -> Pipeline:
        """Parse a YAML string into a Pipeline object.

        Simplified parser for basic key-value YAML structures.
        For production use, consider a full YAML library.
        """
        pipeline = Pipeline(
            name="imported",
            provider=self.provider,
        )

        lines = yaml_str.strip().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("name:"):
                pipeline.name = stripped.split(":", 1)[1].strip()
                break

        return pipeline

    def save(self, path: str) -> None:
        """Write the pipeline configuration to a file."""
        yaml_content = self.to_yaml()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(yaml_content)

    def load(self, path: str) -> Pipeline:
        """Load a pipeline configuration from a file."""
        with open(path, "r") as f:
            content = f.read()
        return self.from_yaml(content)

    def get_templates(self) -> List[PipelineTemplate]:
        """Return built-in pipeline templates."""
        templates: List[PipelineTemplate] = []

        # Python CI template
        py_builder = PipelineBuilder(CIProvider.GITHUB_ACTIONS)
        py_builder._name = "Python CI"
        py_builder.set_trigger("push", ["main"])
        py_builder.set_trigger("pull_request", ["main"])
        lint_stage = py_builder.add_stage("lint")
        lint_stage.steps.append(PipelineStep(
            name="Lint",
            command="pip install flake8 && flake8 .",
        ))
        test_stage = py_builder.add_stage("test")
        test_stage.steps.append(PipelineStep(
            name="Test",
            command="pip install -r requirements.txt && pytest",
            cache=["~/.cache/pip"],
        ))
        templates.append(PipelineTemplate(
            name="python-ci",
            description="Python CI with linting and testing",
            provider=CIProvider.GITHUB_ACTIONS,
            pipeline=py_builder.build(),
        ))

        # Node.js CI template
        node_builder = PipelineBuilder(CIProvider.GITHUB_ACTIONS)
        node_builder._name = "Node.js CI"
        node_builder.set_trigger("push", ["main"])
        node_builder.set_trigger("pull_request", ["main"])
        build_stage = node_builder.add_stage("build")
        build_stage.steps.append(PipelineStep(
            name="Install & Build",
            command="npm ci && npm run build",
            cache=["node_modules"],
        ))
        test_stage_node = node_builder.add_stage("test")
        test_stage_node.depends_on = ["build"]
        test_stage_node.steps.append(PipelineStep(
            name="Test",
            command="npm test",
        ))
        templates.append(PipelineTemplate(
            name="node-ci",
            description="Node.js CI with build and test",
            provider=CIProvider.GITHUB_ACTIONS,
            pipeline=node_builder.build(),
        ))

        # Docker build & push template
        docker_builder = PipelineBuilder(CIProvider.GITHUB_ACTIONS)
        docker_builder._name = "Docker Build & Push"
        docker_builder.set_trigger("push", ["main"])
        docker_stage = docker_builder.add_stage("docker")
        docker_stage.steps.append(PipelineStep(
            name="Build and Push",
            command="docker build -t $IMAGE_NAME:$GITHUB_SHA . && docker push $IMAGE_NAME:$GITHUB_SHA",
        ))
        templates.append(PipelineTemplate(
            name="docker-build",
            description="Docker build and push pipeline",
            provider=CIProvider.GITHUB_ACTIONS,
            pipeline=docker_builder.build(),
        ))

        return templates

    def create_from_template(self, template_name: str) -> Pipeline:
        """Create a pipeline from a built-in template name."""
        for template in self.get_templates():
            if template.name == template_name:
                self._name = template.pipeline.name
                self._stages = {s.name: s for s in template.pipeline.stages}
                self._triggers = dict(template.pipeline.triggers)
                self._env = dict(template.pipeline.env)
                return template.pipeline
        raise ValueError(f"Unknown template: {template_name}")


class BuildMonitor:
    """Monitors CI/CD build status across providers."""

    def _lazy_get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict:
        """Make an HTTP GET request using httpx (lazily imported)."""
        try:
            import httpx
        except ImportError:
            return {"error": "httpx not installed"}
        try:
            resp = httpx.get(url, headers=headers or {}, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_status(self, provider: CIProvider, repo: str) -> Dict:
        """Check the latest build status for a repository."""
        if provider == CIProvider.GITHUB_ACTIONS:
            url = f"https://api.github.com/repos/{repo}/actions/runs?per_page=1"
            data = self._lazy_get(url)
            if "error" in data:
                return data
            runs = data.get("workflow_runs", [])
            if not runs:
                return {"status": "no_runs"}
            run = runs[0]
            return {
                "id": run.get("id"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "branch": run.get("head_branch"),
                "commit": run.get("head_sha", "")[:8],
                "url": run.get("html_url"),
                "created_at": run.get("created_at"),
            }
        elif provider == CIProvider.GITLAB_CI:
            encoded_repo = repo.replace("/", "%2F")
            url = f"https://gitlab.com/api/v4/projects/{encoded_repo}/pipelines?per_page=1"
            data = self._lazy_get(url)
            if isinstance(data, dict) and "error" in data:
                return data
            if isinstance(data, list) and data:
                pipe = data[0]
                return {
                    "id": pipe.get("id"),
                    "status": pipe.get("status"),
                    "ref": pipe.get("ref"),
                    "url": pipe.get("web_url"),
                    "created_at": pipe.get("created_at"),
                }
            return {"status": "no_pipelines"}
        return {"error": f"Unsupported provider: {provider.value}"}

    def get_logs(self, provider: CIProvider, repo: str, build_id: str) -> str:
        """Get build logs for a specific build run."""
        if provider == CIProvider.GITHUB_ACTIONS:
            url = f"https://api.github.com/repos/{repo}/actions/runs/{build_id}/logs"
            try:
                import httpx
            except ImportError:
                return "httpx not installed"
            try:
                resp = httpx.get(url, timeout=30, follow_redirects=True)
                return resp.text
            except Exception as e:
                return f"Error fetching logs: {e}"
        elif provider == CIProvider.GITLAB_CI:
            encoded_repo = repo.replace("/", "%2F")
            url = f"https://gitlab.com/api/v4/projects/{encoded_repo}/pipelines/{build_id}/jobs"
            data = self._lazy_get(url)
            if isinstance(data, dict) and "error" in data:
                return data["error"]
            if isinstance(data, list):
                log_lines: List[str] = []
                for job in data:
                    log_lines.append(
                        f"--- {job.get('name', 'unknown')} "
                        f"({job.get('status', '')}) ---"
                    )
                return "\n".join(log_lines)
            return "No logs available"
        return f"Unsupported provider: {provider.value}"
