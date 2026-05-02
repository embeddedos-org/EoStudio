from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserPresence:
    user_id: str
    display_name: str
    color: str
    cursor_line: int = 0
    cursor_col: int = 0
    selection_start: tuple[int, int] = (0, 0)
    selection_end: tuple[int, int] = (0, 0)
    file: str = ""
    online: bool = True
    last_active: str = ""


class PresenceManager:
    def __init__(self) -> None:
        self._users: dict[str, UserPresence] = {}

    def track_user(self, presence: UserPresence) -> None:
        presence.last_active = datetime.now(timezone.utc).isoformat()
        self._users[presence.user_id] = presence

    def remove_user(self, user_id: str) -> None:
        self._users.pop(user_id, None)

    def get_user(self, user_id: str) -> UserPresence | None:
        return self._users.get(user_id)

    def get_users(self) -> list[UserPresence]:
        return list(self._users.values())

    def update_cursor(self, user_id: str, line: int, col: int) -> None:
        user = self._users.get(user_id)
        if user:
            user.cursor_line = line
            user.cursor_col = col
            user.last_active = datetime.now(timezone.utc).isoformat()

    def update_selection(
        self, user_id: str, start: tuple[int, int], end: tuple[int, int]
    ) -> None:
        user = self._users.get(user_id)
        if user:
            user.selection_start = start
            user.selection_end = end
            user.last_active = datetime.now(timezone.utc).isoformat()

    def get_all_presence(self) -> list[UserPresence]:
        return [u for u in self._users.values() if u.online]