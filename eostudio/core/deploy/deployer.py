"""Deployer — generates deployment configs for Docker, Vercel, Netlify, GitHub Pages."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DeployTarget(Enum):
    DOCKER = "docker"
    VERCEL = "vercel"
    NETLIFY = "netlify"
    GITHUB_PAGES = "github_pages"
    FLY_IO = "fly_io"
    RAILWAY = "railway"


@dataclass
class DeployConfig:
    """Deployment configuration."""
    target: DeployTarget = DeployTarget.DOCKER
    project_name: str = "my-app"
    framework: str = "react"  # react, next, vue, fastapi
    node_version: str = "20"
    python_version: str = "3.10"
    port: int = 3000
    env_vars: Dict[str, str] = field(default_factory=dict)
    build_command: str = "npm run build"
    start_command: str = "npm start"
    output_dir: str = "dist"
    custom_domain: str = ""


@dataclass
class DeployResult:
    """Result of deployment config generation."""
    target: str
    files_generated: Dict[str, str] = field(default_factory=dict)
    commands: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"target": self.target, "files": list(self.files_generated.keys()),
                "commands": self.commands, "notes": self.notes}


class Deployer:
    """Generates deployment configurations, health checks, env validation, and CI/CD."""

    def deploy(self, config: DeployConfig) -> DeployResult:
        """Generate deployment files for the target platform."""
        generators = {
            DeployTarget.DOCKER: self._docker,
            DeployTarget.VERCEL: self._vercel,
            DeployTarget.NETLIFY: self._netlify,
            DeployTarget.GITHUB_PAGES: self._github_pages,
            DeployTarget.FLY_IO: self._fly_io,
            DeployTarget.RAILWAY: self._railway,
        }
        gen = generators.get(config.target)
        if gen:
            result = gen(config)
            # Add common production files
            result.files_generated.update(self._generate_health_check(config))
            result.files_generated.update(self._generate_env_example(config))
            result.files_generated.update(self._generate_monitoring(config))
            result.files_generated.update(self._generate_ci_cd(config))
            result.notes.extend(self._rollback_instructions(config))
            return result
        raise ValueError(f"Unknown target: {config.target}")

    def deploy_all(self, config: DeployConfig) -> Dict[str, DeployResult]:
        """Generate configs for all platforms."""
        results = {}
        for target in DeployTarget:
            cfg = DeployConfig(**{**config.__dict__, "target": target})
            results[target.value] = self.deploy(cfg)
        return results

    def write_files(self, result: DeployResult, output_dir: str) -> List[str]:
        """Write deployment files to disk."""
        written = []
        for filename, content in result.files_generated.items():
            path = os.path.join(output_dir, filename)
            os.makedirs(os.path.dirname(path) or output_dir, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            written.append(path)
        return written

    def _docker(self, config: DeployConfig) -> DeployResult:
        dockerfile = (
            f"# Build stage\n"
            f"FROM node:{config.node_version}-alpine AS build\n"
            f"WORKDIR /app\n"
            f"COPY package*.json ./\n"
            f"RUN npm ci\n"
            f"COPY . .\n"
            f"RUN {config.build_command}\n\n"
            f"# Production stage\n"
            f"FROM nginx:alpine\n"
            f"COPY --from=build /app/{config.output_dir} /usr/share/nginx/html\n"
            f"COPY nginx.conf /etc/nginx/conf.d/default.conf\n"
            f"EXPOSE {config.port}\n"
            f'CMD ["nginx", "-g", "daemon off;"]\n'
        )

        nginx_conf = (
            "server {\n"
            f"    listen {config.port};\n"
            "    server_name localhost;\n"
            "    root /usr/share/nginx/html;\n"
            "    index index.html;\n\n"
            "    location / {\n"
            "        try_files $uri $uri/ /index.html;\n"
            "    }\n\n"
            "    location /api {\n"
            "        proxy_pass http://backend:8000;\n"
            "    }\n"
            "}\n"
        )

        docker_compose = (
            "version: '3.8'\n"
            "services:\n"
            f"  {config.project_name}:\n"
            "    build: .\n"
            f"    ports:\n      - '{config.port}:{config.port}'\n"
            "    environment:\n"
            + "".join(f"      - {k}={v}\n" for k, v in config.env_vars.items())
            + "    restart: unless-stopped\n"
        )

        dockerignore = "node_modules\n.git\n.env\ndist\nbuild\n*.md\n"

        return DeployResult(
            target="docker",
            files_generated={
                "Dockerfile": dockerfile,
                "nginx.conf": nginx_conf,
                "docker-compose.yml": docker_compose,
                ".dockerignore": dockerignore,
            },
            commands=[
                f"docker build -t {config.project_name} .",
                f"docker run -p {config.port}:{config.port} {config.project_name}",
                "# Or with docker-compose:",
                "docker-compose up -d",
            ],
        )

    def _vercel(self, config: DeployConfig) -> DeployResult:
        vercel_json = json.dumps({
            "framework": "vite" if config.framework == "react" else config.framework,
            "buildCommand": config.build_command,
            "outputDirectory": config.output_dir,
            "rewrites": [{"source": "/(.*)", "destination": "/index.html"}],
        }, indent=2)

        return DeployResult(
            target="vercel",
            files_generated={"vercel.json": vercel_json},
            commands=[
                "npm i -g vercel",
                "vercel login",
                "vercel --prod",
            ],
            notes=["Vercel auto-detects Vite/React projects",
                   "Set env vars in Vercel dashboard"],
        )

    def _netlify(self, config: DeployConfig) -> DeployResult:
        netlify_toml = (
            "[build]\n"
            f'  command = "{config.build_command}"\n'
            f'  publish = "{config.output_dir}"\n\n'
            "[[redirects]]\n"
            '  from = "/*"\n'
            '  to = "/index.html"\n'
            "  status = 200\n"
        )

        return DeployResult(
            target="netlify",
            files_generated={"netlify.toml": netlify_toml},
            commands=[
                "npm i -g netlify-cli",
                "netlify login",
                "netlify deploy --prod",
            ],
        )

    def _github_pages(self, config: DeployConfig) -> DeployResult:
        workflow = (
            "name: Deploy to GitHub Pages\n"
            "on:\n  push:\n    branches: [main]\n\n"
            "permissions:\n  contents: read\n  pages: write\n  id-token: write\n\n"
            "jobs:\n"
            "  build-and-deploy:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            f"      - uses: actions/setup-node@v4\n        with:\n          node-version: '{config.node_version}'\n"
            "      - run: npm ci\n"
            f"      - run: {config.build_command}\n"
            "      - uses: actions/upload-pages-artifact@v3\n"
            f"        with:\n          path: ./{config.output_dir}\n"
            "      - uses: actions/deploy-pages@v4\n"
        )

        return DeployResult(
            target="github_pages",
            files_generated={".github/workflows/deploy.yml": workflow},
            commands=["git push origin main  # triggers auto-deploy"],
            notes=["Enable GitHub Pages in repo Settings → Pages → Source: GitHub Actions"],
        )

    def _fly_io(self, config: DeployConfig) -> DeployResult:
        fly_toml = (
            f'app = "{config.project_name}"\n'
            f'primary_region = "sjc"\n\n'
            "[build]\n"
            '  dockerfile = "Dockerfile"\n\n'
            "[http_service]\n"
            f"  internal_port = {config.port}\n"
            "  force_https = true\n"
            '  auto_stop_machines = "stop"\n'
            '  auto_start_machines = true\n'
        )

        return DeployResult(
            target="fly_io",
            files_generated={"fly.toml": fly_toml},
            commands=["flyctl launch", "flyctl deploy"],
        )

    def _railway(self, config: DeployConfig) -> DeployResult:
        railway_json = json.dumps({
            "build": {"builder": "NIXPACKS"},
            "deploy": {"startCommand": config.start_command},
        }, indent=2)

        return DeployResult(
            target="railway",
            files_generated={"railway.json": railway_json},
            commands=["railway login", "railway up"],
        )

    # ------------------------------------------------------------------
    # Production additions: health checks, env, monitoring, CI/CD
    # ------------------------------------------------------------------

    def _generate_health_check(self, config: DeployConfig) -> Dict[str, str]:
        """Generate health check endpoint files."""
        files: Dict[str, str] = {}

        if config.framework in ("fastapi", "flask", "express"):
            # Backend health check
            if config.framework == "fastapi":
                files["api/health.py"] = (
                    'from fastapi import APIRouter\n'
                    'from datetime import datetime\n\n'
                    'router = APIRouter()\n\n\n'
                    '@router.get("/healthz")\n'
                    'async def healthz():\n'
                    '    """Liveness probe — is the process running?"""\n'
                    '    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}\n\n\n'
                    '@router.get("/readyz")\n'
                    'async def readyz():\n'
                    '    """Readiness probe — can the service handle traffic?"""\n'
                    '    # TODO: add database/cache connectivity checks\n'
                    '    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}\n'
                )
            else:
                files["api/health.js"] = (
                    'const express = require("express");\n'
                    'const router = express.Router();\n\n'
                    'router.get("/healthz", (req, res) => {\n'
                    '  res.json({ status: "ok", timestamp: new Date().toISOString() });\n'
                    '});\n\n'
                    'router.get("/readyz", (req, res) => {\n'
                    '  // TODO: add database/cache connectivity checks\n'
                    '  res.json({ status: "ready", timestamp: new Date().toISOString() });\n'
                    '});\n\n'
                    'module.exports = router;\n'
                )
        else:
            # Frontend-only: add a static health page
            files["public/healthz.json"] = json.dumps(
                {"status": "ok", "version": "1.0.0"}, indent=2
            )

        return files

    def _generate_env_example(self, config: DeployConfig) -> Dict[str, str]:
        """Generate .env.example with documented variables."""
        lines = [
            "# ============================================",
            f"# Environment variables for {config.project_name}",
            "# Copy this file to .env and fill in values",
            "# ============================================",
            "",
            "# --- Application ---",
            f"PORT={config.port}",
            'NODE_ENV=development',
            "",
            "# --- Database ---",
            "DATABASE_URL=postgresql://user:password@localhost:5432/dbname",
            "REDIS_URL=redis://localhost:6379",
            "",
            "# --- Authentication ---",
            "JWT_SECRET=change-me-to-a-random-string",
            "JWT_EXPIRY=7d",
            "",
            "# --- External APIs ---",
            "# STRIPE_SECRET_KEY=sk_test_...",
            "# SENDGRID_API_KEY=SG...",
            "",
        ]
        # Add any project-specific env vars
        for key, value in config.env_vars.items():
            lines.append(f"{key}={value}")

        return {".env.example": "\n".join(lines) + "\n"}

    @staticmethod
    def validate_env(env_file: str = ".env",
                     example_file: str = ".env.example") -> Dict[str, Any]:
        """Check that all required env vars from .env.example are set."""
        required: List[str] = []
        missing: List[str] = []

        if os.path.exists(example_file):
            with open(example_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        required.append(key)

        # Check against actual env file or os.environ
        actual_keys: set = set()
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        actual_keys.add(key)

        for key in required:
            if key not in actual_keys and key not in os.environ:
                missing.append(key)

        return {
            "valid": len(missing) == 0,
            "required": required,
            "missing": missing,
            "message": f"{len(missing)} missing env vars" if missing else "All env vars set",
        }

    def _generate_monitoring(self, config: DeployConfig) -> Dict[str, str]:
        """Generate basic monitoring/metrics configuration."""
        files: Dict[str, str] = {}

        # Structured logging config
        if config.framework == "fastapi":
            files["api/logging_config.py"] = (
                'import logging\n'
                'import json\n'
                'from datetime import datetime\n\n\n'
                'class JSONFormatter(logging.Formatter):\n'
                '    """Structured JSON log formatter for production."""\n\n'
                '    def format(self, record: logging.LogRecord) -> str:\n'
                '        log_data = {\n'
                '            "timestamp": datetime.utcnow().isoformat(),\n'
                '            "level": record.levelname,\n'
                '            "message": record.getMessage(),\n'
                '            "module": record.module,\n'
                '            "function": record.funcName,\n'
                '        }\n'
                '        if record.exc_info:\n'
                '            log_data["exception"] = self.formatException(record.exc_info)\n'
                '        return json.dumps(log_data)\n\n\n'
                'def setup_logging(level: str = "INFO") -> None:\n'
                '    handler = logging.StreamHandler()\n'
                '    handler.setFormatter(JSONFormatter())\n'
                '    logging.root.handlers = [handler]\n'
                '    logging.root.setLevel(getattr(logging, level))\n'
            )

        # Prometheus metrics endpoint stub
        files["docs/monitoring.md"] = (
            f"# Monitoring — {config.project_name}\n\n"
            "## Health Checks\n"
            "- `GET /healthz` — liveness probe (is the process alive?)\n"
            "- `GET /readyz` — readiness probe (can it handle traffic?)\n\n"
            "## Metrics\n"
            "- Add `prom-client` (Node) or `prometheus-client` (Python) for `/metrics` endpoint\n"
            "- Key metrics: request latency, error rate, active connections, queue depth\n\n"
            "## Alerting\n"
            "- Set up alerts for: 5xx error rate > 1%, p99 latency > 2s, health check failures\n\n"
            "## Logging\n"
            "- Structured JSON logging enabled by default\n"
            "- Log levels: ERROR for failures, WARN for degraded, INFO for requests\n"
        )

        return files

    def _generate_ci_cd(self, config: DeployConfig) -> Dict[str, str]:
        """Generate GitHub Actions CI/CD workflow."""
        target = config.target.value
        deploy_step = {
            "docker": (
                "      - name: Build and push Docker image\n"
                "        run: |\n"
                f"          docker build -t ${{{{ secrets.REGISTRY }}}}/{config.project_name}:${{{{ github.sha }}}} .\n"
                f"          docker push ${{{{ secrets.REGISTRY }}}}/{config.project_name}:${{{{ github.sha }}}}\n"
            ),
            "vercel": (
                "      - name: Deploy to Vercel\n"
                "        run: npx vercel --prod --token=${{ secrets.VERCEL_TOKEN }}\n"
            ),
            "netlify": (
                "      - name: Deploy to Netlify\n"
                "        run: npx netlify deploy --prod --auth=${{ secrets.NETLIFY_TOKEN }}\n"
            ),
            "fly_io": (
                "      - name: Deploy to Fly.io\n"
                "        run: flyctl deploy --remote-only\n"
                "        env:\n"
                "          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}\n"
            ),
            "railway": (
                "      - name: Deploy to Railway\n"
                "        run: railway up\n"
                "        env:\n"
                "          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}\n"
            ),
        }

        workflow = (
            f"name: CI/CD — {config.project_name}\n"
            "on:\n"
            "  push:\n"
            "    branches: [main]\n"
            "  pull_request:\n"
            "    branches: [main]\n\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            f"      - uses: actions/setup-node@v4\n"
            f"        with:\n          node-version: '{config.node_version}'\n"
            "      - run: npm ci\n"
            "      - run: npm run lint\n"
            "      - run: npm test\n"
            f"      - run: {config.build_command}\n\n"
            "  deploy:\n"
            "    needs: test\n"
            "    if: github.ref == 'refs/heads/main' && github.event_name == 'push'\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            f"      - uses: actions/setup-node@v4\n"
            f"        with:\n          node-version: '{config.node_version}'\n"
            "      - run: npm ci\n"
            f"      - run: {config.build_command}\n"
            + deploy_step.get(target, "      - run: echo 'Deploy step not configured'\n")
        )

        return {".github/workflows/ci.yml": workflow}

    @staticmethod
    def _rollback_instructions(config: DeployConfig) -> List[str]:
        """Return platform-specific rollback instructions."""
        instructions = {
            DeployTarget.DOCKER: [
                "ROLLBACK: docker pull <registry>/<image>:<previous-tag> && docker-compose up -d",
            ],
            DeployTarget.VERCEL: [
                "ROLLBACK: vercel rollback  # reverts to previous deployment",
            ],
            DeployTarget.NETLIFY: [
                "ROLLBACK: Go to Netlify dashboard → Deploys → click previous deploy → Publish",
            ],
            DeployTarget.GITHUB_PAGES: [
                "ROLLBACK: git revert HEAD && git push  # reverts the last deploy commit",
            ],
            DeployTarget.FLY_IO: [
                "ROLLBACK: flyctl releases list && flyctl deploy --image <previous-image>",
            ],
            DeployTarget.RAILWAY: [
                "ROLLBACK: railway rollback  # reverts to previous deployment",
            ],
        }
        return instructions.get(config.target, ["ROLLBACK: redeploy previous version"])
