
# ═══════════════════════════════════════════════════════════════════════════
# 1. THE MODEL — one function, four providers (Groq, OpenAI, Gemini, offline mock)
# ═══════════════════════════════════════════════════════════════════════════
# Everything else in this file talks to `call_llm()` and nothing else.
# Messages use ONE neutral format; the adapters translate it:
#   {"role": "system" | "user" | "assistant" | "tool", "content": "...",
#    "tool_calls": [{"id", "name", "args"}]           # on assistant messages
#    "tool_call_id", "name"                           # on tool messages }
# Keys are read from environment variables. NEVER paste keys into code.
# Groq is the course default (free tier, same key as Sessions 4-5). Its API speaks the OpenAI protocol,
# so the OpenAI adapter below serves both. Model names change often: override with GROQ_MODEL if needed.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
CACHE_ON = os.getenv("LLM_CACHE", "off").lower() == "on"     # record/replay safety net for live demos
CACHE_FILE = os.path.join(DATA_DIR, "llm_cache.json")


def _gemini_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _pick_provider() -> str:
    wanted = os.getenv("LLM_PROVIDER", "").lower()
    if wanted in ("groq", "openai", "gemini", "mock"):
        return wanted
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if _gemini_key():
        return "gemini"
    return "mock"


PROVIDER = _pick_provider()


class LLMError(RuntimeError):
    pass


def _openai(messages, tools, json_mode, base_url=None, api_key=None, model=None):
    try:
        from openai import OpenAI
    except ImportError as e:
        raise LLMError("Missing package: pip install openai") from e
    msgs = []
    for m in messages:
        if m["role"] == "assistant":
            d = {"role": "assistant", "content": m.get("content") or None}
            if m.get("tool_calls"):
                d["tool_calls"] = [{"id": t["id"], "type": "function",
                                    "function": {"name": t["name"], "arguments": json.dumps(t["args"])}}
                                   for t in m["tool_calls"]]
            msgs.append(d)
        elif m["role"] == "tool":
            msgs.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    kw = {}
    if tools:
        kw["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                         "parameters": t["parameters"]}} for t in tools]
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    client = OpenAI(base_url=base_url, api_key=api_key) if base_url else OpenAI()
    r = client.chat.completions.create(model=model or OPENAI_MODEL, messages=msgs, **kw)
    msg = r.choices[0].message
    calls = [{"id": c.id, "name": c.function.name, "args": json.loads(c.function.arguments or "{}")}
             for c in (msg.tool_calls or [])]
    return {"content": msg.content or "", "tool_calls": calls,
            "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}}


def _groq(messages, tools, json_mode):
    if not os.getenv("GROQ_API_KEY"):
        raise LLMError("GROQ_API_KEY is not set (free key: https://console.groq.com)")
    return _openai(messages, tools, json_mode, base_url=GROQ_BASE_URL, api_key=os.environ["GROQ_API_KEY"], model=GROQ_MODEL)


def _gemini(messages, tools, json_mode):
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise LLMError("Missing package: pip install google-genai") from e
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents, pending = [], []          # pending = tool results waiting to be sent as ONE user turn
    for m in messages:
        if m["role"] == "tool":
            pending.append(types.Part.from_function_response(name=m["name"], response={"result": m["content"]}))
            continue
        if pending:
            contents.append(types.Content(role="user", parts=pending))
            pending = []
        if m["role"] == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["content"])]))
        elif m["role"] == "assistant":
            if m.get("gemini_content"):          # echo Gemini's own turn back (keeps its thought signatures)
                contents.append(types.Content.model_validate(m["gemini_content"]))
            else:
                parts = [types.Part.from_text(text=m["content"])] if m.get("content") else []
                parts += [types.Part(function_call=types.FunctionCall(name=t["name"], args=t["args"]))
                          for t in m.get("tool_calls", [])]
                contents.append(types.Content(role="model", parts=parts))
    if pending:
        contents.append(types.Content(role="user", parts=pending))
    cfg = {"system_instruction": system or None}
    if tools:
        cfg["tools"] = [types.Tool(function_declarations=[
            types.FunctionDeclaration(name=t["name"], description=t["description"],
                                      parameters_json_schema=t["parameters"]) for t in tools])]
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    r = genai.Client(api_key=_gemini_key()).models.generate_content(
        model=GEMINI_MODEL, contents=contents, config=types.GenerateContentConfig(**cfg))
    content = r.candidates[0].content
    text, calls = "", []
    for p in content.parts or []:
        if p.function_call:
            calls.append({"id": p.function_call.id or "call_" + uuid.uuid4().hex[:8],
                          "name": p.function_call.name, "args": dict(p.function_call.args or {})})
        elif p.text and not getattr(p, "thought", False):
            text += p.text
    u = r.usage_metadata
    return {"content": text, "tool_calls": calls,
            "usage": {"in": (u.prompt_token_count or 0) if u else 0,
                      "out": (u.candidates_token_count or 0) if u else 0},
            "gemini_content": content.model_dump(mode="json", exclude_none=True)}


def _cache_key(messages, tools, json_mode) -> str:
    plain = [{k: v for k, v in m.items() if k not in ("id", "tool_call_id", "gemini_content")} for m in messages]
    for m in plain:
        if m.get("tool_calls"):
            m["tool_calls"] = [{"name": t["name"], "args": t["args"]} for t in m["tool_calls"]]
    blob = json.dumps([plain, [t["name"] for t in tools or []], json_mode], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def call_llm(messages: list[dict], tools: list[dict] | None = None, json_mode: bool = False) -> dict:
    """Send messages (+ tool specs) to the model. Returns content, tool_calls, usage."""
    key = _cache_key(messages, tools, json_mode) if CACHE_ON else None
    cache = {}
    if CACHE_ON and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
        if key in cache:
            return {**cache[key], "latency_s": 0.0, "cached": True}
    adapter = {"groq": _groq, "openai": _openai, "gemini": _gemini, "mock": _mock_llm}[PROVIDER]
    last = None
    for attempt in range(3):
        try:
            t0 = time.time()
            out = adapter(messages, tools, json_mode)
            out["latency_s"] = round(time.time() - t0, 2)
            break
        except LLMError:
            raise
        except Exception as e:                         # rate limit, network blip, 5xx …
            last = e
            if attempt < 2:
                print(paint(f"   ⚠️  model call failed ({type(e).__name__}); retrying in {2 ** attempt}s …", GREY))
                time.sleep(2 ** attempt)
    else:
        raise LLMError(f"{PROVIDER} call failed 3 times: {last}")
    if CACHE_ON:
        cache[key] = out
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    return out


def model_label() -> str:
    return {"groq": f"Groq · {GROQ_MODEL}", "openai": f"OpenAI · {OPENAI_MODEL}", "gemini": f"Gemini · {GEMINI_MODEL}",
            "mock": "🧪 MOCK model (scripted rules, NOT a real LLM — rehearsal only)"}[PROVIDER]


def ensure_provider() -> None:
    """No silent fallback to the mock. With no key and no explicit LLM_PROVIDER, ask the person what to do."""
    global PROVIDER
    if os.getenv("LLM_PROVIDER") or PROVIDER != "mock":          # an explicit choice, or a real key was found
        return
    me = os.path.basename(__file__) if "__file__" in globals() else "this script"
    print(paint("\n⚠️  No API key found.", YELLOW) + " This demo talks to a real LLM, so it needs one before it starts.")
    if AUTO:                                                       # rehearsal mode never waits for a menu
        raise SystemExit("Rehearsal / non-interactive run: choose a provider on purpose.\n"
                         "  set GROQ_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY), or run with LLM_PROVIDER=mock to rehearse offline.")
    for _ in range(3):
        print("""
  1  I have a Groq key: paste it now (used for this run only, never saved to disk)
  2  I need a key: show me how to get one and set it, then I run the script again
  3  No key at all: rehearse offline with the MOCK model (scripted rules, NOT a real LLM)""")
        try:
            choice = input("\nYour choice [1/2/3] ➔ ").strip()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit("\nStopped: no provider chosen.")
        if choice == "1":
            import getpass
            key = getpass.getpass("Groq API key (typing is hidden) ➔ ").strip()
            if not key:
                print("Nothing entered.")
                continue
            if not key.startswith("gsk_"):
                print(paint("   (Groq keys usually start with gsk_ : if the first call fails, check the key.)", GREY))
            os.environ["GROQ_API_KEY"] = key                      # this process and the crash-scene child processes only
            os.environ["LLM_PROVIDER"] = "groq"
            PROVIDER = "groq"
            return
        if choice == "2":
            explain(f"""
                How to set up a key (about 2 minutes, free):
                  1. Open https://console.groq.com  →  sign in  →  API Keys  →  Create API Key  →  copy it (starts with gsk_).
                  2. Put it in an environment variable in the SAME terminal you run the demo from:
                       macOS / Linux :   export GROQ_API_KEY="gsk_..."
                       Windows (PowerShell):   $env:GROQ_API_KEY = "gsk_..."
                       Google Colab  :   add GROQ_API_KEY under Secrets, then  os.environ["GROQ_API_KEY"] = userdata.get("GROQ_API_KEY")
                  3. Run it again:   python {me}
                Prefer another provider? Set OPENAI_API_KEY or GEMINI_API_KEY instead (Gemini also needs: pip install google-genai).
                Never paste a key into the code or commit it to git.
            """)
            raise SystemExit(0)
        if choice == "3":
            os.environ["LLM_PROVIDER"] = "mock"                   # child processes inherit the explicit choice
            PROVIDER = "mock"
            return
        print("Please type 1, 2 or 3.")
    raise SystemExit("No valid choice: stopping. Set GROQ_API_KEY and run again.")
