"""
actions/routines.py
Custom Voice Routines & System Macros for Veda AI / Veda Echo.
Executes multi-step desktop presets with a single voice command.
"""

import sys
import time
import json
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from actions.open_app import open_app
from actions.computer_control import _focus_window

BASE_DIR = Path(__file__).resolve().parent.parent
ROUTINES_PATH = BASE_DIR / "config" / "routines.json"

DEFAULT_ROUTINES = {
    "study_mode": {
        "name": "Study Mode",
        "description": "Opens browser to academic resources, launches Notepad for study notes, and sets a focus environment.",
        "steps": [
            {"action": "open", "target": "https://scholar.google.com"},
            {"action": "open", "target": "Notepad"},
            {"action": "type", "target": "Notepad", "text": "=== VEDA AI STUDY NOTES ===\nDate: Today\nTopic:\n\n1. Key Concepts:\n- \n\n2. Summary:\n- \n\n"},
            {"action": "message", "text": "Study mode activated. Notes template is open and Google Scholar is ready, Rohan."}
        ]
    },
    "coding_session": {
        "name": "Coding Session",
        "description": "Launches VS Code, opens Terminal/Command Prompt, and navigates to GitHub.",
        "steps": [
            {"action": "open", "target": "vscode"},
            {"action": "open", "target": "terminal"},
            {"action": "open", "target": "https://github.com"},
            {"action": "message", "text": "Coding environment ready. VS Code, Terminal, and GitHub are launched, Rohan."}
        ]
    },
    "deep_work": {
        "name": "Deep Work",
        "description": "Minimizes clutter, starts Spotify focus music, and creates a distraction-free environment.",
        "steps": [
            {"action": "hotkey", "keys": "win+d"},
            {"action": "open", "target": "Notepad"},
            {"action": "message", "text": "Deep work mode initiated. Distractions cleared, focus document ready."}
        ]
    },
    "meeting_setup": {
        "name": "Meeting Setup",
        "description": "Prepares meeting notes in Notepad and opens calendar.",
        "steps": [
            {"action": "open", "target": "Notepad"},
            {"action": "type", "target": "Notepad", "text": "=== MEETING NOTES ===\nAttendees:\nAgenda:\n- \n\nAction Items:\n- \n\n"},
            {"action": "message", "text": "Meeting setup complete. Notes outline prepared."}
        ]
    },
    "relax_mode": {
        "name": "Relax Mode",
        "description": "Opens YouTube for relaxing lofi / ambient music.",
        "steps": [
            {"action": "open", "target": "https://www.youtube.com/results?search_query=relaxing+lofi+beats"},
            {"action": "message", "text": "Relax mode activated. Enjoy your break, Rohan."}
        ]
    }
}


def _load_routines() -> dict:
    try:
        if ROUTINES_PATH.exists():
            return json.loads(ROUTINES_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    # Initialize default
    _save_routines(DEFAULT_ROUTINES)
    return DEFAULT_ROUTINES


def _save_routines(data: dict) -> None:
    try:
        ROUTINES_PATH.parent.mkdir(parents=True, exist_ok=True)
        ROUTINES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Routines] Save error: {e}")


def execute_routine(routine_key: str, player: Any = None, speak: Optional[Callable[[str], None]] = None) -> str:
    routines = _load_routines()
    r_key = routine_key.lower().replace(" ", "_").strip()

    # Find matching routine
    target_routine = None
    if r_key in routines:
        target_routine = routines[r_key]
    else:
        for k, v in routines.items():
            if k in r_key or r_key in k or v.get("name", "").lower() in routine_key.lower():
                target_routine = v
                break

    if not target_routine:
        available = ", ".join([v.get("name", k) for k, v in routines.items()])
        return f"Routine '{routine_key}' not found. Available routines: {available}."

    routine_name = target_routine.get("name", routine_key)
    steps = target_routine.get("steps", [])

    if player and hasattr(player, "write_log"):
        player.write_log(f"Veda AI: Activating {routine_name}...")
    if speak:
        speak(f"Activating {routine_name} for you, Rohan.")

    final_msg = f"{routine_name} activated successfully."

    for s in steps:
        act = s.get("action")
        target = s.get("target")

        if act == "open" and target:
            open_app({"app_name": target}, player=player)
            time.sleep(1.0)

        elif act == "type":
            from actions.computer_control import computer_control
            time.sleep(0.5)
            computer_control({"action": "type", "text": s.get("text", ""), "app": target}, player=player)

        elif act == "hotkey":
            import pyautogui
            keys = s.get("keys", "").split("+")
            pyautogui.hotkey(*keys)
            time.sleep(0.5)

        elif act == "message":
            final_msg = s.get("text", final_msg)

    if player and hasattr(player, "write_log"):
        player.write_log(f"Veda AI: {final_msg}")
    if speak:
        speak(final_msg)

    return final_msg


def list_routines() -> str:
    routines = _load_routines()
    lines = ["Available Routines:"]
    for k, v in routines.items():
        lines.append(f"• {v.get('name', k)}: {v.get('description', '')}")
    return "\n".join(lines)


def routines_action(parameters: Optional[Dict[str, Any]] = None, player: Any = None, speak: Optional[Callable[[str], None]] = None) -> str:
    p = parameters or {}
    action = p.get("action", "run").lower().strip()
    name = p.get("name") or p.get("routine") or ""

    if action in ("list", "show"):
        return list_routines()
    elif action in ("run", "execute", "start", "activate"):
        return execute_routine(name or "study_mode", player=player, speak=speak)

    return execute_routine(action if action not in ("run", "execute") else name, player=player, speak=speak)
