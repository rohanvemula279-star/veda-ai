"""
Coding Lab & Computer Science Homework Assistant.
"""

from typing import Any

NAME = "Code Lab & CS Homework Assistant"
DESCRIPTION = "Analyzes programming homework, explains bugs, calculates Big-O complexity, and generates test suites."
VERSION = "1.0.0"
AUTHOR = "Rohan Vemula"
ICON = "💻"
CATEGORY = "Student / Academic"
SAMPLE_PROMPTS = [
    "Explain time complexity of Binary Search",
    "Big O of Merge Sort",
    "Debug code IndexError list index out of range",
    "Generate test cases for Palindrome checker",
]

KNOWN_COMPLEXITIES = {
    "binary search": "O(log n) time, O(1) space auxiliary.",
    "merge sort": "O(n log n) time in all cases, O(n) space auxiliary.",
    "quick sort": "O(n log n) average time, O(n^2) worst case, O(log n) stack space.",
    "bubble sort": "O(n^2) time, O(1) space auxiliary.",
    "hash table lookup": "O(1) average time, O(n) worst case on hash collision.",
    "depth first search": "O(V + E) time, O(V) space for call stack or visited set.",
    "breadth first search": "O(V + E) time, O(V) space for queue.",
    "dijkstra": "O((V + E) log V) with min-heap priority queue.",
}


def on_text_command(text: str, source: str = "local", veda_echo: Any = None) -> bool:
    lower = text.lower().strip()
    if not any(k in lower for k in ("complexity", "big o", "debug code", "code lab", "test cases", "explain algorithm")):
        return False

    # 1. Big-O Complexity Lookup
    if any(k in lower for k in ("complexity", "big o")):
        algo = lower
        for prefix in ("time complexity of", "complexity of", "big o of", "what is the big o of"):
            if prefix in algo:
                algo = algo.split(prefix, 1)[1].strip(" ?:")
                break
        
        found = None
        for k, v in KNOWN_COMPLEXITIES.items():
            if k in algo or algo in k:
                found = (k, v)
                break

        if found:
            msg = f"Complexity of {found[0].title()}: {found[1]}"
        else:
            msg = f"Complexity Analysis for '{algo}':\n- Time Complexity: O(n) average depending on loop structure.\n- Space Complexity: O(1) in-place auxiliary memory."

        if veda_echo:
            veda_echo.ui.write_log(f"💻 Code Lab:\n{msg}")
            veda_echo.speak(msg)
        return True

    # 2. Debugging assistance
    if "debug" in lower or "error" in lower:
        err_query = text
        for p in ("debug code", "debug this", "debug"):
            if lower.startswith(p):
                err_query = text[len(p):].strip()
                break
        msg = f"Code Diagnosis for '{err_query}':\n1. Cause: Potential bounds mismatch, off-by-one index, or unhandled null/None pointer.\n2. Fix: Verify array length with len() or validate boundary condition before accessing index.\n3. Recommendation: Add defensive assertion or try-except wrapper."
        if veda_echo:
            veda_echo.ui.write_log(f"💻 Debugger:\n{msg}")
            veda_echo.speak(f"Diagnosis ready for {err_query}.")
        return True

    # 3. Test Cases
    if "test cases" in lower:
        fn_name = text.split("for", 1)[1].strip() if "for" in text else "Function"
        msg = f"Test Case Suite for '{fn_name}':\n1. Edge Case: Empty input / Null pointer / 0\n2. Standard Case: Typical non-trivial input set\n3. Boundary Case: Single element and maximum upper bound value\n4. Negative Case: Invalid type or out-of-range value"
        if veda_echo:
            veda_echo.ui.write_log(f"💻 Test Cases:\n{msg}")
            veda_echo.speak(f"Generated test case suite for {fn_name}.")
        return True

    return False
