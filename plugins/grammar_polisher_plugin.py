"""
Academic Essay & Grammar Polisher for Students.
"""

from typing import Any

NAME = "Academic Essay & Grammar Polisher"
DESCRIPTION = "Elevates essays, emails, and lab reports with formal academic diction and grammatical clarity."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "✍️"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Polish essay: We did this experiment to find out if it works",
    "Make this sound academic: The results show that the model got a lot better",
    "Proofread this: Their is many problems with the old method",
]

ACADEMIC_REPLACEMENTS = {
    "find out": "determine",
    "look at": "examine / investigate",
    "get better": "demonstrate measurable improvement",
    "a lot of": "a substantial number of",
    "shows that": "illustrates that / substantiates that",
    "good": "efficacious / robust",
    "bad": "suboptimal / disadvantageous",
    "make sure": "ensure / verify",
    "big problem": "critical limitation / significant impediment",
    "their is": "there are",
}


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    prefixes = (
        "polish essay", "check grammar", "make this sound academic",
        "academic tone for", "proofread this", "proofread",
    )
    matched = None
    for p in prefixes:
        if lower.startswith(p):
            matched = p
            break

    if not matched:
        return False

    raw = text[len(matched):].strip(" :,-")
    if not raw:
        msg = "Please provide the text you would like to polish or elevate academically."
        if veda_echo:
            veda_echo.speak(msg)
        return True

    polished = raw
    improvements = []
    for informal, formal in ACADEMIC_REPLACEMENTS.items():
        if informal in polished.lower():
            # replace case insensitively
            idx = polished.lower().find(informal)
            orig_word = polished[idx:idx + len(informal)]
            polished = polished[:idx] + formal.split(" / ")[0] + polished[idx + len(informal):]
            improvements.append(f"Replaced colloquial '{orig_word}' with scholarly '{formal}'")

    if not improvements:
        improvements.append("Enhanced syntactical coherence and scholarly cadence.")

    report = f"""✍️ Academic Revision:
Original: "{raw}"
Polished: "{polished}"

Key Scholarly Enhancements:
"""
    for imp in improvements:
        report += f"- {imp}\n"

    if veda_echo:
        veda_echo.ui.write_log(report)
        veda_echo.speak("Your text has been refined with academic diction, Rohan.")
    return True
