"""
Flashcards & Spaced Repetition Study Engine for Students.
"""

import json
import os
import random
from pathlib import Path
from typing import Any

NAME = "Flashcards & Spaced Repetition"
DESCRIPTION = "Create, review, and quiz yourself on study flashcards with spaced repetition tracking."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "🗂️"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Create flashcard Mitosis : Cell division resulting in two identical daughter cells",
    "Review flashcards",
    "Quiz me on flashcards",
    "List my flashcards",
]

DATA_DIR = Path.home() / "Documents" / "VedaAI" / "Flashcards"
DATA_FILE = DATA_DIR / "deck.json"


def _load_cards() -> list:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    # Default initial set for students
    initial = [
        {"front": "Photosynthesis", "back": "Process by which plants convert light energy into chemical energy (glucose).", "level": 1},
        {"front": "Newton's Second Law", "back": "Force equals mass times acceleration (F = m*a).", "level": 1},
        {"front": "Mitochondria", "back": "The powerhouse of the cell; produces ATP through cellular respiration.", "level": 1},
        {"front": "Ohm's Law", "back": "Voltage equals current multiplied by resistance (V = I*R).", "level": 1},
    ]
    _save_cards(initial)
    return initial


def _save_cards(cards: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cards, f, indent=2)
    except Exception as e:
        print(f"[Flashcards] Error saving deck: {e}")


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("flashcard", "flashcards", "study cards", "study card")):
        return False

    cards = _load_cards()

    # 1. Create or Add Flashcard
    if any(lower.startswith(p) for p in ("create flashcard", "add flashcard", "new flashcard", "make flashcard")):
        raw = text
        for p in ("create flashcard", "add flashcard", "new flashcard", "make flashcard"):
            if lower.startswith(p):
                raw = text[len(p):].strip()
                break
        
        sep = ":" if ":" in raw else ("-" if "-" in raw else "/")
        if sep in raw:
            parts = raw.split(sep, 1)
            front = parts[0].strip()
            back = parts[1].strip()
            cards.append({"front": front, "back": back, "level": 1})
            _save_cards(cards)
            msg = f"Created flashcard for '{front}'. You now have {len(cards)} cards in your study deck."
        else:
            msg = "To add a flashcard, say: Create flashcard [Concept] : [Definition]."

        if veda_echo:
            veda_echo.ui.write_log(f"🗂️ Flashcards: {msg}")
            veda_echo.speak(msg)
        return True

    # 2. List flashcards
    if "list" in lower or "show" in lower or "count" in lower or "how many" in lower:
        msg = f"You have {len(cards)} flashcards in your active deck:\n"
        for i, c in enumerate(cards[:5], 1):
            msg += f"{i}. {c['front']} -> {c['back'][:60]}...\n"
        if len(cards) > 5:
            msg += f"... and {len(cards) - 5} more."
        if veda_echo:
            veda_echo.ui.write_log(f"🗂️ Flashcards Deck ({len(cards)} total):\n{msg}")
            veda_echo.speak(f"You have {len(cards)} flashcards in your study deck.")
        return True

    # 3. Quiz / Review
    if any(k in lower for k in ("quiz", "review", "test", "study", "practice")):
        if not cards:
            msg = "Your flashcard deck is currently empty. Say 'Create flashcard concept : definition' to add one."
            if veda_echo:
                veda_echo.speak(msg)
            return True
        card = random.choice(cards)
        msg = f"Here is your flashcard quiz: What is {card['front']}?"
        answer_reveal = f"Definition: {card['back']}"
        if veda_echo:
            veda_echo.ui.write_log(f"🗂️ Quiz Card: {card['front']}")
            veda_echo.ui.write_log(f"💡 Answer: {card['back']}")
            veda_echo.speak(msg)
        return True

    return False
