from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Comment:
    id: str
    author: str
    text: str
    timestamp: str
    resolved: bool = False
    replies: list[Comment] = field(default_factory=list)


@dataclass
class CommentThread:
    id: str
    file: str
    line_start: int
    line_end: int
    comments: list[Comment] = field(default_factory=list)
    status: str = "open"


class CommentManager:
    def __init__(self) -> None:
        self._threads: dict[str, CommentThread] = {}

    def create_thread(
        self, file: str, line_start: int, line_end: int, author: str, text: str
    ) -> CommentThread:
        comment = Comment(
            id=str(uuid.uuid4()),
            author=author,
            text=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        thread = CommentThread(
            id=str(uuid.uuid4()),
            file=file,
            line_start=line_start,
            line_end=line_end,
            comments=[comment],
        )
        self._threads[thread.id] = thread
        return thread

    def add_comment(self, thread_id: str, author: str, text: str) -> Comment:
        thread = self._threads[thread_id]
        comment = Comment(
            id=str(uuid.uuid4()),
            author=author,
            text=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        thread.comments.append(comment)
        return comment

    def resolve_thread(self, thread_id: str) -> None:
        thread = self._threads.get(thread_id)
        if thread:
            thread.status = "resolved"

    def reopen_thread(self, thread_id: str) -> None:
        thread = self._threads.get(thread_id)
        if thread:
            thread.status = "open"

    def get_threads(self) -> list[CommentThread]:
        return list(self._threads.values())

    def get_threads_for_file(self, file: str) -> list[CommentThread]:
        return [t for t in self._threads.values() if t.file == file]

    def delete_comment(self, thread_id: str, comment_id: str) -> None:
        thread = self._threads.get(thread_id)
        if thread:
            thread.comments = [c for c in thread.comments if c.id != comment_id]