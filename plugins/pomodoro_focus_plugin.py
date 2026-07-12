"""
Pomodoro & Deep Work Focus Coach for Students.
"""

import threading
import time
from datetime import datetime
from typing import Any

NAME = "Pomodoro & Deep Work Coach"
DESCRIPTION = "Manages 25/5 and 50/10 focus intervals, tracks study time, and announces session checkpoints."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "⏱️"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Start 25 minute pomodoro",
    "Start 50 minute study session",
    "Pomodoro status",
    "Stop pomodoro timer",
]

_ACTIVE_TIMER = None
_TIMER_END = 0
_SESSION_MINUTES = 25
_LOCK = threading.Lock()


def _timer_worker(duration_min: int, veda_echo: Any):
    global _ACTIVE_TIMER, _TIMER_END
    time.sleep(duration_min * 60)
    with _LOCK:
        if _ACTIVE_TIMER is None:
            return
        _ACTIVE_TIMER = None
        _TIMER_END = 0

    msg = f"Ding! Your {duration_min}-minute study session is complete. Time for a 5-minute rejuvenating break!"
    if veda_echo:
        veda_echo.ui.write_log(f"⏱️ Pomodoro Finished: {msg}")
        veda_echo.speak(msg)


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    global _ACTIVE_TIMER, _TIMER_END, _SESSION_MINUTES
    lower = text.lower().strip()
    if not any(k in lower for k in ("pomodoro", "study timer", "focus session", "deep work")):
        return False

    # 1. Stop / Cancel
    if any(k in lower for k in ("stop", "cancel", "end", "pause")):
        with _LOCK:
            _ACTIVE_TIMER = None
            _TIMER_END = 0
        msg = "Pomodoro study timer has been stopped."
        if veda_echo:
            veda_echo.ui.write_log(f"⏱️ Pomodoro: {msg}")
            veda_echo.speak(msg)
        return True

    # 2. Status
    if any(k in lower for k in ("status", "how much time", "remaining", "check")):
        if _TIMER_END > time.time():
            rem = int((_TIMER_END - time.time()) / 60)
            msg = f"You have approximately {max(1, rem)} minutes remaining in your current study block."
        else:
            msg = "No active Pomodoro study timer is running. Say 'Start 25 minute pomodoro' to begin."
        if veda_echo:
            veda_echo.ui.write_log(f"⏱️ Pomodoro: {msg}")
            veda_echo.speak(msg)
        return True

    # 3. Start timer
    mins = 25
    if "50" in lower:
        mins = 50
    elif "15" in lower:
        mins = 15
    elif "30" in lower:
        mins = 30
    elif "45" in lower:
        mins = 45

    with _LOCK:
        _SESSION_MINUTES = mins
        _TIMER_END = time.time() + (mins * 60)
        t = threading.Thread(target=_timer_worker, args=(mins, veda_echo), daemon=True)
        _ACTIVE_TIMER = t
        t.start()

    msg = f"Started {mins}-minute deep focus study timer. Silence all distractions and focus. I'll notify you when it's time for a break!"
    if veda_echo:
        veda_echo.ui.write_log(f"⏱️ Pomodoro: {msg}")
        veda_echo.speak(f"Started {mins} minute focus session, Rohan. Happy studying!")
    return True
