# Veda AI Plugin System Guide

Welcome to the **Veda AI Plugin Architecture**! Plugins allow you to extend Veda AI with custom skills, custom triggers, external APIs, study/work coaches, automation scripts, and event listeners.

---

## 🚀 How to Use Existing Plugins

1. All active plugins reside inside the `plugins/` directory.
2. Veda automatically loads all `.py` files in `plugins/` on startup.
3. You can enable or disable plugins individually in `config/plugins_config.json`:
   ```json
   {
     "pomodoro_focus_plugin": true,
     "exam_prep_plugin": true,
     "quick_notes_plugin": true
   }
   ```
4. You can interact with any plugin by speaking or typing naturally in Veda AI. For example:
   - *"Start 25 minute pomodoro"*
   - *"Add flashcard Question: What is photosynthesis? Answer: Process plants use to make food"*
   - *"Solve 2x + 5 = 15"*
   - *"Summarize this textbook text"*

---

## 🛠️ How to Create Your Own Custom Plugin

Creating a new plugin is as simple as dropping a single Python file into the `plugins/` folder (e.g. `plugins/my_custom_plugin.py`).

### Minimal Plugin Template

```python
"""
My Custom Plugin for Veda AI
"""

from typing import Any

# Plugin Metadata
NAME = "Weather & Outfit Advisor"
DESCRIPTION = "Provides real-time local weather tips and outfit suggestions."
VERSION = "1.0.0"
AUTHOR = "Rohan"
ICON = "🌤️"
CATEGORY = "Lifestyle / Utilities"
SAMPLE_PROMPTS = [
    "What should I wear today?",
    "Check outfit recommendation",
    "Weather advice"
]


def on_veda_created(veda_ai: Any):
    """Called once when Veda AI starts up."""
    print(f"[{NAME}] Initialized successfully!")


def on_text_command(text: str, source: str = "local", veda_ai: Any = None, **kwargs) -> bool:
    """
    Called whenever a user types or speaks a command.
    Return True if this plugin handled the request (stops further processing).
    Return False to let Veda AI handle it normally.
    """
    lower = text.lower().strip()

    if any(k in lower for k in ("what should i wear", "outfit recommendation", "clothing suggestion")):
        response = "It's sunny and 24°C outside! A light cotton shirt and sunglasses would be perfect today."
        
        # Log to Veda UI
        if veda_ai and hasattr(veda_ai, "ui"):
            veda_ai.ui.write_log(f"🌤️ {NAME}: {response}")
            
        # Speak back via Veda voice
        if veda_ai and hasattr(veda_ai, "speak"):
            veda_ai.speak(response)

        return True  # Handled!

    return False  # Let Veda handle
```

---

## ⚡ Plugin Lifecycle Hooks

| Hook Function | When It Runs | Arguments | Return Value |
| :--- | :--- | :--- | :--- |
| `on_veda_created(veda_ai)` | When Veda AI engine is initialized | `veda_ai` instance | None |
| `on_startup(veda_ai)` | Immediately after all plugins load | `veda_ai` instance | None |
| `on_text_command(text, source, veda_ai)` | When user types or speaks | `text`, `source`, `veda_ai` | `True` if handled, `False` otherwise |

---

## 💡 Accessing Veda AI Services in Plugins

Inside `veda_ai`, you have full access to:
- `veda_ai.speak("Text to speak")` - Speaks out loud using Veda's natural voice synthesizer.
- `veda_ai.ui.write_log("Message")` - Displays a message in the desktop UI console log.
- `veda_ai.ui.begin_task_workspace(title, steps)` - Starts a visual stage workspace card on the screen.
- `veda_ai.ui.update_task_workspace(status, output, percent)` - Updates task progress visually.
