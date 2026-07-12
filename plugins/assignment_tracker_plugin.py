"""
Assignment & Deadline Tracker for Students.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

NAME = "Assignment & Deadline Tracker"
DESCRIPTION = "Organize homework, project milestones, and exam dates with urgency alerts."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "📅"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Add assignment Physics Lab Report due Friday",
    "List my assignments",
    "What assignments are due this week?",
    "Complete assignment Physics Lab Report",
]

DATA_DIR = Path.home() / "Documents" / "VedaAI" / "Assignments"
DATA_FILE = DATA_DIR / "assignments.json"


def _load_assignments() -> list:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    initial = [
        {"title": "Computer Networks Project", "course": "CS301", "due": "Friday", "completed": False},
        {"title": "Calculus Problem Set 4", "course": "MATH201", "due": "Tomorrow", "completed": False},
    ]
    _save_assignments(initial)
    return initial


def _save_assignments(items: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        print(f"[AssignmentTracker] Error saving: {e}")


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("assignment", "assignments", "homework", "due date", "deadline")):
        return False

    items = _load_assignments()

    # 1. Add assignment
    if any(lower.startswith(p) for p in ("add assignment", "new assignment", "create assignment", "add homework")):
        raw = text
        for p in ("add assignment", "new assignment", "create assignment", "add homework"):
            if lower.startswith(p):
                raw = text[len(p):].strip()
                break

        title = raw
        due = "Soon"
        course = "General"

        if " due " in raw.lower():
            p_split = raw.lower().split(" due ", 1)
            title = raw[:len(p_split[0])].strip()
            due = raw[len(p_split[0]) + 5:].strip()

        if " for " in title.lower():
            c_split = title.lower().split(" for ", 1)
            course = title[len(c_split[0]) + 5:].strip()
            title = title[:len(c_split[0])].strip()

        items.append({
            "title": title,
            "course": course,
            "due": due,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "completed": False,
        })
        _save_assignments(items)
        msg = f"Added assignment '{title}' for {course}, due {due}."
        if veda_echo:
            veda_echo.ui.write_log(f"📅 Tracker: {msg}")
            veda_echo.speak(msg)
        return True

    # 2. Complete assignment
    if any(lower.startswith(p) for p in ("complete assignment", "finish assignment", "done assignment", "remove assignment")):
        raw = text
        for p in ("complete assignment", "finish assignment", "done assignment", "remove assignment"):
            if lower.startswith(p):
                raw = text[len(p):].strip().lower()
                break
        found = False
        for it in items:
            if raw in it["title"].lower() and not it.get("completed"):
                it["completed"] = True
                found = True
                msg = f"Great job! Marked '{it['title']}' as completed."
                break
        if not found:
            msg = f"Couldn't find an active assignment matching '{raw}'."
        else:
            _save_assignments(items)
        if veda_echo:
            veda_echo.ui.write_log(f"📅 Tracker: {msg}")
            veda_echo.speak(msg)
        return True

    # 3. List / check deadlines
    active = [it for it in items if not it.get("completed")]
    msg = f"You have {len(active)} pending assignments:\n"
    if not active:
        msg = "You have no pending assignments! Everything is up to date."
    else:
        for i, a in enumerate(active, 1):
            msg += f"{i}. [{a.get('course', 'Course')}] {a['title']} - Due: {a.get('due', 'Soon')}\n"
    if veda_echo:
        veda_echo.ui.write_log(f"📅 Assignments:\n{msg}")
        speak_msg = f"You have {len(active)} pending assignments. Next up is {active[0]['title']} due {active[0].get('due', 'soon')}." if active else msg
        veda_echo.speak(speak_msg)
    return True
