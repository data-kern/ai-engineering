#!/usr/bin/env python3
"""Generates the seven single-file demo scripts (01-07) from tools/parts/*.py.

Directives inside parts (lines starting with '#@'):  #@if <expr over v>  /  #@elif  /  #@else  /  #@end
Edit the parts, run `python tools/build_versions.py`, and all seven files are regenerated consistently."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, "tools", "parts")

VERSIONS = {
    0: dict(file="01_loop_and_tools.py", short="01 · The Loop, Tools & a Router",
            goal="Understand what an agent IS: a loop where the model chooses tools and our code runs them.",
            new=["The agent loop: think → act → observe → repeat", "Tools = functions the model can ASK for but never run",
                 "A router that picks a route (prompt + allowed tools)", "Stop conditions: max steps, token budget, timeout"],
            watch="Nothing external yet. Watch the colour-coded console: 🟠 model decided, 🟢 code decided.",
            recap=["The model never executes anything: it requests a tool, our code runs it", "The loop is ~50 lines; the model chooses the path",
                   "A router + allowed tools removes whole classes of risk", "Errors are observations: the agent adapts", "Every loop needs stop conditions"],
            next="python 02_state_and_resume.py  →  write tools, saved state, crash & resume, idempotency."),
    1: dict(file="02_state_and_resume.py", short="02 · State, Write Tools & Crash-Resume",
            goal="Give the agent hands (write tools) and a notebook (state) — and survive a crash without paying twice.",
            new=["Write tools: refund, replacement, email, escalate", "State saved after every step in agent_state.db",
                 "Write-ahead checkpoints + idempotency keys", "Resume a killed run"],
            watch="Open demo_data/agent_state.db (VS Code 'SQLite Viewer' or DB Browser for SQLite) → tables runs, audit. Keep the ledger table of kernmart.db in view.",
            recap=["State = the run's notebook, saved after every step", "A crash between 'money moved' and 'result saved' is the dangerous moment",
                   "Naive retry = double refund; idempotency key = one refund", "At-least-once + idempotent tools = effectively-once"],
            next="python 03_human_approval.py  →  a human gate for risky actions."),
    2: dict(file="03_human_approval.py", short="03 · Human-in-the-Loop Approval",
            goal="Let the agent act alone when risk is low, and stop for a human when it is not.",
            new=["Risk tiers: auto-run vs ask a human", "Approve / edit / reject-with-feedback", "Agent re-plans from human feedback",
                 "Approvals are saved, so a crash never asks twice"],
            watch="Open demo_data/agent_state.db → table approvals. Keep kernmart.db → ledger visible while you decide.",
            recap=["Gate = code (needs_approval), not a polite request to the model", "Low-risk actions stay automatic: humans only see what matters",
                   "A rejection with feedback is a steering wheel, not a dead end", "Decisions are persisted with the run"],
            next="python 04_guardrails.py  →  prompt injection, policy engine, output checks."),
    3: dict(file="04_guardrails.py", short="04 · Guardrails & Prompt Injection",
            goal="Watch an attack succeed, then see which layers actually stop it.",
            new=["Input guard (PII masking, attack phrases)", "Prompt hardening + text scan (weak layers)", "Policy engine in code (the real defence)",
                 "Output guard before the customer sees the reply"],
            watch="Open demo_data/kernmart.db → shipment_events (order KM-49007) to read the planted text, and ledger to see what moved.",
            recap=["Indirect injection: attackers write into data the agent reads", "Prompts and filters are speed bumps; attackers reword",
                   "Deterministic policy checks the ACTION, not the words", "A human gate alone fails when reviewers get tired", "Least privilege: no parameter, no abuse"],
            next="python 05_memory.py  →  short-term, long-term memory and the right to be forgotten."),
    4: dict(file="05_memory.py", short="05 · Memory",
            goal="Separate the three kinds of 'memory' and see an agent adapt to a returning customer.",
            new=["Context-window trimming (short-term)", "Long-term customer memory table + guarded remember tool", "Recall into the prompt",
                 "Memory poisoning defence and erasure"],
            watch="Open demo_data/agent_state.db → table memory and refresh it after each scene.",
            recap=["Short-term = context window, long-term = table, state = checkpoint", "Memory changes behaviour: verify what is stored",
                   "Memory is a write path: guard it like any other", "Isolated memory makes 'forget me' a one-liner"],
            next="python 06_observability_and_eval.py  →  traces, audit log and trajectory evals."),
    5: dict(file="06_observability_and_eval.py", short="06 · Observability & Evals",
            goal="See inside every run, prove who decided what, and catch regressions before customers do.",
            new=["Spans for router, model calls and tool calls (Arize Phoenix or local waterfall)", "Audit log queries",
                 "Trajectory evals with 3 assertions", "A prompt regression caught by the eval"],
            watch="Second terminal: `pip install arize-phoenix` then `phoenix serve` → http://localhost:6006 → project 'kernmart-agent'.",
            recap=["A trace is the tree of one request: model time vs tool time", "The audit log answers 'who authorised this?'",
                   "Evals test the PATH, not only the final text", "Safety nets can hide a regression: evals expose it"],
            next="python 07_full_agent.py  →  connect every layer: one request through the whole agent, then attack it."),
    6: dict(file="07_full_agent.py", short="07 · The Full Agent, everything connected",
            goal="Connect every layer you built and prove, with a trace, an audit trail and evals, who decided what.",
            new=["No new mechanism: this file connects scripts 01-06", "One request through router, memory, policy, human gate and output guard",
                 "Trace + audit tally: model vs code vs human", "The finished agent under attack, then the scoreboard",
                 "The complete clean reference: the agent without the teaching"],
            watch="Second terminal: `phoenix serve` → http://localhost:6006 → project 'kernmart-agent'. Keep demo_data/agent_state.db open (tables memory, approvals, audit).",
            recap=["An agent is LLM + tools + loop + memory/state + guardrails, wrapped in traces and evals",
                   "The model decides WHAT to ask for; code and humans decide what is ALLOWED",
                   "Every decision is on record: model, code or human, with a timestamp",
                   "The policy rules hold even when the model is fooled and the reviewer is tired",
                   "Frameworks give you the same pieces with less typing, not less thinking"],
            next="Next session: the same skeleton in LangGraph and the OpenAI Agents SDK. You now know what each piece does."),
}


def preprocess(text: str, v: int) -> str:
    out, stack = [], []          # stack of (active_now, taken_any, parent_active)
    for line in text.split("\n"):
        d = line.strip()
        if d.startswith("#@"):
            cmd, _, expr = d[2:].partition(" ")
            if cmd == "if":
                parent = all(s[0] for s in stack)
                ok = bool(eval(expr, {"v": v})) if parent else False
                stack.append([ok, ok, parent])
            elif cmd == "elif":
                s = stack[-1]
                ok = (not s[1]) and s[2] and bool(eval(expr, {"v": v}))
                s[0], s[1] = ok, s[1] or ok
            elif cmd == "else":
                s = stack[-1]
                s[0], s[1] = (not s[1]) and s[2], True
            elif cmd == "end":
                stack.pop()
            else:
                raise SystemExit(f"bad directive: {line}")
            continue
        if all(s[0] for s in stack):
            out.append(line)
    assert not stack, "unclosed #@if"
    return "\n".join(out)


def header(v: int, m: dict) -> str:
    new = "\n".join(f"      ✦ {x}" for x in m["new"])
    prev = "" if v == 0 else f"\n  Builds on script {v:02d}: everything from the previous file is still here, plus the new items below."
    return f'''#!/usr/bin/env python3
"""
KernMart Support Agent · {m["short"]}
{"=" * 70}
GOAL     {m["goal"]}{prev}

NEW IN THIS SCRIPT
{new}

HOW TO RUN   (Python 3.10+)
      pip install -r requirements.txt
      set one of:  GROQ_API_KEY=... (course default) · OPENAI_API_KEY=... · GEMINI_API_KEY=...   (no key → the script asks you what to do; offline mock only if you choose it)
      python {m["file"]}
      Colab / Jupyter:  %run {m["file"]}      (not "!python": that cannot answer the ENTER prompts)
      Optional:  GROQ_MODEL / OPENAI_MODEL / GEMINI_MODEL pick a model · LLM_PROVIDER=groq|openai|gemini|mock · LLM_CACHE=on (record/replay)
                 --scenes 1,3,4  (run only some scenes) · DEMO_AUTO=1 (no pauses, for rehearsal)

WHAT TO OPEN WHILE IT RUNS
      {m["watch"]}

No frameworks on purpose: plain Python, so every moving part is visible. A fictional retailer and synthetic data.
Generated from tools/parts by tools/build_versions.py; edit the parts, not this file.
"""
'''


def build():
    files = sorted(f for f in os.listdir(PARTS) if f.endswith(".py"))
    body = "\n".join(open(os.path.join(PARTS, f), encoding="utf-8").read() for f in files)
    for v, m in VERSIONS.items():
        text = preprocess(body, v)
        text = (text.replace("@@TITLE@@", repr("KernMart Support Agent · " + m["short"]))
                    .replace("@@RECAP@@", repr(m["recap"])).replace("@@NEXT@@", repr(m["next"]))
                    .replace("@@HAS_STATE@@", "True" if v >= 1 else "False"))
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        path = os.path.join(ROOT, m["file"])
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(header(v, m) + text.strip("\n") + "\n")
        print(f"built {m['file']:<36} {text.count(chr(10)) + 1:>5} lines")


if __name__ == "__main__":
    build()
