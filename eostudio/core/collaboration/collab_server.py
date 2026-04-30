from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from eostudio.core.collaboration.crdt import CRDTOperation


@dataclass
class CollabSession:
    id: str
    document_id: str
    participants: list[str] = field(default_factory=list)
    created: str = ""
    owner: str = ""


class CollabServer:
    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._sessions: dict[str, CollabSession] = {}
        self._running: bool = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def create_session(self, doc_id: str, owner: str) -> CollabSession:
        session = CollabSession(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            participants=[owner],
            created=datetime.now(timezone.utc).isoformat(),
            owner=owner,
        )
        self._sessions[session.id] = session
        return session

    def join_session(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if user_id not in session.participants:
            session.participants.append(user_id)
        return True

    def leave_session(self, session_id: str, user_id: str) -> None:
        session = self._sessions.get(session_id)
        if session and user_id in session.participants:
            session.participants.remove(user_id)

    def broadcast_operation(
        self, session_id: str, op: CRDTOperation
    ) -> None:
        _session = self._sessions.get(session_id)
        # In a real implementation this would broadcast to all participants

    def get_sessions(self) -> list[CollabSession]:
        return list(self._sessions.values())

    def generate_share_link(self, session_id: str) -> str:
        return f"eostudio://collab/{session_id}"