from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class OperationType(Enum):
    INSERT = auto()
    DELETE = auto()
    RETAIN = auto()


@dataclass
class CRDTOperation:
    type: OperationType
    position: int
    content: str = ""
    length: int = 0
    author: str = ""
    timestamp: float = 0.0
    vector_clock: dict[str, int] = field(default_factory=dict)


class CRDTDocument:
    def __init__(self, doc_id: str) -> None:
        self.doc_id = doc_id
        self._text: list[str] = []
        self._history: list[CRDTOperation] = []
        self._vector_clock: dict[str, int] = {}

    def insert(self, position: int, text: str, author: str) -> CRDTOperation:
        self._vector_clock[author] = self._vector_clock.get(author, 0) + 1
        op = CRDTOperation(
            type=OperationType.INSERT,
            position=position,
            content=text,
            length=len(text),
            author=author,
            timestamp=time.time(),
            vector_clock=dict(self._vector_clock),
        )
        self.apply(op)
        return op

    def delete(self, position: int, length: int, author: str) -> CRDTOperation:
        self._vector_clock[author] = self._vector_clock.get(author, 0) + 1
        op = CRDTOperation(
            type=OperationType.DELETE,
            position=position,
            content="",
            length=length,
            author=author,
            timestamp=time.time(),
            vector_clock=dict(self._vector_clock),
        )
        self.apply(op)
        return op

    def apply(self, op: CRDTOperation) -> None:
        if op.type == OperationType.INSERT:
            chars = list(op.content)
            for i, ch in enumerate(chars):
                self._text.insert(op.position + i, ch)
        elif op.type == OperationType.DELETE:
            for _ in range(op.length):
                if op.position < len(self._text):
                    self._text.pop(op.position)
        self._history.append(op)

    def merge(self, remote_ops: list[CRDTOperation]) -> None:
        for remote_op in remote_ops:
            transformed = remote_op
            for local_op in self._history:
                transformed, _ = self.transform(transformed, local_op)
            self.apply(transformed)

    def get_text(self) -> str:
        return "".join(self._text)

    def get_history(self) -> list[CRDTOperation]:
        return list(self._history)

    def transform(
        self, op1: CRDTOperation, op2: CRDTOperation
    ) -> tuple[CRDTOperation, CRDTOperation]:
        new_op1 = CRDTOperation(
            type=op1.type,
            position=op1.position,
            content=op1.content,
            length=op1.length,
            author=op1.author,
            timestamp=op1.timestamp,
            vector_clock=dict(op1.vector_clock),
        )
        new_op2 = CRDTOperation(
            type=op2.type,
            position=op2.position,
            content=op2.content,
            length=op2.length,
            author=op2.author,
            timestamp=op2.timestamp,
            vector_clock=dict(op2.vector_clock),
        )
        if op1.type == OperationType.INSERT and op2.type == OperationType.INSERT:
            if op1.position <= op2.position:
                new_op2.position += op1.length
            else:
                new_op1.position += op2.length
        elif op1.type == OperationType.INSERT and op2.type == OperationType.DELETE:
            if op1.position <= op2.position:
                new_op2.position += op1.length
            elif op1.position >= op2.position + op2.length:
                new_op1.position -= op2.length
            else:
                new_op1.position = op2.position
        elif op1.type == OperationType.DELETE and op2.type == OperationType.INSERT:
            if op2.position <= op1.position:
                new_op1.position += op2.length
            elif op2.position >= op1.position + op1.length:
                new_op2.position -= op1.length
            else:
                new_op2.position = op1.position
        elif op1.type == OperationType.DELETE and op2.type == OperationType.DELETE:
            if op1.position >= op2.position + op2.length:
                new_op1.position -= op2.length
            elif op2.position >= op1.position + op1.length:
                new_op2.position -= op1.length
            elif op1.position <= op2.position:
                overlap = (
                    min(op1.position + op1.length, op2.position + op2.length)
                    - op2.position
                )
                new_op1.length -= overlap
                new_op2.position = op1.position
                new_op2.length -= overlap
            else:
                overlap = (
                    min(op2.position + op2.length, op1.position + op1.length)
                    - op1.position
                )
                new_op2.length -= overlap
                new_op1.position = op2.position
                new_op1.length -= overlap
        return new_op1, new_op2

    def snapshot(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "text": self.get_text(),
            "vector_clock": dict(self._vector_clock),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> CRDTDocument:
        doc = cls(data["doc_id"])
        doc._text = list(data["text"])
        doc._vector_clock = dict(data.get("vector_clock", {}))
        return doc