from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import textwrap
import time
import uuid
from collections import deque
from datetime import date, datetime

# ═══════════════════════════════════════════════════════════════════════════
# 0. SETUP  — config + console helpers. Nothing "agentic" here, skim it.
# ═══════════════════════════════════════════════════════════════════════════
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "demo_data")
os.makedirs(DATA_DIR, exist_ok=True)
BIZ_DB = os.path.join(DATA_DIR, "kernmart.db")          # KernMart's "real" business system
#@if v>=1
STATE_DB = os.path.join(DATA_DIR, "agent_state.db")      # the AGENT's own state (separate on purpose!)
#@end

TODAY = date(2026, 10, 20)       # frozen so every run behaves the same
MAX_STEPS = 8                    # stop condition 1: loop limit
TOKEN_BUDGET = 40_000            # stop condition 2: cost limit (tokens, all steps together)
TIMEOUT_S = 120                  # stop condition 3: wall-clock limit
#@if v>=2
REFUND_AUTO_LIMIT_EUR = 50.0     # refunds above this need a human
#@end
#@if v>=3
DAILY_REFUND_CAP_EUR = 300.0     # hard cap per day, whatever anyone approves
#@end
#@if v>=1
IDEMPOTENT = os.getenv("IDEMPOTENT", "on").lower() != "off"   # demo switch for the crash scene
#@end

AUTO = os.getenv("DEMO_AUTO") == "1"        # rehearsal mode: no pauses, scripted answers
ANSWERS = deque(a.strip() for a in os.getenv("DEMO_ANSWERS", "").split(";") if a.strip())
VERBOSE = True

if os.name == "nt":
    os.system("")                           # switches on ANSI colours in Windows terminals
with contextlib.suppress(Exception):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
USE_COLOR = not os.getenv("NO_COLOR")

ORANGE, TEAL, YELLOW, RED, GREY, GREEN = 208, 43, 220, 203, 245, 78


def paint(text: str, colour: int) -> str:
    return f"\033[38;5;{colour}m{text}\033[0m" if USE_COLOR else text


def banner(text: str) -> None:
    print("\n" + "=" * 70 + f"\n{text}\n" + "=" * 70)


def explain(text: str) -> None:
    print(textwrap.dedent(text).strip())


def predict(question: str) -> None:
    print(f"\n🔮 PREDICT: {question}")


def observe(text: str) -> None:
    print(f"\n👀 OBSERVE: {text}")


def pause(msg: str = "Press ENTER to continue") -> None:
    """Observe Mode: nothing moves until the room is ready."""
    if AUTO:
        print("─" * 70)
        return
    try:
        input(f"\n🔍 {msg} ➔ ")
    except EOFError:
        pass
    print("\n" + "─" * 70)


def eur(cents: int | float) -> str:
    return f"€{cents / 100:,.2f}"


def short(obj, n: int = 230) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"
