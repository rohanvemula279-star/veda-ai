"""
actions/form_filler.py
Smart Desktop Form Filler & UI Clicker for Veda AI / Veda Echo.
Fills forms in active applications or web pages using stored user profile
or realistic test/synthetic data.
"""

import sys
import time
import json
import random
import string
from pathlib import Path
from typing import Optional, Dict, Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import pyautogui
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

from actions.computer_control import _focus_window

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_PATH = BASE_DIR / "memory" / "long_term.json"

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper", "Rohan"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Kumar", "Sharma"
]
DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "proton.me"]


def _get_user_profile() -> dict:
    profile = {
        "name": "Rohan",
        "first_name": "Rohan",
        "last_name": "Kumar",
        "email": "rohan@example.com",
        "phone": "+91 9876543210",
        "city": "Hyderabad",
        "country": "India",
        "state": "Telangana",
        "zip_code": "500074",
        "address": "123 Tech Park, Hyderabad",
    }
    try:
        if MEMORY_PATH.exists():
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            for k, v in identity.items():
                if isinstance(v, dict) and "value" in v:
                    profile[k.lower()] = v["value"]
                elif isinstance(v, str):
                    profile[k.lower()] = v
    except Exception as e:
        print(f"[FormFiller] Profile read exception: {e}")
    return profile


def _generate_synthetic_data() -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    num = random.randint(10, 999)
    domain = random.choice(DOMAINS)
    email = f"{first.lower()}.{last.lower()}{num}@{domain}"
    phone = f"+1{random.randint(200,999)}{random.randint(1000000,9999999)}"
    street_num = random.randint(100, 9999)
    street = random.choice(["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Broadway"])
    address = f"{street_num} {street}"
    city = random.choice(["New York", "San Francisco", "Austin", "Seattle", "Chicago"])
    zip_code = str(random.randint(10000, 99999))
    pwd = "".join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=12))

    return {
        "name": f"{first} {last}",
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "country": "United States",
        "zip_code": zip_code,
        "password": pwd,
    }


def _type_field(text: str) -> None:
    if not _PYAUTOGUI:
        return
    # Clear field first
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("backspace")
    time.sleep(0.05)
    # Paste for fast and 100% accurate entry
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.03)
    time.sleep(0.1)


def fill_form_fields(fields: list[str], values_dict: dict, advance_key: str = "tab") -> str:
    """
    Sequentially types each value and presses advance_key (usually 'tab').
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed."

    filled = []
    time.sleep(0.5)
    for idx, field in enumerate(fields):
        val = str(values_dict.get(field.lower(), ""))
        if not val:
            continue
        _type_field(val)
        filled.append(f"{field}: {val[:20]}")
        if idx < len(fields) - 1:
            pyautogui.press(advance_key)
            time.sleep(0.15)

    return f"Filled {len(filled)} fields: " + ", ".join(filled)


def auto_fill_form(mode: str = "profile", app_name: Optional[str] = None) -> str:
    """
    Fills standard registration/contact form fields (Name, Email, Phone, Address, City, Zip).
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed."

    if app_name:
        _focus_window(app_name)
        time.sleep(0.4)

    values = _get_user_profile() if mode == "profile" else _generate_synthetic_data()
    standard_fields = ["name", "email", "phone", "address", "city", "zip_code"]

    time.sleep(0.4)
    filled_count = 0
    for idx, field in enumerate(standard_fields):
        val = values.get(field, "")
        if val:
            _type_field(val)
            filled_count += 1
        if idx < len(standard_fields) - 1:
            pyautogui.press("tab")
            time.sleep(0.15)

    return f"Form filled ({mode} mode): {filled_count} fields entered."


def click_button(label: str, app_name: Optional[str] = None) -> str:
    """
    Attempts to click a button by label or common submit actions.
    """
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed."

    if app_name:
        _focus_window(app_name)
        time.sleep(0.3)

    label_lower = label.lower().strip()
    if label_lower in ("submit", "enter", "done", "save", "ok"):
        pyautogui.press("enter")
        return f"Pressed Enter to submit/confirm '{label}'."

    # Use screen find via computer_control if available
    try:
        from actions.computer_control import _screen_find, _click
        coords = _screen_find(f"{label} button")
        if coords:
            _click(coords[0], coords[1])
            return f"Clicked '{label}' button at {coords}."
    except Exception:
        pass

    pyautogui.press("enter")
    return f"Confirmed '{label}'."


def form_filler(parameters: Optional[Dict[str, Any]] = None, player: Any = None) -> str:
    p = parameters or {}
    action = p.get("action", "fill").lower().strip()
    mode = p.get("mode", "profile").lower().strip()
    app = p.get("app") or p.get("window")

    if player and hasattr(player, "write_log"):
        player.write_log(f"[FormFiller] {action} ({mode})")

    if action in ("fill", "fill_form", "auto_fill"):
        fields = p.get("fields")
        if fields and isinstance(fields, list):
            data_source = _get_user_profile() if mode == "profile" else _generate_synthetic_data()
            return fill_form_fields(fields, data_source)
        return auto_fill_form(mode=mode, app_name=app)

    elif action in ("click", "click_button", "press_button"):
        label = p.get("label") or p.get("button", "Submit")
        return click_button(label, app_name=app)

    elif action == "get_data":
        return json.dumps(_get_user_profile() if mode == "profile" else _generate_synthetic_data(), indent=2)

    return f"Unknown form_filler action: '{action}'."
