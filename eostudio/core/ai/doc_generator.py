from __future__ import annotations

import os

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class DocGenerator:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(LLMConfig())

    def _ask(self, prompt: str) -> str:
        return self.llm_client.complete(prompt)

    def generate_readme(self, project_path: str) -> str:
        files: list[str] = []
        for root, _dirs, filenames in os.walk(project_path):
            for fname in filenames:
                if fname.endswith((".py", ".md", ".toml", ".cfg")):
                    files.append(os.path.join(root, fname))
        context_parts: list[str] = []
        for fpath in files[:20]:
            try:
                with open(fpath, "r") as f:
                    content = f.read(2000)
                context_parts.append(f"--- {fpath} ---\n{content}")
            except OSError:
                continue
        context = "\n\n".join(context_parts)
        prompt = (
            f"Generate a comprehensive README.md for this project.\n\n{context}"
        )
        return self._ask(prompt)

    def generate_api_docs(self, code: str, filename: str) -> str:
        prompt = (
            f"Generate API documentation for the following code "
            f"from {filename}:\n\n{code}"
        )
        return self._ask(prompt)

    def generate_architecture_diagram(self, project_path: str) -> str:
        files: list[str] = []
        for root, _dirs, filenames in os.walk(project_path):
            for fname in filenames:
                if fname.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, fname), project_path)
                    files.append(rel)
        file_list = "\n".join(files[:50])
        prompt = (
            f"Generate a Mermaid architecture diagram for a project with "
            f"these files:\n{file_list}"
        )
        return self._ask(prompt)

    def generate_changelog(self, git_log: str) -> str:
        prompt = (
            f"Generate a changelog from the following git log:\n\n{git_log}"
        )
        return self._ask(prompt)

    def generate_migration_guide(self, old_code: str, new_code: str) -> str:
        prompt = (
            f"Generate a migration guide for the following code change.\n\n"
            f"Old code:\n{old_code}\n\nNew code:\n{new_code}"
        )
        return self._ask(prompt)