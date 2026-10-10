"""
DataKern Session 5 Demo — Step 1: Input & Chunk Sanitization (Defense 2)
Scans text for adversarial prompt injection patterns to treat retrieved content
as strictly untrusted data (Slides 13 & 14).
"""

import re
from typing import Tuple, List

# Common prompt injection signatures discussed in Slide 14
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(a|an)?\s*",
    r"new\s+(system\s+)?instructions?:",
    r"bypass\s+all\s+(security|guardrails?|rules?)",
    r"system\s*prompt\s*override",
    r"refuse\s+to\s+acknowledge",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan_for_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Scans a block of text for known prompt injection signatures.
    Returns:
        (is_flagged: bool, matches_found: list of pattern matches)
    """
    matches = []
    for pattern in COMPILED_PATTERNS:
        found = pattern.findall(text)
        if found:
            matches.append(pattern.pattern)

    is_flagged = len(matches) > 0
    return is_flagged, matches


def sanitize_or_quarantine(text: str, quarantine: bool = False) -> Tuple[str, bool, List[str]]:
    """
    Scans text. If flagged:
    - If quarantine is True, replaces with safe sanitized warning.
    - If quarantine is False, neutralizes known trigger phrases.
    """
    flagged, triggers = scan_for_injection(text)
    if not flagged:
        return text, False, []

    if quarantine:
        sanitized = (
            "[QUARANTINED CONTENT — POTENTIAL PROMPT INJECTION DETECTED. "
            "TEXT REMOVED BY DEFENSE LAYER 2]"
        )
        return sanitized, True, triggers

    # Defuse patterns by inserting break tokens
    sanitized = text
    for pattern in COMPILED_PATTERNS:
        sanitized = pattern.sub("[FILTERED_INJECTION_TRIGGER]", sanitized)

    return sanitized, True, triggers
