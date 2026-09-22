from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Mode(str, Enum):
    IDLE = "IDLE"
    LEARN = "LEARN"
    WRITE = "WRITE"

class RuntimeErrorState(RuntimeError):
    pass

@dataclass
class RuntimeEngine:
    mode: Mode = Mode.IDLE
    pinned_snapshot_id: int | None = None

    def enter_learn(self) -> None:
        if self.mode != Mode.IDLE:
            raise RuntimeErrorState(f"Cannot enter LEARN from {self.mode}")
        self.mode = Mode.LEARN
        self.pinned_snapshot_id = None

    def enter_write(self, snapshot_id: int) -> None:
        if self.mode != Mode.IDLE:
            raise RuntimeErrorState(f"Cannot enter WRITE from {self.mode}")
        if not snapshot_id:
            raise RuntimeErrorState("WRITE requires a published Xuehai snapshot")
        self.mode = Mode.WRITE
        self.pinned_snapshot_id = int(snapshot_id)

    def exit(self) -> None:
        self.mode = Mode.IDLE
        self.pinned_snapshot_id = None

    def require(self, expected: Mode) -> None:
        if self.mode != expected:
            raise RuntimeErrorState(f"Operation requires {expected}, current={self.mode}")
