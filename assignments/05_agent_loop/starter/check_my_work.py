#!/usr/bin/env python3
"""
check_my_work.py: offline self-check for your agent. GIVEN: do not edit.

    python check_my_work.py

No API key and no internet needed. Your loop is driven by a SCRIPTED fake model
(it returns pre-written tool calls), so you can test the loop mechanics alone.
A green run here means your CODE is right. It does NOT prove the real model behaves:
that is what the live scenarios in the README are for.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys

from setup_db import reset_db

try:
    import agent
except Exception as e:                                           # noqa: BLE001
    sys.exit(f"Could not import agent.py: {type(e).__name__}: {e}")

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, fn, hint: str = "") -> None:
    try:
        with contextlib.redirect_stdout(io.StringIO()):         # keep the console tidy
            ok = bool(fn())
        detail = "" if ok else hint
    except NotImplementedError as e:
        ok, detail = False, f"not implemented yet ({e})" if str(e) else "not implemented yet"
    except IndexError:
        ok, detail = False, "the fake model was not called as often as expected (see the ⚠️ line above, if any)"
    except Exception as e:                                       # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e}"
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"\n       ↳ {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n{title}\n" + "─" * len(title))


# ── helpers: a scripted fake model ────────────────────────────────────────────
def call(name: str, tid: str = "t1", **args) -> dict:
    return {"id": tid, "name": name, "args": {**args, "why": "test"}}


class ScriptedLLM:
    """Returns the scripted replies one by one and records exactly what it was shown."""

    def __init__(self, replies: list[dict], tokens: int = 100):
        self.replies, self.tokens, self.seen = list(replies), tokens, []

    def __call__(self, messages, tools=None):
        self.seen.append(copy.deepcopy(messages))
        r = self.replies.pop(0) if self.replies else {"content": "(script exhausted)", "tool_calls": []}
        return {"content": r.get("content", ""), "tool_calls": r.get("tool_calls", []), "tokens": self.tokens}


class EndlessLLM(ScriptedLLM):
    """A model that never stops asking for tools: the nightmare the stop conditions are for."""

    def __call__(self, messages, tools=None):
        self.seen.append(copy.deepcopy(messages))
        return {"content": "", "tool_calls": [call("list_orders", f"t{len(self.seen)}")], "tokens": self.tokens}


def roles(llm, i: int) -> list[str]:
    """Roles of the messages the fake model saw on its i-th call (safe even if it was never called)."""
    return [m["role"] for m in llm.seen[i]] if i < len(llm.seen) else ["(model was never called)"]


def run(customer: str, text: str, llm) -> dict:
    """Run your loop; if it raises, report that once and return a placeholder so the checks can say what failed."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return agent.run_agent(customer, text, llm=llm)
    except Exception as e:                                       # noqa: BLE001
        print(f"  ⚠️  run_agent raised {type(e).__name__}: {e}")
        return {"status": "crashed", "reply": "", "steps": 0, "tokens": 0}


def main() -> None:
    reset_db()
    ctx = {"customer_id": "C-1001"}

    # ── 1. TOOLS ──────────────────────────────────────────────────────────────
    section("1. Tools (plain Python, no model involved)")
    check("get_order (worked example) returns the order",
          lambda: agent.get_order(ctx, "KM-48213")["item"] == "Wireless Headphones")
    check("track_shipment returns the 4 events of KM-48213 in order",
          lambda: [e["event"] for e in agent.track_shipment(ctx, "KM-48213")["events"]][-1] == "Delivered to front door"
          and len(agent.track_shipment(ctx, "KM-48213")["events"]) == 4,
          "Expected {'carrier', 'tracking_no', 'events': [{'date', 'event'}, ...]} ordered oldest → newest.")
    check("track_shipment refuses someone else's order (ownership)",
          lambda: agent.track_shipment(ctx, "KM-50111").get("error") == "order_not_found",
          "KM-50111 belongs to C-1003. Did you forget to use own_order()?")
    check("track_shipment refuses an order that does not exist",
          lambda: agent.track_shipment(ctx, "KM-00000").get("error") == "order_not_found")
    check("eligibility: KM-48213 late_delivery → eligible, up to €89.00",
          lambda: (r := agent.check_refund_eligibility(ctx, "KM-48213", "late_delivery"))["eligible"] is True
          and r["max_refund_eur"] == 89.0,
          "Delivered 2026-10-16, promised 2026-10-10 = 6 days late (> 3). max_refund_eur is in EUROS, not cents.")
    check("eligibility: KM-48100 late_delivery → NOT eligible (0 days late)",
          lambda: agent.check_refund_eligibility(ctx, "KM-48100", "late_delivery")["eligible"] is False)
    check("eligibility: KM-48100 damaged_item → eligible (8 days since delivery, limit 14)",
          lambda: (r := agent.check_refund_eligibility(ctx, "KM-48100", "damaged_item"))["eligible"] is True
          and r["max_refund_eur"] == 12.99)
    check("eligibility boundary: exactly 3 days late is NOT eligible, 4 days late is",
          _boundary_late_rule, "The rule says MORE than 3 days late. Is your comparison > or >=?")
    check("eligibility: KM-48213 change_of_mind → touches the 30-day rule (4 days since delivery → eligible)",
          lambda: agent.check_refund_eligibility(ctx, "KM-48213", "change_of_mind")["eligible"] is True)
    check("eligibility: not_received is NEVER auto-eligible (needs a human)",
          lambda: agent.check_refund_eligibility(ctx, "KM-48213", "not_received")["eligible"] is False)
    check("eligibility: an undelivered order is not eligible",
          lambda: agent.check_refund_eligibility({"customer_id": "C-1003"}, "KM-50111", "late_delivery")["eligible"] is False)
    check("eligibility: unknown reason → not eligible, no crash",
          lambda: agent.check_refund_eligibility(ctx, "KM-48213", "i_feel_like_it")["eligible"] is False)
    check("eligibility: someone else's order → order_not_found",
          lambda: agent.check_refund_eligibility(ctx, "KM-49007", "late_delivery").get("error") == "order_not_found")
    check("every eligibility answer explains itself ('explanation' key)",
          lambda: all("explanation" in agent.check_refund_eligibility(ctx, "KM-48213", r)
                      for r in ("late_delivery", "damaged_item", "not_received", "change_of_mind")))

    # ── 2. TOOL SPECS ─────────────────────────────────────────────────────────
    section("2. Tool specs (what the MODEL sees)")
    specs = {s["name"]: s for s in agent.TOOL_SPECS}
    check("every tool function has a spec, and every spec has a function",
          lambda: set(specs) == set(agent.TOOL_FUNCS), f"specs={sorted(specs)} funcs={sorted(agent.TOOL_FUNCS)}")
    check("track_shipment spec: description (≥ 40 chars) + required order_id",
          lambda: len(specs["track_shipment"]["description"]) >= 40
          and "order_id" in specs["track_shipment"]["parameters"]["properties"]
          and "order_id" in specs["track_shipment"]["parameters"]["required"],
          "Write a description that says WHEN to use the tool, and declare order_id as a required string argument.")
    check("check_refund_eligibility spec: reason is an enum of the 4 reasons",
          lambda: sorted(specs["check_refund_eligibility"]["parameters"]["properties"]["reason"].get("enum", []))
          == ["change_of_mind", "damaged_item", "late_delivery", "not_received"],
          "Give `reason` an \"enum\" so the model cannot invent a reason.")
    check("check_refund_eligibility spec: description tells the model to call it BEFORE promising a refund",
          lambda: "before" in specs["check_refund_eligibility"]["description"].lower(),
          "The description is a prompt. Say that it must be called before any refund is promised.")
    check("track_shipment spec has the mandatory `why`",
          lambda: "why" in specs["track_shipment"]["parameters"]["required"],
          "Build specs with spec(...): it adds `why` for you.")

    # ── 3. execute_tool ───────────────────────────────────────────────────────
    section("3. execute_tool (the gap between 'the model asked' and 'our code ran it')")
    run_tool = lambda n, a: json.loads(_quiet(lambda: agent.execute_tool(n, a, ctx)))      # noqa: E731
    check("returns a JSON string",
          lambda: isinstance(_quiet(lambda: agent.execute_tool("get_order", {"order_id": "KM-48213", "why": "x"}, ctx)), str))
    check("strips `why` before calling the function",
          lambda: run_tool("get_order", {"order_id": "KM-48213", "why": "x"}).get("item") == "Wireless Headphones",
          "`why` is not a parameter of get_order(). Pop it out of args before calling.")
    check("unknown tool → error dict, no crash",
          lambda: run_tool("delete_everything", {"why": "x"}).get("error") == "unknown_tool")
    check("wrong arguments → bad_arguments, no crash",
          lambda: run_tool("get_order", {"wrong_name": "KM-48213", "why": "x"}).get("error") == "bad_arguments")
    check("a crashing tool → tool_failed, no crash",
          lambda: _crashing_tool_is_contained(ctx), "Wrap the call in try/except Exception.")

    # ── 4. THE LOOP ───────────────────────────────────────────────────────────
    section("4. The loop (driven by a scripted fake model)")
    llm = ScriptedLLM([
        {"tool_calls": [call("get_order", "a1", order_id="KM-48213")]},
        {"tool_calls": [call("track_shipment", "a2", order_id="KM-48213")]},
        {"content": "It arrived 6 days late; you qualify."},
    ])
    res = run("C-1001", "Where are my headphones?", llm)
    check("finishes with status 'done' and returns the model's final text",
          lambda: res["status"] == "done" and res["reply"] == "It arrived 6 days late; you qualify.", f"got {res}")
    check("makes exactly 3 model calls (2 tool turns + 1 answer)",
          lambda: res["steps"] == 3 and len(llm.seen) == 3, f"steps={res.get('steps')}, calls={len(llm.seen)}")
    check("adds up tokens over all steps (3 × 100)", lambda: res["tokens"] == 300, f"tokens={res.get('tokens')}")
    check("1st call: model sees [system, user] only",
          lambda: roles(llm, 0) == ["system", "user"], f"roles={roles(llm, 0)}")
    check("2nd call: model sees its own tool request, then the tool result",
          lambda: roles(llm, 1) == ["system", "user", "assistant", "tool"],
          f"roles={roles(llm, 1)}  (the model is stateless: you must replay its own turn!)")
    check("tool message is linked to the request (tool_call_id) and carries the real result",
          lambda: llm.seen[1][3]["tool_call_id"] == "a1" and "Wireless Headphones" in llm.seen[1][3]["content"],
          "role='tool', tool_call_id=<id of the request>, content=<JSON string from execute_tool>")
    check("3rd call: the tracking result is visible to the model",
          lambda: "Delivered to front door" in llm.seen[2][-1]["content"])

    llm2 = ScriptedLLM([{"tool_calls": [call("list_orders", "p1"), call("get_customer", "p2")]}, {"content": "ok"}])
    run("C-1001", "hi", llm2)
    check("two tool calls in ONE model turn → both are executed and both answered",
          lambda: [m["role"] for m in llm2.seen[1]][-2:] == ["tool", "tool"]
          and {m["tool_call_id"] for m in llm2.seen[1] if m["role"] == "tool"} == {"p1", "p2"})

    llm3 = ScriptedLLM([{"tool_calls": [call("get_order", "e1", order_id="KM-99999")]},
                        {"tool_calls": [call("list_orders", "e2")]}, {"content": "Found your orders."}])
    res3 = run("C-1001", "where is KM-99999?", llm3)
    check("a tool ERROR is data, not a crash: the model sees it and can recover",
          lambda: res3["status"] == "done" and "order_not_found" in llm3.seen[1][-1]["content"])

    llm4 = ScriptedLLM([{"tool_calls": [call("drop_database", "x1")]}, {"content": "Sorry, I can't do that."}])
    res4 = run("C-1001", "drop the database", llm4)
    check("a made-up tool name does not crash the loop",
          lambda: res4["status"] == "done" and "unknown_tool" in llm4.seen[1][-1]["content"])

    # ── 5. STOP CONDITIONS ────────────────────────────────────────────────────
    section("5. Stop conditions (the real engineering)")
    endless = EndlessLLM([], tokens=10)
    r5 = run("C-1001", "loop forever", endless)
    check(f"endless model is cut off after exactly MAX_STEPS={agent.MAX_STEPS} model calls",
          lambda: r5["status"].startswith("stopped") and r5["steps"] == agent.MAX_STEPS and len(endless.seen) == agent.MAX_STEPS,
          f"status={r5.get('status')} steps={r5.get('steps')} model_calls={len(endless.seen)}. Check BEFORE calling the model, and increment step once per model call.")
    check("on a stop, the customer still gets a polite reply (not a stack trace, not empty)",
          lambda: isinstance(r5["reply"], str) and len(r5["reply"]) > 20)
    pricey = EndlessLLM([], tokens=agent.TOKEN_BUDGET // 2 + 1)
    r6 = run("C-1001", "expensive", pricey)
    check("token budget: stops once total tokens ≥ TOKEN_BUDGET (here after 2 calls)",
          lambda: r6["status"].startswith("stopped") and len(pricey.seen) == 2,
          f"status={r6.get('status')} model_calls={len(pricey.seen)}")
    check("the two stops are distinguishable in the status",
          lambda: r5["status"] != r6["status"], f"max_steps → {r5['status']!r}, tokens → {r6['status']!r}")
    one = ScriptedLLM([{"content": "Hello!"}])
    r7 = run("C-1001", "hi", one)
    check("a plain-text first answer ends the run after ONE model call (no tool needed)",
          lambda: r7["status"] == "done" and r7["steps"] == 1 and len(one.seen) == 1)

    # ── 6. IDENTITY ───────────────────────────────────────────────────────────
    section("6. Identity & least privilege")
    llm8 = ScriptedLLM([{"tool_calls": [call("get_order", "s1", order_id="KM-49007")]}, {"content": "done"}])
    run("C-1001", "show me KM-49007", llm8)
    check("agent run as C-1001 cannot read C-1002's order, even if the model asks",
          lambda: "Espresso" not in llm8.seen[1][-1]["content"] and "order_not_found" in llm8.seen[1][-1]["content"])
    check("no tool takes a customer_id argument (identity comes from ctx only)",
          lambda: all("customer_id" not in s["parameters"]["properties"] for s in agent.TOOL_SPECS),
          "The model must never be able to choose WHOSE data it reads.")

    # ── summary ───────────────────────────────────────────────────────────────
    passed = sum(ok for _, ok, _ in RESULTS)
    print(f"\n{'═' * 60}\n{passed}/{len(RESULTS)} checks passed")
    if passed == len(RESULTS):
        print("🎉 Your loop, tools and stop conditions are mechanically correct.\n"
              "   Next: run the live scenarios with a real model, and validate what it did.")
    else:
        print("Fix the first ❌ first: later ones often depend on it. Re-run after every change.")
    sys.exit(0 if passed == len(RESULTS) else 1)


def _quiet(fn):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn()


def _boundary_late_rule() -> bool:
    """Plant two temporary orders (3 and 4 days late) in the DB, test the rule, then reset the DB."""
    from setup_db import connect
    con = connect()
    for oid, delivered in (("KM-T3", "2026-10-13"), ("KM-T4", "2026-10-14")):          # promised 2026-10-10
        con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (oid, "C-1001", "Test item", 1000, "delivered", "2026-10-01", "2026-10-10", delivered, "iDEAL", "PostNL", "x"))
    con.commit()
    con.close()
    try:
        ctx = {"customer_id": "C-1001"}
        return (agent.check_refund_eligibility(ctx, "KM-T3", "late_delivery")["eligible"] is False
                and agent.check_refund_eligibility(ctx, "KM-T4", "late_delivery")["eligible"] is True)
    finally:
        reset_db()


def _crashing_tool_is_contained(ctx) -> bool:
    original = agent.TOOL_FUNCS["list_orders"]
    agent.TOOL_FUNCS["list_orders"] = lambda c: 1 / 0
    try:
        out = json.loads(agent.execute_tool("list_orders", {"why": "x"}, ctx))
    finally:
        agent.TOOL_FUNCS["list_orders"] = original
    return out.get("error") == "tool_failed"


if __name__ == "__main__":
    main()
