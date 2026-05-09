from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

from openclaw_da.config import get_settings


def _reminder_file() -> Path:
    settings = get_settings()
    path = settings.openclaw_workspace / "reminders"
    path.mkdir(parents=True, exist_ok=True)
    return path / "reminders.jsonl"


@tool
def add_reminder(when: str, text: str) -> str:
    """Add a local reminder. when should be a human-readable or ISO-like time."""
    reminder = {
        "when": when,
        "text": text,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "done": False,
    }
    file_path = _reminder_file()
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(reminder, ensure_ascii=False) + "\n")
    return f"Reminder saved: {when} - {text}"


@tool
def list_reminders(limit: int = 20) -> str:
    """List local reminders from the MVP JSONL store."""
    file_path = _reminder_file()
    if not file_path.exists():
        return "No reminders found."

    lines = file_path.read_text(encoding="utf-8").splitlines()
    reminders = [json.loads(line) for line in lines[-limit:]]
    if not reminders:
        return "No reminders found."

    return "\n".join(
        f"- {r['when']} | {r['text']} | done={r['done']}"
        for r in reminders
    )
