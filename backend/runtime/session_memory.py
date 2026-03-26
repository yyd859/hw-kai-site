from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: str
    history: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(
        default_factory=lambda: {
            "project_brief": "",
            "requirements": [],
            "constraints": [],
            "selected_module_ids": [],
            "selected_board_id": "esp32_devkit_v1",
            "last_search": [],
            "last_inspected": {},
            "last_build_check": None,
            "ready_to_build": False,
        }
    )
    turn: int = 0


_sessions: dict[str, SessionState] = {}


def get_session(session_id: str) -> SessionState:
    if session_id not in _sessions:
        _sessions[session_id] = SessionState(session_id=session_id)
    return _sessions[session_id]


def append_history(session: SessionState, role: str, content: Any) -> None:
    session.history.append({"role": role, "content": content})
    session.history[:] = session.history[-24:]


def merge_memory(session: SessionState, patch: dict[str, Any] | None) -> None:
    if not patch:
        return

    for key, value in patch.items():
        if value is None:
            continue
        if key in {"requirements", "constraints", "selected_module_ids", "last_search"} and isinstance(value, list):
            session.memory[key] = value
        elif key == "last_inspected" and isinstance(value, dict):
            session.memory[key] = value
        else:
            session.memory[key] = value
