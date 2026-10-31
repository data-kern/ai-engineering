"""Plumbing, not part of the agent: print the loop's events in colour.

🧠 orange = the MODEL decided      ⚙️ teal = our CODE ran      🙋 yellow = a HUMAN decided      🛡️ red = blocked
"""
import json
import os

_ON = "NO_COLOR" not in os.environ
_C = {"model": "\033[38;5;208m", "code": "\033[36m", "human": "\033[33m", "bad": "\033[31m",
      "good": "\033[32m", "dim": "\033[2m", "bold": "\033[1m"}


def paint(kind, text):
    return f"{_C[kind]}{text}\033[0m" if _ON else text


def compact(obj):
    return json.dumps(obj, ensure_ascii=False)


def ask(prompt):
    """input() that treats Ctrl+D / Ctrl+C as an empty answer instead of a traceback."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def banner(text):
    print("\n" + paint("bold", "=" * 78) + "\n" + paint("bold", "  " + text) + "\n" + paint("bold", "=" * 78))


def render(ev):
    """Print one event of the agent loop."""
    t = ev["type"]
    if t == "model_request":
        print(paint("bold", f"\n── Loop {ev['step']} " + "─" * 60))
        print(paint("dim", f"   sending {len(ev['messages'])} messages + {len(ev['tool_names'])} tool schemas to the model"))
    elif t == "model_response":
        u = ev["usage"]
        print(paint("dim", f"   model replied in {u.get('ms', '?')} ms · {u.get('prompt_tokens', '?')} tokens in, "
                           f"{u.get('completion_tokens', '?')} out"))
    elif t == "think":
        print(f"{paint('model', '🧠 THINK')}   {ev['text']}")
    elif t == "tool_call":
        print(f"{paint('model', '🧠 ACT')}     model ASKS for {paint('model', ev['name'])}({ev['raw_arguments']})   "
              + paint("dim", "(nothing has run yet)"))
    elif t == "approval_needed":
        print(f"{paint('human', '🙋 PAUSED')}  {ev['reason']}")
    elif t == "approval_result":
        print(f"{paint('human', '🙋 HUMAN')}   {ev['summary']}")
    elif t == "guard":
        print(f"{paint('bad', '🛡️  GUARD')}   [{ev['where']}] {ev['detail']}")
    elif t == "observation":
        bad = isinstance(ev["result"], dict) and "error" in ev["result"]
        print(f"{paint('code', '⚙️  RUN')}     our code ran {ev['name']}")
        print(f"{paint('bad' if bad else 'code', '👁  OBSERVE')} {compact(ev['result'])[:300]}   "
              + paint("dim", "-> appended to messages"))
    elif t == "final":
        print(paint("good", f"\n✅ FINAL (loop {ev['step']}: no tool call means done)"))
        print(f"🤖 {ev['text']}")
    elif t == "stopped":
        print(paint("bad", f"\n🛑 {ev['reason']}"))
    elif t == "error":
        print(paint("bad", f"\n🛑 model call failed: {ev['error']}"))
