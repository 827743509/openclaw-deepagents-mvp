from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool

from openclaw_da.config import get_settings


def _calendar_file() -> Path:
    settings = get_settings()
    path = settings.openclaw_workspace / "calendar"
    path.mkdir(parents=True, exist_ok=True)
    return path / "events.jsonl"


@tool
def list_calendar_events(limit: int = 20) -> str:
    """List local calendar events from the MVP JSONL store."""
    file_path = _calendar_file()
    if not file_path.exists():
        return "No calendar events found."

    lines = file_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines[-limit:]]
    if not events:
        return "No calendar events found."

    return "\n".join(
        f"- {e['start']} to {e['end']} | {e['title']} | {e.get('location', '')}"
        for e in events
    )


@tool
def create_calendar_event(title: str, start: str, end: str, location: str = "", notes: str = "") -> str:
    """Create a local calendar event. Sensitive operation: should require human approval before use.

    start/end should be ISO-like strings, for example: 2026-05-07 10:00.
    """
    event = {
        "title": title,
        "start": start,
        "end": end,
        "location": location,
        "notes": notes,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    file_path = _calendar_file()
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return f"Calendar event created locally: {title} ({start} - {end})"
