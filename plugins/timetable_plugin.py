"""
Course Schedule & Timetable Organizer for Students.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

NAME = "Course Schedule & Timetable"
DESCRIPTION = "Manages weekly lecture timetables, classroom numbers, and alerts for upcoming classes."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "🗓️"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "What class do I have next?",
    "Show my class schedule",
    "Timetable for today",
    "Add class Algorithms Monday at 10:00 AM Room 402",
]

DATA_DIR = Path.home() / "Documents" / "VedaAI" / "Timetable"
DATA_FILE = DATA_DIR / "schedule.json"

DEFAULT_SCHEDULE = {
    "Monday": [
        {"time": "09:00 AM", "subject": "Data Structures & Algorithms", "room": "Hall B-12", "prof": "Dr. Sharma"},
        {"time": "11:30 AM", "subject": "Computer Architecture", "room": "Lab 3", "prof": "Prof. Rao"},
        {"time": "02:00 PM", "subject": "Discrete Mathematics", "room": "Hall A-04", "prof": "Dr. Miller"},
    ],
    "Tuesday": [
        {"time": "10:00 AM", "subject": "Database Management Systems", "room": "Hall C-08", "prof": "Dr. Evans"},
        {"time": "01:30 PM", "subject": "Operating Systems Lab", "room": "CS Lab 1", "prof": "Prof. Lin"},
    ],
    "Wednesday": [
        {"time": "09:00 AM", "subject": "Data Structures & Algorithms", "room": "Hall B-12", "prof": "Dr. Sharma"},
        {"time": "03:00 PM", "subject": "Technical Communication", "room": "Hall D-01", "prof": "Prof. Adams"},
    ],
    "Thursday": [
        {"time": "11:00 AM", "subject": "Probability & Statistics", "room": "Hall A-02", "prof": "Dr. Gupta"},
        {"time": "02:00 PM", "subject": "Database Lab", "room": "Lab 2", "prof": "Dr. Evans"},
    ],
    "Friday": [
        {"time": "10:00 AM", "subject": "Artificial Intelligence", "room": "Auditorium", "prof": "Dr. Patel"},
        {"time": "01:00 PM", "subject": "Project Seminar", "room": "Seminar Room 1", "prof": "Dept Chair"},
    ],
}


def _load_schedule() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_SCHEDULE
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SCHEDULE, f, indent=2)
    except Exception:
        pass
    return DEFAULT_SCHEDULE


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("timetable", "class schedule", "schedule for today", "next class", "what class do i have")):
        return False

    schedule = _load_schedule()
    today_name = datetime.now().strftime("%A")

    # 1. Next class or today's classes
    if any(k in lower for k in ("next class", "what class do i have next", "upcoming class")):
        today_classes = schedule.get(today_name, [])
        if not today_classes:
            msg = f"You have no scheduled classes for today ({today_name}). Enjoy your free day!"
        else:
            first = today_classes[0]
            msg = f"Your next class today is {first['subject']} at {first['time']} in {first['room']} ({first['prof']})."
        if veda_echo:
            veda_echo.ui.write_log(f"🗓️ Timetable: {msg}")
            veda_echo.speak(msg)
        return True

    # 2. Today's full schedule
    if any(k in lower for k in ("today", "schedule for today", "classes today")):
        classes = schedule.get(today_name, [])
        if not classes:
            msg = f"No classes scheduled for {today_name}."
        else:
            msg = f"📅 Today's Schedule ({today_name}):\n"
            for c in classes:
                msg += f"• {c['time']} — {c['subject']} (Room: {c['room']}, {c['prof']})\n"
        if veda_echo:
            veda_echo.ui.write_log(f"🗓️ {msg}")
            veda_echo.speak(f"You have {len(classes)} classes scheduled for today, Rohan.")
        return True

    # 3. Full weekly schedule
    msg = "📚 Weekly Class Timetable:\n"
    for day, items in schedule.items():
        msg += f"\n**{day}**:\n"
        for it in items:
            msg += f"  - {it['time']}: {it['subject']} ({it['room']})\n"

    if veda_echo:
        veda_echo.ui.write_log(f"🗓️ {msg}")
        veda_echo.speak("Here is your full weekly academic timetable.")
    return True
