"""
Academic Citation & Bibliography Generator for Students.
"""

from datetime import datetime
from typing import Any

NAME = "Academic Citation & Bibliography Generator"
DESCRIPTION = "Generates formatted citations in APA 7, MLA 9, IEEE, Chicago, and Harvard standards."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "📝"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "APA citation for Deep Learning by Goodfellow 2016",
    "MLA citation for Hamlet by William Shakespeare",
    "IEEE citation for Attention Is All You Need",
]


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("citation", "cite ", "bibliography", "apa style", "mla style", "ieee style")):
        return False

    style = "APA 7"
    if "mla" in lower:
        style = "MLA 9"
    elif "ieee" in lower:
        style = "IEEE"
    elif "chicago" in lower:
        style = "Chicago"
    elif "harvard" in lower:
        style = "Harvard"

    # Extract target
    target = text
    for p in ("apa citation for", "mla citation for", "ieee citation for", "citation for", "cite this", "cite"):
        if lower.startswith(p):
            target = text[len(p):].strip(" :,-")
            break

    if not target:
        target = "Academic Source"

    year = str(datetime.now().year)
    for y in range(1950, 2030):
        if str(y) in target:
            year = str(y)
            break

    author = "Author, A. A."
    if " by " in target.lower():
        parts = target.lower().split(" by ", 1)
        title_part = target[:len(parts[0])].strip()
        author_part = target[len(parts[0]) + 4:].strip()
        author = author_part.title()
        title = title_part.title()
    else:
        title = target.title()

    if style == "APA 7":
        citation = f"{author} ({year}). *{title}*. Academic Press."
    elif style == "MLA 9":
        citation = f'{author}. "{title}." *Academic Publication*, {year}.'
    elif style == "IEEE":
        citation = f'[1] {author}, "{title}," in *IEEE Transactions*, {year}.'
    elif style == "Chicago":
        citation = f'{author}. "{title}." ({year}).'
    else:
        citation = f"{author}, {year}. {title}. Academic Press."

    msg = f"Generated {style} Citation:\n{citation}"
    if veda_echo:
        veda_echo.ui.write_log(f"📝 {msg}")
        veda_echo.speak(f"Generated {style} citation for {title}.")
    return True
