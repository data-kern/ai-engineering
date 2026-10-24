
# ═══════════════════════════════════════════════════════════════════════════
# 4. THE LIVE CONSOLE — every decision is an event; events are printed in colour
# ═══════════════════════════════════════════════════════════════════════════
#   🧠 ORANGE = the MODEL decided this        ⚙️  TEAL = our CODE decided this
#   🙋 YELLOW = a HUMAN decided this           🛡️  RED  = something was blocked
# Keeping "who decided" visible is the whole point of this demo.
EVENTS: list[dict] = []
CURRENT = {"run_id": None}
ACTOR = {"route": "model+code", "llm": "model", "tool_call": "model", "final": "model", "tool_result": "code",
         "policy": "code", "approval": "human", "checkpoint": "code", "stop": "code", "guard": "code",
         "memory": "code", "context": "code", "crash": "code", "resume": "code", "trace": "code"}


def emit(event: str, **data) -> None:
    rec = {"ts": time.time(), "run_id": CURRENT["run_id"], "event": event, "actor": ACTOR.get(event, "code"), **data}
    EVENTS.append(rec)
#@if v>=1
    audit_write(rec)
#@end
    if VERBOSE:
        render(rec)


def render(e: dict) -> None:
    ev = e["event"]
    if ev == "route":
        print(orange_line(f"🧠 MODEL   classified the request → {e['model_route']} (confidence {e['confidence']}) “{e['reason']}”"))
        print(teal_line(f"⚙️  CODE    applied route '{e['route']}' → allowed tools: {e['tools'] or 'none'}"))
    elif ev == "llm":
        print(paint(f"   ⏱  step {e['step']} · model call took {e['latency']}s · tokens in/out {e['tokens_in']}/{e['tokens_out']}"
                    + (" (cached)" if e.get("cached") else ""), GREY))
        if e["text"] and e["wants_tool"]:
            print(orange_line(f"🧠 MODEL   says: {short(e['text'], 200)}"))
    elif ev == "tool_call":
        args = ", ".join(f"{k}={v!r}" for k, v in e["args"].items())
        print(orange_line(f"🧠 MODEL   wants to call → {e['name']}({args})"))
        if e["why"]:
            print(orange_line(f"           why (stated rationale): “{e['why']}”"))
    elif ev == "tool_result":
        print(teal_line(f"⚙️  CODE    ran {e['name']} ({e['ms']} ms) → {short(e['result'], 210)}"))
    elif ev == "policy":
        if e["ok"]:
            print(teal_line(f"⚙️  CODE    policy check passed ({e['rule']})"))
        else:
            print(paint(f"🛡️  CODE    BLOCKED [{e['rule']}] {e['message']}", RED))
    elif ev == "approval":
        tag = " (decision restored from the saved state — no need to ask again)" if e.get("resumed") else ""
        print(paint(f"🙋 HUMAN   {e['decision'].upper()}{(' → ' + str(e['detail'])) if e.get('detail') else ''}{tag}", YELLOW))
    elif ev == "checkpoint":
        if not e.get("quiet"):
            print(paint(f"   💾 checkpoint saved · step {e['step']} · {e['n_messages']} messages in state", GREY))
    elif ev == "guard":
        print(paint(f"🛡️  CODE    guardrail '{e['layer']}': {e['action']}", RED if e.get("blocked") else TEAL))
    elif ev == "memory":
        print(teal_line(f"🧩 CODE    memory: {e['action']}"))
    elif ev == "context":
        print(teal_line(f"✂️  CODE    context window trimmed: {e['action']}"))
    elif ev == "crash":
        print(paint(f"💥 PROCESS KILLED right after '{e['tool']}' ran, before its result was saved!", RED))
    elif ev == "resume":
        print(teal_line(f"⚙️  CODE    resuming {e['run_id']} from its last checkpoint (step {e['step']}, {e['n_messages']} messages)"))
    elif ev == "stop":
        print(paint(f"🛑 CODE    stop condition hit: {e['reason']}", RED))
    elif ev == "final":
        print(orange_line("🧠 MODEL   final reply to the customer:" if e["status"] == "done" else "⚙️  CODE    reply to the customer:"))
        print(textwrap.indent(textwrap.fill(e["reply"], 76), "   │ "))
        print(paint(f"   ✔ status={e['status']} · steps={e['steps']} · tokens={e['tokens']}", GREY))


def orange_line(s: str) -> str:
    return paint(s, ORANGE)


def teal_line(s: str) -> str:
    return paint(s, TEAL)

#@if v>=1


# ═══════════════════════════════════════════════════════════════════════════
# 5. STATE — what survives a crash. Lives in agent_state.db (NOT in the business DB)
# ═══════════════════════════════════════════════════════════════════════════
# STATE   = where is THIS run? (messages so far, step, tokens)  → saved after EVERY step
#           A run is a row in `runs`. Kill the process, read the row, carry on.
# AUDIT   = append-only diary of who decided what (model / code / human)
SCHEMA_STATE = """
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, customer_id TEXT, user_message TEXT, route TEXT, status TEXT,
                                step INTEGER, tokens INTEGER, messages TEXT, reply TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, run_id TEXT, actor TEXT, event TEXT, detail TEXT);
#@if v>=2
CREATE TABLE IF NOT EXISTS approvals(run_id TEXT, call_id TEXT, tool TEXT, decision TEXT, args TEXT, feedback TEXT, decided_at TEXT,
                                     PRIMARY KEY(run_id, call_id));
#@end
#@if v>=4
CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT, kind TEXT, fact TEXT, run_id TEXT, created_at TEXT);
#@end
"""


def state_db() -> sqlite3.Connection:
    con = sqlite3.connect(STATE_DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA_STATE)
    return con


def reset_state_db() -> None:
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(STATE_DB + suffix):
            os.remove(STATE_DB + suffix)
    state_db().close()


def audit_write(rec: dict) -> None:
    detail = {k: v for k, v in rec.items() if k not in ("ts", "run_id", "event", "actor")}
    con = state_db()
    con.execute("INSERT INTO audit(ts, run_id, actor, event, detail) VALUES (?,?,?,?,?)",
                (datetime.fromtimestamp(rec["ts"]).isoformat(timespec="milliseconds"), rec["run_id"], rec["actor"],
                 rec["event"], json.dumps(detail, ensure_ascii=False, default=str)))
    con.commit()
    con.close()


def save_run(run: dict, quiet: bool = False) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    con = state_db()
    con.execute("INSERT INTO runs(id, customer_id, user_message, route, status, step, tokens, messages, reply, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET route=excluded.route, status=excluded.status,"
                " step=excluded.step, tokens=excluded.tokens, messages=excluded.messages, reply=excluded.reply, updated_at=excluded.updated_at",
                (run["id"], run["customer_id"], run["user_message"], run["route"], run["status"], run["step"], run["tokens"],
                 json.dumps(run["messages"], ensure_ascii=False), run["reply"], now, now))
    con.commit()
    con.close()
    emit("checkpoint", step=run["step"], n_messages=len(run["messages"]), quiet=quiet)


def load_run(run_id: str) -> dict:
    con = state_db()
    r = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    con.close()
    if r is None:
        raise KeyError(f"No saved run {run_id}")
    run = {k: r[k] for k in ("id", "customer_id", "user_message", "route", "status", "step", "tokens", "reply")}
    run.update(messages=json.loads(r["messages"]), started=time.time())
    return run


def latest_run_id(status: str = "running") -> str | None:
    con = state_db()
    r = con.execute("SELECT id FROM runs WHERE status=? ORDER BY updated_at DESC, rowid DESC LIMIT 1", (status,)).fetchone()
    con.close()
    return r["id"] if r else None


def show_table(sql: str, title: str, args: tuple = (), width: int = 100) -> None:
    con = state_db()
    rows = con.execute(sql, args).fetchall()
    con.close()
    print(paint(f"   ┌─ {title}", TEAL))
    for r in rows:
        print(paint("   │ " + short(" | ".join(str(r[k]) for k in r.keys()), width), TEAL))
    if not rows:
        print(paint("   │ (no rows)", TEAL))
    print(paint("   └" + "─" * 60, TEAL))


def run_child(key: str, crash_after: str | None = None, idempotent: bool = True, answers: str = "") -> int:
    """Run a scenario in a SEPARATE process so we can really kill it mid-way. Its output is streamed here
    (works in terminals, VS Code and Colab/Jupyter alike)."""
    env = {**os.environ, "DEMO_CHILD": "1", "DEMO_AUTO": "1", "DEMO_ANSWERS": answers, "IDEMPOTENT": "on" if idempotent else "off",
           "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    if crash_after:
        env["CRASH_AFTER"] = crash_after
    print(paint(f"   ▶ starting a child process for scenario {key} …", GREY))
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--child", key], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for line in p.stdout:
        print(line, end="")
    return p.wait()


def maybe_crash(tool_name: str) -> None:
    """DEMO ONLY: simulates `kill -9` at the worst possible moment (side effect done, result not yet saved)."""
    if os.getenv("DEMO_CHILD") and os.getenv("CRASH_AFTER") == tool_name:
        emit("crash", tool=tool_name)
        sys.stdout.flush()
        os._exit(137)
#@end
