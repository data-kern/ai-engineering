
#@if v>=5
# ═══════════════════════════════════════════════════════════════════════════
# 9. TRACING — every router call, model call and tool call becomes a span
# ═══════════════════════════════════════════════════════════════════════════
# A trace = the full tree of one request. We keep it locally (always works, printed as a
# waterfall) AND ship it to Arize Phoenix if it is running (nice UI at http://localhost:6006).
# Standard OpenTelemetry underneath — the same spans can go to Datadog, Grafana, Langfuse …
import contextvars
import functools

PHOENIX_URL = os.getenv("PHOENIX_URL", "http://localhost:6006")
SPANS: list[dict] = []
_stack: contextvars.ContextVar = contextvars.ContextVar("span_stack", default=())
_tracer = None


def setup_tracing() -> str:
    """Connect to Phoenix if it is running. Returns 'phoenix' or 'local'."""
    global _tracer
    try:
        import urllib.request
        urllib.request.urlopen(PHOENIX_URL, timeout=1.5)
        from phoenix.otel import register
        provider = register(project_name="kernmart-agent", endpoint=PHOENIX_URL + "/v1/traces", batch=False,
                            verbose=False, set_global_tracer_provider=False)
        _tracer = provider.get_tracer("kernmart")
        return "phoenix"
    except Exception:
        _tracer = None
        return "local"


def _annotate(rec: dict, kind: str, a: tuple, kw: dict, out) -> None:
    at = rec["attrs"]
    at["openinference.span.kind"] = kind
    if kind == "LLM":
        msgs = a[0] if a else kw.get("messages", [])
        at["input.value"] = short(msgs[-1].get("content") or "", 300)
        at["llm.model_name"] = {"groq": GROQ_MODEL, "openai": OPENAI_MODEL, "gemini": GEMINI_MODEL, "mock": "mock"}[PROVIDER]
        at["llm.token_count.prompt"], at["llm.token_count.completion"] = out["usage"]["in"], out["usage"]["out"]
        at["output.value"] = out["content"] or "tool_calls: " + ", ".join(t["name"] for t in out["tool_calls"])
    elif kind == "TOOL":
        at["tool.name"] = a[0]
        at["input.value"] = short(a[1], 300)
        at["output.value"] = short(out, 300)
    elif kind == "AGENT":
        at["input.value"] = short(a[1] if len(a) > 1 else kw.get("user_message", ""), 300)
        at["output.value"] = short(out["reply"], 300)
        at["kernmart.run_id"], at["kernmart.status"] = out["run_id"], out["status"]
    else:
        at["input.value"] = short(a[-1] if a and isinstance(a[-1], str) else "", 200)


def traced(kind: str, name):
    """Decorator: wrap a function in a span. `name` is a string or f(args, kwargs) → string."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            nm = name(a, kw) if callable(name) else name
            parent = _stack.get()
            rec = {"id": len(SPANS) + 1, "parent": parent[-1] if parent else None, "name": nm, "kind": kind,
                   "t0": time.time(), "t1": None, "attrs": {}}
            SPANS.append(rec)
            token = _stack.set(parent + (rec["id"],))
            cm = _tracer.start_as_current_span(nm) if _tracer else contextlib.nullcontext()
            with cm as s:
                try:
                    out = fn(*a, **kw)
                    _annotate(rec, kind, a, kw, out)
                    return out
                except Exception as e:
                    rec["error"] = repr(e)
                    raise
                finally:
                    rec["t1"] = time.time()
                    _stack.reset(token)
                    if s is not None:
                        for k, v in rec["attrs"].items():
                            s.set_attribute(k, v)
                        if "error" in rec:
                            s.set_attribute("error", rec["error"])
        return wrapper
    return deco


call_llm = traced("LLM", "llm.call")(call_llm)
execute_tool = traced("TOOL", lambda a, kw: f"tool:{a[0]}")(execute_tool)


def print_trace() -> None:
    """Text waterfall of the most recent agent.run — the same shape you will see in Phoenix."""
    roots = [s for s in SPANS if s["parent"] is None and s["name"] == "agent.run"]
    if not roots:
        print("   (no trace recorded yet)")
        return
    root = roots[-1]
    t0, total = root["t0"], max((root["t1"] or time.time()) - root["t0"], 1e-6)
    kids: dict = {}
    for s in SPANS:
        kids.setdefault(s["parent"], []).append(s)

    def walk(s, depth):
        t1 = s["t1"] or time.time()
        start, width = int((s["t0"] - t0) / total * 36), max(1, int((t1 - s["t0"]) / total * 36))
        colour = {"LLM": ORANGE, "TOOL": TEAL, "AGENT": GREY, "CHAIN": GREY}[s["kind"]]
        label = ("  " * depth + s["name"]).ljust(34)
        tok = f" {s['attrs'].get('llm.token_count.prompt', 0) + s['attrs'].get('llm.token_count.completion', 0)} tok" if s["kind"] == "LLM" else ""
        print(paint(f"   {label} {' ' * start}{'█' * width}{' ' * (36 - start - width)} {int((t1 - s['t0']) * 1000):>6} ms{tok}", colour))
        for k in kids.get(s["id"], []):
            walk(k, depth + 1)
    print(paint("   " + "span".ljust(34) + " " + "timeline (🟠 model · 🟢 tools)".ljust(37) + "   time", GREY))
    walk(root, 0)
#@end
