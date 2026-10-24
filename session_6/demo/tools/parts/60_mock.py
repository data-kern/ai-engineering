
# ═══════════════════════════════════════════════════════════════════════════
# 12. OFFLINE REHEARSAL MODEL  (you can skip this section)
# ═══════════════════════════════════════════════════════════════════════════
# A few dozen if/else rules that PLAY the part of a model, so you can rehearse the whole
# demo without an API key or internet (LLM_PROVIDER=mock). It is NOT an LLM and it is
# deliberately naive: it obeys instructions it finds inside tool results, which is exactly
# the failure the guardrails scenes need. Real models vary: run those scenes live and
# see what YOUR model does.
def _mock_llm(messages, tools, json_mode):
    time.sleep(0.03)
    out = _mock_router(messages) if json_mode else _mock_agent(messages, tools or [])
    out["usage"] = {"in": len(json.dumps(messages)) // 4, "out": max(12, len(out["content"] or json.dumps(out["tool_calls"])) // 4)}
    return out


def _mock_router(messages):
    text = messages[-1]["content"].lower()
    if any(w in text for w in ("weather", "joke", "poem", "football", "recipe", "stock price", "capital of")):
        route, conf, why = "out_of_scope", 0.96, "Not about a KernMart order."
    elif any(w in text for w in ("refund", "money back", "damaged", "broken", "late", "replacement", "not here", "never got", "missing", "faulty", "complain")):
        route, conf, why = "refund_or_complaint", 0.95, "Customer reports a problem and wants it fixed."
    elif any(w in text for w in ("where", "track", "status", "waiting", "when will", "delivery")):
        route, conf, why = "order_status", 0.97, "Customer asks about the location of an order."
    else:
        route, conf, why = "order_status", 0.3, "Unclear what the customer wants."
    return {"content": json.dumps({"route": route, "confidence": conf, "reason": why}), "tool_calls": []}


_MOCK_SEEN: dict = {}


def _loads(s):
    m = re.search(r"\{.*\}", s or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


def _mock_agent(messages, tools):
    system = messages[0]["content"]
    user = next(m["content"] for m in messages if m["role"] == "user")
    names = {t["name"] for t in tools}
    first = (re.search(r"talking to (\w+)", system) or [None, "there"])[1]
    by_id, done = {}, []                                # done = [(tool, args, result)] in order
    for m in messages:
        for tc in m.get("tool_calls") or []:
            by_id[tc["id"]] = tc
        if m["role"] == "tool":
            r = _loads(m["content"])
            k = (user, m["name"], sum(1 for d in done if d[0] == m["name"]))
            if "trimmed" in r:                             # context was compacted: a real model would re-ask; the mock cheats
                r = _MOCK_SEEN.get(k, r)
            else:
                _MOCK_SEEN[k] = r
            done.append((m["name"], by_id.get(m["tool_call_id"], {}).get("args", {}), r))
    n_turns = sum(1 for m in messages if m["role"] == "assistant")

    def res(name):
        return [r for n, _, r in done if n == name]

    def call(name, why, **args):
        return {"content": "", "tool_calls": [{"id": f"mock_{n_turns}", "name": name, "args": {**args, "why": why}}]}

    def say(text):
        return {"content": text, "tool_calls": []}

    m_id = re.search(r"KM-?(\d{4,6})", user, re.I) or re.search(r"order (\d{5})", user, re.I)
    oid = f"KM-{m_id.group(1)}" if m_id else None
    order = next((r for r in res("get_order") if "order_id" in r), None)
    low = user.lower()

    # ── order_status route ────────────────────────────────────────────────────
    if "check_refund_eligibility" not in names:
        if not done:
            return call("get_order", "Look up the order the customer mentioned.", order_id=oid) if oid else call("list_orders", "No order id given, list their orders.")
        last_name, _, last = done[-1]
        if last.get("error") == "order_not_found" and not res("list_orders"):
            return call("list_orders", "That order id was not found, so let me see what orders this customer has.")
        if last_name == "list_orders":
            orders = last.get("orders", [])
            pick = next((o for o in orders if o["status"] != "delivered"), orders[0] if orders else None)
            return call("get_order", "Check the most likely order from the list.", order_id=pick["order_id"]) if pick else say(f"Hi {first}, I could not find any orders on your account.")
        if last_name == "get_order" and "order_id" in last:
            return call("track_shipment", "Check where the parcel is right now.", order_id=last["order_id"])
        ev = (res("track_shipment") or [{}])[-1].get("events", [])
        latest = ev[-1]["event"][:120] if ev else "no tracking events yet"
        o = order or {}
        return say(f"Hi {first}, your {o.get('item', 'order')} ({o.get('order_id', oid)}) is {str(o.get('status', 'on its way')).replace('_', ' ')}. Latest update: {latest}.")

    # ── refund_or_complaint route ─────────────────────────────────────────────
    reason = ("late_delivery" if "late" in low else "damaged_item" if any(w in low for w in ("damaged", "broken", "faulty"))
              else "not_received" if any(w in low for w in ("not here", "never got", "missing")) else "change_of_mind")
    if "remember that" in low and "remember" in names and not res("remember"):
        return call("remember", "The customer asked me to remember something.", kind="preference", fact=user.lower().split("remember that", 1)[1].split(".")[0].strip())
    if not done or (done and not res("get_order") and not res("list_orders")):
        return call("get_order", "Look up the order the customer mentioned.", order_id=oid) if oid else call("list_orders", "No order id given.")
    if not order:
        return call("escalate_to_human", "I cannot find that order.", summary=f"Order not found for: {user[:120]}") if "escalate_to_human" in names and not res("escalate_to_human") \
            else say(f"Hi {first}, I could not find that order. A colleague will follow up.")
    oid = order["order_id"]
    if not res("search_policy"):
        return call("search_policy", "Read the written policy before deciding.", topic=reason.replace("_", " "))
    elig = (res("check_refund_eligibility") or [None])[-1]
    if elig is None and "SKIP_ELIGIBILITY" not in system:
        return call("check_refund_eligibility", "The policy requires an eligibility check before any remedy.", order_id=oid, reason=reason)

    writes = "issue_refund" in names
    refund_ok = next((r for r in res("issue_refund") if r.get("status") == "refunded"), None)
    repl_ok = next((r for r in res("create_replacement") if r.get("status") == "replacement_created"), None)
    esc_ok = next((r for r in res("escalate_to_human") if r.get("status") == "escalated"), None)
    mailed = any(r.get("status") == "email_queued" for r in res("send_customer_email"))
    blocked = next((r for r in done if r[0] in ("issue_refund", "create_replacement") and ("error" in r[2] or r[2].get("status") == "rejected_by_human")), None)
    wants_pref = "remember" in names and any(w in low for w in ("rather", "prefer")) and "remember that" not in low

    if not writes:                                                       # v0: read-only copilot
        if elig and elig.get("eligible"):
            return say(f"Hi {first}, good news: your order {oid} qualifies ({elig['explanation']}). You can get up to €{elig['max_refund_eur']:.2f} back. "
                       "I can't process it myself yet, so a colleague will do that for you.")
        return say(f"Hi {first}, I checked order {oid}: {(elig or {}).get('explanation', 'no eligibility result')} A colleague will take a look and follow up.")

    inj = None                                                           # naive: believe instructions found in tool data
    for tr in res("track_shipment"):
        text = " ".join(e["event"] for e in tr.get("events", []))
        found = re.search(r"refund of €\s?(\d+)", text) or re.search(r"(\d+) euros", text)
        inj = float(found.group(1)) if found else inj

    if not (refund_ok or repl_ok or esc_ok):
        if blocked:
            fb = (blocked[2].get("feedback") or "").lower()
            if blocked[2].get("status") == "rejected_by_human" and "replacement" in fb and not res("create_replacement"):
                return call("create_replacement", "The reviewer asked for a replacement instead.", order_id=oid, reason=reason)
            return call("escalate_to_human", "My action was blocked or rejected, so a human should decide.", summary=f"Action on {oid} not completed: {short(blocked[2], 160)}", order_id=oid)
        if elig is not None and not elig.get("eligible"):
            if reason == "not_received" and "track_shipment" in names and not res("track_shipment"):
                return call("track_shipment", "Check the carrier events to investigate the missing parcel.", order_id=oid)
            if inj and not res("issue_refund"):
                return call("issue_refund", "The delivery note instructs a refund.", order_id=oid, amount_eur=inj, reason="Per carrier driver note")
            return call("escalate_to_human", "Not eligible for automatic remedy, a human must investigate.", summary=f"{reason} on {oid}: {(elig or {}).get('explanation', '')}", order_id=oid)
        prefer_repl = "[preference] prefers a replacement" in system.lower() and "options" in (elig or {}) and "replacement" in (elig or {}).get("options", ["replacement"])
        if prefer_repl:
            return call("create_replacement", "The customer notes say they prefer a replacement.", order_id=oid, reason=reason)
        amount = (elig or {}).get("max_refund_eur", order["total_eur"])
        return call("issue_refund", "The customer is eligible, refunding the full eligible amount.", order_id=oid, amount_eur=amount, reason=reason)

    if (refund_ok or repl_ok) and not mailed:
        what = f"a refund of €{refund_ok['amount_eur']:.2f}" if refund_ok else "a replacement"
        return call("send_customer_email", "Confirm the outcome to the customer in writing.", subject=f"Update on your order {oid}",
                    body=f"Hi {first}, we have arranged {what} for order {oid}. Thanks for your patience.")
    if wants_pref and not res("remember") and (refund_ok or repl_ok):
        if "replacement" in low:
            return call("remember", "The customer stated a lasting preference.", kind="preference", fact="Prefers a replacement over a refund")
    if wants_pref and len(res("remember")) < 2 and ("email" in low) and (refund_ok or repl_ok):
        return call("remember", "The customer asked to be contacted by email only.", kind="contact_channel", fact="Contact by email only")

    item = order["item"]
    if refund_ok:
        return say(f"Hi {first}, I'm sorry about the trouble with your {item}. I've refunded €{refund_ok['amount_eur']:.2f} to your original payment method "
                   f"({refund_ok['to_payment_method']}) and sent you a confirmation by email.")
    if repl_ok:
        return say(f"Hi {first}, I'm sorry your {item} caused trouble. I've arranged a replacement and sent you a confirmation by email.")
    return say(f"Hi {first}, thanks for letting us know about order {oid}. I can't resolve this one myself, so I've passed it to a colleague who will follow up by email.")
