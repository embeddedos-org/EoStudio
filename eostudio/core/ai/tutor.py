"""Kids tutor — interactive learning assistant (stub)."""

from __future__ import annotations

from typing import Optional


class KidsTutor:
    def __init__(self, lesson: Optional[str] = None, difficulty: Optional[str] = None) -> None:
        self.lesson = lesson or "intro"
        self.difficulty = difficulty or "easy"

    def start_interactive(self) -> str:
        return (
            f"Welcome to EoStudio Tutor!\n"
            f"Lesson: {self.lesson} | Difficulty: {self.difficulty}\n"
            f"(Interactive mode is not yet implemented.)"
        )
