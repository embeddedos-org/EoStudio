"""Spec Engine — AI-powered spec generation: prompt → requirements → design → tech → tasks.

Multi-pass refinement: generate → validate → refine → finalize.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig
from eostudio.core.specs.requirement import Requirement, RequirementType, RequirementPriority
from eostudio.core.specs.design_spec import DesignSpec
from eostudio.core.specs.tech_spec import TechSpec
from eostudio.core.specs.task_breakdown import TaskBreakdown, Task


# ---------------------------------------------------------------------------
# Spec templates for common project types
# ---------------------------------------------------------------------------

SPEC_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "saas": {
        "required_sections": ["Authentication", "Dashboard", "Billing", "Settings", "API"],
        "default_requirements": [
            "User signup/login with email + OAuth",
            "Role-based access control (admin, member, viewer)",
            "Subscription billing with Stripe",
            "Team/org management",
            "Usage analytics dashboard",
            "REST API with rate limiting",
        ],
        "tech_defaults": {
            "frontend": ["React", "TypeScript", "Tailwind CSS"],
            "backend": ["FastAPI", "SQLAlchemy", "Alembic"],
            "database": ["PostgreSQL", "Redis"],
            "infra": ["Docker", "Vercel"],
        },
    },
    "ecommerce": {
        "required_sections": ["Product Catalog", "Cart", "Checkout", "Orders", "Admin"],
        "default_requirements": [
            "Product listing with search and filters",
            "Shopping cart with persistent state",
            "Checkout with Stripe/PayPal",
            "Order tracking and history",
            "Admin product management",
            "Inventory tracking",
        ],
        "tech_defaults": {
            "frontend": ["Next.js", "TypeScript", "Tailwind CSS"],
            "backend": ["Node.js", "Express", "Prisma"],
            "database": ["PostgreSQL", "Redis"],
            "infra": ["Docker", "Vercel"],
        },
    },
    "mobile_app": {
        "required_sections": ["Onboarding", "Core Features", "Profile", "Notifications", "Offline"],
        "default_requirements": [
            "User onboarding flow",
            "Push notifications",
            "Offline data sync",
            "Profile management",
            "Deep linking",
            "App analytics",
        ],
        "tech_defaults": {
            "frontend": ["React Native", "TypeScript", "NativeWind"],
            "backend": ["FastAPI", "SQLAlchemy"],
            "database": ["PostgreSQL", "SQLite (local)"],
            "infra": ["Docker", "AWS"],
        },
    },
    "api": {
        "required_sections": ["Endpoints", "Authentication", "Rate Limiting", "Documentation", "Monitoring"],
        "default_requirements": [
            "RESTful API design with OpenAPI spec",
            "JWT/OAuth2 authentication",
            "Rate limiting and throttling",
            "Request validation and error handling",
            "Auto-generated API documentation",
            "Health check and monitoring endpoints",
        ],
        "tech_defaults": {
            "frontend": [],
            "backend": ["FastAPI", "Python 3.10+", "Pydantic"],
            "database": ["PostgreSQL", "Redis"],
            "infra": ["Docker", "AWS Lambda"],
        },
    },
}


@dataclass
class SpecValidationResult:
    """Result of spec validation with gaps identified."""
    is_valid: bool = True
    missing_acceptance_criteria: List[str] = field(default_factory=list)
    requirements_without_tasks: List[str] = field(default_factory=list)
    components_without_tests: List[str] = field(default_factory=list)
    invest_violations: List[str] = field(default_factory=list)
    missing_sections: List[str] = field(default_factory=list)
    score: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid, "score": self.score,
            "missing_acceptance_criteria": self.missing_acceptance_criteria,
            "requirements_without_tasks": self.requirements_without_tasks,
            "components_without_tests": self.components_without_tests,
            "invest_violations": self.invest_violations,
            "missing_sections": self.missing_sections,
        }

    @property
    def gap_summary(self) -> str:
        gaps = []
        if self.missing_acceptance_criteria:
            gaps.append(f"{len(self.missing_acceptance_criteria)} requirements missing acceptance criteria")
        if self.requirements_without_tasks:
            gaps.append(f"{len(self.requirements_without_tasks)} requirements have no mapped tasks")
        if self.components_without_tests:
            gaps.append(f"{len(self.components_without_tests)} components have no test tasks")
        if self.invest_violations:
            gaps.append(f"{len(self.invest_violations)} INVEST violations")
        if self.missing_sections:
            gaps.append(f"{len(self.missing_sections)} missing design sections")
        return "; ".join(gaps) if gaps else "No gaps found"


class SpecEngine:
    """Kiro-style spec-driven development: prompt → requirements → design → tech → tasks.

    Supports multi-pass refinement: generate → validate → refine → finalize.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 max_refinement_passes: int = 2) -> None:
        self._client = llm_client or LLMClient(LLMConfig())
        self.max_refinement_passes = max_refinement_passes

    def generate_full_spec(self, prompt: str, framework: str = "react",
                           project_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate complete spec pipeline with multi-pass refinement.

        Pipeline: generate → validate → refine → finalize.
        """
        template = SPEC_TEMPLATES.get(project_type) if project_type else None

        # Pass 1: Generate
        requirements = self.generate_requirements(prompt, template=template)
        design = self.generate_design_spec(prompt, requirements, template=template)
        tech = self.generate_tech_spec(design, framework, template=template)
        tasks = self.generate_task_breakdown(tech, requirements)

        spec_data = {
            "requirements": [r.to_dict() for r in requirements],
            "design_spec": design.to_dict(),
            "tech_spec": tech.to_dict(),
            "task_breakdown": tasks.to_dict(),
        }

        # Pass 2+: Validate → Refine loop
        for _ in range(self.max_refinement_passes):
            validation = self.validate_spec(spec_data)
            if validation.is_valid and validation.score >= 90.0:
                break
            spec_data = self.refine_spec(spec_data, validation)

        spec_data["validation"] = self.validate_spec(spec_data).to_dict()
        return spec_data

    def generate_requirements(self, prompt: str,
                              template: Optional[Dict[str, Any]] = None) -> List[Requirement]:
        """Generate requirements/user stories from a project description."""
        template_hint = ""
        if template:
            defaults = template.get("default_requirements", [])
            if defaults:
                template_hint = (
                    f"\n\nCommon requirements for this type of project "
                    f"(include these if relevant):\n"
                    + "\n".join(f"- {r}" for r in defaults)
                )

        messages = [{"role": "user", "content": (
            f"Generate requirements as JSON array for this project:\n{prompt}\n\n"
            f"Each requirement: {{id, title, description, type (functional/user_story), "
            f"priority (must/should/could), acceptance_criteria: [{{description, test_method}}], "
            f"estimated_effort (S/M/L/XL)}}\n\n"
            f"IMPORTANT: Every requirement MUST have at least 2 acceptance criteria "
            f"with concrete, testable conditions.{template_hint}"
        )}]
        raw = self._client.chat(messages)
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [Requirement.from_dict(r) for r in data]
        except (json.JSONDecodeError, TypeError):
            pass
        return self._fallback_requirements(prompt)

    def generate_design_spec(self, prompt: str, requirements: List[Requirement],
                             template: Optional[Dict[str, Any]] = None) -> DesignSpec:
        """Generate design spec from requirements."""
        req_summary = "\n".join(f"- {r.title}" for r in requirements)
        section_hint = ""
        if template:
            sections = template.get("required_sections", [])
            if sections:
                section_hint = (
                    f"\n\nRequired design sections (include all of these):\n"
                    + "\n".join(f"- {s}" for s in sections)
                )
        messages = [{"role": "user", "content": (
            f"Generate a design spec as JSON for:\n{prompt}\n\nRequirements:\n{req_summary}\n\n"
            f"Return: {{project_name, overview, goals:[], non_goals:[], target_users:[], "
            f"sections:[{{title, content}}], open_questions:[], risks:[{{risk, mitigation}}]}}{section_hint}"
        )}]
        raw = self._client.chat(messages)
        try:
            data = json.loads(raw)
            if "project_name" in data:
                return DesignSpec.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            pass
        return self._fallback_design_spec(prompt)

    def generate_tech_spec(self, design: DesignSpec, framework: str = "react",
                           template: Optional[Dict[str, Any]] = None) -> TechSpec:
        """Generate tech spec from design spec."""
        messages = [{"role": "user", "content": (
            f"Generate a tech spec as JSON for: {design.project_name}\n"
            f"Overview: {design.overview}\nFramework: {framework}\n\n"
            f"Return: {{project_name, architecture_overview, "
            f"tech_stack:{{frontend:[], backend:[], database:[], infra:[]}}, "
            f"components:[{{name, description, tech_stack:[], responsibilities:[], "
            f"file_structure:[]}}], "
            f"security:[], performance_targets:{{}}, testing_strategy:{{}}, "
            f"deployment:{{}}}}"
        )}]
        raw = self._client.chat(messages)
        try:
            data = json.loads(raw)
            if "project_name" in data:
                return TechSpec.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            pass
        return self._fallback_tech_spec(design, framework)

    def generate_task_breakdown(self, tech: TechSpec, requirements: List[Requirement]) -> TaskBreakdown:
        """Generate implementation tasks from tech spec."""
        tb = TaskBreakdown(project_name=tech.project_name)

        for comp in tech.components:
            # Create tasks for each file
            for f in comp.file_structure:
                task = tb.add_task(
                    title=f"Implement {f}",
                    component=comp.name,
                    files_to_create=[f],
                    effort="M",
                )
            # Add test task
            tb.add_task(
                title=f"Write tests for {comp.name}",
                component=comp.name,
                tests_needed=[f"test_{comp.name.lower().replace(' ', '_')}.py"],
                effort="M",
            )

        # Add integration and deployment tasks
        tb.add_task(title="Integration testing", component="Testing", effort="L")
        tb.add_task(title="CI/CD pipeline setup", component="DevOps", effort="M")
        tb.add_task(title="Documentation", component="Docs", effort="M")
        tb.add_task(title="Deploy to production", component="DevOps", effort="S")

        return tb

    def validate_spec(self, spec_data: Dict[str, Any]) -> SpecValidationResult:
        """Validate spec completeness — check that all pieces connect."""
        result = SpecValidationResult()
        penalty = 0.0

        # 1. All requirements must have acceptance criteria
        for r in spec_data.get("requirements", []):
            criteria = r.get("acceptance_criteria", [])
            if len(criteria) < 1:
                result.missing_acceptance_criteria.append(r.get("title", r.get("id", "?")))
                penalty += 5.0

        # 2. INVEST validation on user stories
        for r in spec_data.get("requirements", []):
            violations = self._validate_invest(r)
            result.invest_violations.extend(violations)
            penalty += len(violations) * 2.0

        # 3. Tech spec components should have test tasks
        tasks = spec_data.get("task_breakdown", {}).get("tasks", [])
        task_components = {t.get("component", "") for t in tasks if "test" in t.get("title", "").lower()}
        for comp in spec_data.get("tech_spec", {}).get("components", []):
            comp_name = comp.get("name", "")
            if comp_name and comp_name not in task_components:
                result.components_without_tests.append(comp_name)
                penalty += 3.0

        # 4. Requirements should map to tasks via component
        task_titles_lower = " ".join(t.get("title", "").lower() for t in tasks)
        for r in spec_data.get("requirements", []):
            title_words = r.get("title", "").lower().split()
            if not any(w in task_titles_lower for w in title_words if len(w) > 3):
                result.requirements_without_tasks.append(r.get("title", "?"))
                penalty += 4.0

        # 5. Design spec should have key sections
        sections = [s.get("title", "").lower()
                    for s in spec_data.get("design_spec", {}).get("sections", [])]
        for expected in ["architecture", "data model", "user flow"]:
            if not any(expected in s for s in sections):
                result.missing_sections.append(expected)
                penalty += 3.0

        result.score = max(0.0, 100.0 - penalty)
        result.is_valid = result.score >= 70.0
        return result

    def refine_spec(self, spec_data: Dict[str, Any],
                    validation: SpecValidationResult) -> Dict[str, Any]:
        """Ask AI to fill gaps identified by validation."""
        gap_text = validation.gap_summary
        if not gap_text or gap_text == "No gaps found":
            return spec_data

        messages = [{"role": "user", "content": (
            f"The following spec has validation gaps:\n{gap_text}\n\n"
            f"Current spec (abbreviated):\n"
            f"Requirements: {json.dumps(spec_data.get('requirements', [])[:5], indent=1)[:1500]}\n"
            f"Design sections: {json.dumps([s.get('title') for s in spec_data.get('design_spec', {}).get('sections', [])])}\n\n"
            f"Fix the gaps:\n"
            f"1. Add missing acceptance criteria (at least 2 per requirement)\n"
            f"2. Add missing design sections\n"
            f"3. Ensure user stories follow INVEST (Independent, Negotiable, Valuable, Estimable, Small, Testable)\n\n"
            f"Return JSON with keys: requirements (array), extra_sections (array of {{title, content}})"
        )}]

        raw = self._client.chat(messages)
        try:
            fixes = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return spec_data

        # Merge refined requirements
        if isinstance(fixes.get("requirements"), list):
            existing_ids = {r.get("id") for r in spec_data.get("requirements", [])}
            for new_req in fixes["requirements"]:
                if new_req.get("id") in existing_ids:
                    # Update existing
                    for i, old_req in enumerate(spec_data["requirements"]):
                        if old_req.get("id") == new_req.get("id"):
                            spec_data["requirements"][i] = {**old_req, **new_req}
                            break
                else:
                    spec_data.setdefault("requirements", []).append(new_req)

        # Merge extra design sections
        if isinstance(fixes.get("extra_sections"), list):
            existing_titles = {s.get("title", "").lower()
                             for s in spec_data.get("design_spec", {}).get("sections", [])}
            for section in fixes["extra_sections"]:
                if section.get("title", "").lower() not in existing_titles:
                    spec_data.setdefault("design_spec", {}).setdefault("sections", []).append(section)

        return spec_data

    @staticmethod
    def _validate_invest(requirement: Dict[str, Any]) -> List[str]:
        """Validate a requirement against INVEST criteria for user stories."""
        violations = []
        title = requirement.get("title", "")
        desc = requirement.get("description", "")
        req_type = requirement.get("type", "")

        # Only validate user stories
        if req_type not in ("user_story", "functional"):
            return violations

        # Valuable: must describe user value, not just technical implementation
        tech_only_words = ["refactor", "migrate", "upgrade", "rename", "cleanup"]
        if any(w in desc.lower() for w in tech_only_words) and "user" not in desc.lower():
            violations.append(f"'{title}' may lack user value (INVEST: Valuable)")

        # Estimable: must have effort estimate
        if not requirement.get("estimated_effort"):
            violations.append(f"'{title}' missing effort estimate (INVEST: Estimable)")

        # Small: XL effort may be too large to be a single story
        if requirement.get("estimated_effort") == "XL":
            violations.append(f"'{title}' is XL — consider splitting (INVEST: Small)")

        # Testable: must have acceptance criteria
        criteria = requirement.get("acceptance_criteria", [])
        if len(criteria) < 1:
            violations.append(f"'{title}' has no acceptance criteria (INVEST: Testable)")

        return violations

    def export_markdown(self, spec_data: Dict[str, Any]) -> str:
        """Export the full spec as a single markdown document."""
        lines = []
        if "requirements" in spec_data:
            lines.append("# Requirements\n")
            for r in spec_data["requirements"]:
                req = Requirement.from_dict(r)
                lines.append(req.to_markdown())
                lines.append("")

        if "design_spec" in spec_data:
            ds = DesignSpec.from_dict(spec_data["design_spec"])
            lines.append(ds.to_markdown())
            lines.append("")

        if "tech_spec" in spec_data:
            ts = TechSpec.from_dict(spec_data["tech_spec"])
            lines.append(ts.to_markdown())
            lines.append("")

        if "task_breakdown" in spec_data:
            tb = TaskBreakdown.from_dict(spec_data["task_breakdown"])
            lines.append(tb.to_markdown())

        return "\n".join(lines)

    # Fallbacks
    def _fallback_requirements(self, prompt: str) -> List[Requirement]:
        words = prompt.split()
        name = " ".join(words[:3]) if len(words) >= 3 else prompt
        reqs = [
            Requirement(id="REQ-001", title=f"Core {name} functionality",
                       description=f"Implement the main features described: {prompt}",
                       req_type=RequirementType.FUNCTIONAL, priority=RequirementPriority.MUST,
                       estimated_effort="L"),
            Requirement(id="REQ-002", title="User authentication",
                       description="User login, signup, and session management",
                       req_type=RequirementType.FUNCTIONAL, priority=RequirementPriority.MUST,
                       estimated_effort="M"),
            Requirement(id="REQ-003", title="Responsive UI",
                       description="Mobile-first responsive design",
                       req_type=RequirementType.NON_FUNCTIONAL, priority=RequirementPriority.SHOULD,
                       estimated_effort="M"),
            Requirement(id="REQ-004", title="API endpoints",
                       description="REST API for all CRUD operations",
                       req_type=RequirementType.FUNCTIONAL, priority=RequirementPriority.MUST,
                       estimated_effort="L"),
        ]
        for r in reqs:
            r.add_criteria(f"{r.title} works as expected", "integration")
            r.add_criteria(f"{r.title} has error handling", "unit")
        return reqs

    def _fallback_design_spec(self, prompt: str) -> DesignSpec:
        spec = DesignSpec(project_name=prompt[:30], overview=prompt)
        spec.goals = ["Deliver a production-ready application", "Clean, maintainable code"]
        spec.non_goals = ["Native mobile app (web-first)", "Offline support"]
        spec.add_section("Architecture", "Client-server architecture with React frontend and REST API backend.")
        spec.add_section("User Flows", "1. Landing → Signup → Dashboard\n2. Login → Dashboard → Features")
        spec.add_section("Data Model", "Core entities derived from requirements.")
        return spec

    def _fallback_tech_spec(self, design: DesignSpec, framework: str) -> TechSpec:
        spec = TechSpec(project_name=design.project_name,
                       architecture_overview="Modern web application with component-based frontend and REST API backend.")
        spec.tech_stack = {
            "frontend": [framework, "TypeScript", "Tailwind CSS", "Framer Motion"],
            "backend": ["FastAPI", "Python 3.10+", "SQLAlchemy"],
            "database": ["PostgreSQL", "Redis"],
            "infra": ["Docker", "Vercel/Netlify"],
        }
        frontend = spec.add_component("Frontend", description="React SPA with routing and state management",
                                       tech_stack=[framework, "TypeScript"],
                                       responsibilities=["UI rendering", "Client-side routing", "API calls"],
                                       file_structure=["src/App.tsx", "src/pages/", "src/components/", "src/hooks/"])
        backend = spec.add_component("Backend", description="REST API server",
                                      tech_stack=["FastAPI", "Python"],
                                      responsibilities=["Business logic", "Authentication", "Database access"],
                                      file_structure=["api/main.py", "api/routes/", "api/models/", "api/services/"])
        spec.security = ["JWT authentication", "CORS configuration", "Input validation", "SQL injection prevention"]
        spec.testing_strategy = {"unit": "pytest + jest", "integration": "API tests", "e2e": "Playwright"}
        spec.deployment = {"platform": "Docker + Vercel", "ci": "GitHub Actions"}
        return spec
