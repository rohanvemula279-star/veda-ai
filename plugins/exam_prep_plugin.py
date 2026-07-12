"""
Quiz & Exam Prep Simulator for Students.
"""

from typing import Any

NAME = "Quiz & Exam Prep Simulator"
DESCRIPTION = "Generates practice exams, multiple-choice quizzes, and explains correct answers across subjects."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "🎯"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Quiz me on Computer Networks",
    "Practice test for Organic Chemistry",
    "Exam prep for Machine Learning",
]

PRESET_QUESTIONS = {
    "networks": [
        ("Which layer in the OSI model is responsible for end-to-end communication?", "Transport Layer"),
        ("What protocol is used to map IP addresses to MAC addresses?", "ARP (Address Resolution Protocol)"),
        ("Which transport protocol is connection-oriented and guarantees delivery?", "TCP"),
    ],
    "chemistry": [
        ("What type of hybridization is present in methane (CH4)?", "sp3 hybridization"),
        ("What functional group is characteristic of alcohols?", "Hydroxyl group (-OH)"),
        ("What rule states that electrons fill lower-energy atomic orbitals first?", "Aufbau Principle"),
    ],
    "machine learning": [
        ("What technique prevents overfitting by penalizing large model weights?", "Regularization (L1/L2)"),
        ("Which metric is most appropriate for heavily imbalanced binary classification?", "F1-Score / PR-AUC"),
        ("What optimization algorithm uses running averages of both gradients and second moments?", "Adam Optimizer"),
    ],
}


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("quiz me on", "practice test", "exam prep", "mock test", "mock exam")):
        return False

    subject = text
    for p in ("quiz me on", "practice test for", "practice test on", "exam prep for", "mock test for", "mock exam for"):
        if lower.startswith(p):
            subject = text[len(p):].strip(" :,-")
            break

    if not subject:
        subject = "General Knowledge"

    sub_key = None
    for k in PRESET_QUESTIONS:
        if k in subject.lower():
            sub_key = k
            break

    if sub_key:
        qs = PRESET_QUESTIONS[sub_key]
        msg = f"📝 Practice Exam: {subject.title()}\n"
        for i, (q, a) in enumerate(qs, 1):
            msg += f"\nQ{i}: {q}\n   💡 Answer: {a}\n"
    else:
        msg = f"""📝 Practice Exam: {subject.title()}
Q1: What is the fundamental principle governing {subject}?
   💡 Core theorem and operational conditions.
Q2: State the primary trade-off encountered when optimizing {subject}.
   💡 Efficiency vs accuracy / Cost vs latency.
Q3: What diagnostic test or metric verifies correct functioning of {subject}?
   💡 Empirical benchmark validation.
"""

    if veda_echo:
        veda_echo.ui.write_log(f"🎯 Exam Prep Simulator:\n{msg}")
        veda_echo.speak(f"Generated a practice test for {subject}. Check your log for the questions and answers!")
    return True
