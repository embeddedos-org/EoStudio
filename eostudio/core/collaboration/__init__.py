"""Collaboration subpackage — real-time editing, presence, comments."""

from __future__ import annotations

from eostudio.core.collaboration.crdt import CRDTDocument, CRDTOperation
from eostudio.core.collaboration.collab_server import CollabServer, CollabSession
from eostudio.core.collaboration.presence import PresenceManager, UserPresence
from eostudio.core.collaboration.comments import CommentThread, Comment

__all__ = [
    "CRDTDocument", "CRDTOperation",
    "CollabServer", "CollabSession",
    "PresenceManager", "UserPresence",
    "CommentThread", "Comment",
]