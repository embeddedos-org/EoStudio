from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str = ""
    attachments: list[str] = field(default_factory=list)


@dataclass
class ChatSession:
    id: str
    messages: list[ChatMessage] = field(default_factory=list)
    system_prompt: str = ""
    model: str = ""
    created: str = ""


class ChatPanel:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(LLMConfig())
        self._sessions: dict[str, ChatSession] = {}
        self._active_session_id: str = ""
        self.new_session()

    def _get_active(self) -> ChatSession:
        return self._sessions[self._active_session_id]

    def send_message(self, content: str, attachments: list[str] | None = None) -> str:
        session = self._get_active()
        user_msg = ChatMessage(
            role="user",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            attachments=attachments or [],
        )
        session.messages.append(user_msg)
        prompt = "\n".join(
            f"{m.role}: {m.content}" for m in session.messages
        )
        if session.system_prompt:
            prompt = f"System: {session.system_prompt}\n{prompt}"
        response = self.llm_client.complete(prompt)
        assistant_msg = ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.messages.append(assistant_msg)
        return response

    def get_history(self) -> list[ChatMessage]:
        return list(self._get_active().messages)

    def set_system_prompt(self, prompt: str) -> None:
        self._get_active().system_prompt = prompt

    def attach_file(self, path: str) -> str:
        with open(path, "r") as f:
            content = f.read()
        return f"File: {path}\n{content}"

    def attach_folder(self, path: str) -> str:
        entries = os.listdir(path)
        return f"Folder: {path}\n" + "\n".join(entries)

    def clear(self) -> None:
        self._get_active().messages.clear()

    def search_history(self, query: str) -> list[ChatMessage]:
        query_lower = query.lower()
        return [
            m for m in self._get_active().messages
            if query_lower in m.content.lower()
        ]

    def new_session(self, system_prompt: str | None = None) -> str:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            id=session_id,
            system_prompt=system_prompt or "",
            created=datetime.now(timezone.utc).isoformat(),
        )
        self._sessions[session_id] = session
        self._active_session_id = session_id
        return session_id