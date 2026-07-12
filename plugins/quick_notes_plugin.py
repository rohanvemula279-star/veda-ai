"""
Quick Notes & Lecture Mindmapper for Students.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

NAME = "Quick Notes & Lecture Mindmapper"
DESCRIPTION = "Captures timestamped lecture notes, categorizes by course, and generates visual Markdown mindmaps."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "📓"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Take note CS301: Prof mentioned Dijkstra algorithm will be on the midterm",
    "Lecture note Physics: Resonance occurs when driving frequency matches natural frequency",
    "Create mindmap for Machine Learning",
    "Show my notes",
]

NOTES_DIR = Path.home() / "Documents" / "VedaAI" / "Notes"


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("take note", "lecture note", "create mindmap", "show notes", "show my notes", "read my notes")):
        return False

    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Show notes
    if any(k in lower for k in ("show notes", "show my notes", "read my notes", "list notes")):
        files = list(NOTES_DIR.glob("*.md"))
        if not files:
            msg = "You have no saved lecture notes yet. Say 'Take note [subject]: [content]' to create one."
        else:
            msg = f"You have {len(files)} note notebooks:\n"
            for f in files[:6]:
                msg += f"- {f.stem.replace('_', ' ').title()}\n"
        if veda_echo:
            veda_echo.ui.write_log(f"📓 Notes Archive:\n{msg}")
            veda_echo.speak(f"You have {len(files)} student notebooks in your Notes directory.")
        return True

    # 2. Mindmap generator
    if "create mindmap" in lower or "make mindmap" in lower:
        topic = text
        for p in ("create mindmap for", "create mindmap on", "make mindmap for"):
            if lower.startswith(p):
                topic = text[len(p):].strip(" :,-")
                break
        if not topic:
            topic = "General Subject"

        mindmap_file = NOTES_DIR / f"{topic.replace(' ', '_')}_mindmap.md"
        content = f"""# Visual Mindmap: {topic.title()}
```mermaid
mindmap
  root(({topic.title()}))
    Foundations
      Core Theorems
      Historical Context
      Key Formulas
    Methodologies
      Primary Approach
      Alternative Algorithmic Techniques
    Applications
      Industrial Systems
      Modern Software
    Evaluation
      Metrics
      Benchmarks
```
"""
        with open(mindmap_file, "w", encoding="utf-8") as f:
            f.write(content)

        msg = f"Generated visual mindmap for '{topic}'. Saved to {mindmap_file.name}."
        if veda_echo:
            veda_echo.ui.write_log(f"📓 Mindmap:\n{content}")
            veda_echo.speak(msg)
        return True

    # 3. Take Note
    raw = text
    for p in ("take note", "lecture note", "add note"):
        if lower.startswith(p):
            raw = text[len(p):].strip(" :,-")
            break

    subject = "General"
    note_body = raw
    if ":" in raw:
        parts = raw.split(":", 1)
        subject = parts[0].strip().replace(" ", "_")
        note_body = parts[1].strip()

    note_path = NOTES_DIR / f"{subject}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n- **[{timestamp}]**: {note_body}\n"

    try:
        with open(note_path, "a", encoding="utf-8") as f:
            f.write(entry)
        msg = f"Saved note under {subject.title()}: \"{note_body[:80]}...\""
    except Exception as e:
        msg = f"Failed to record note: {e}"

    if veda_echo:
        veda_echo.ui.write_log(f"📓 Quick Note: {msg}")
        veda_echo.speak(f"Note saved under {subject.title()}, Rohan.")
    return True
