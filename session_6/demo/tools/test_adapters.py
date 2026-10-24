#!/usr/bin/env python3
"""Offline checks of the Groq / OpenAI / Gemini adapters (no network, no keys): fakes stand in for the SDK clients.
Run:  python tools/test_adapters.py"""
import importlib.util, json, os, sys, types
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DEMO_AUTO"] = "1"; os.environ["NO_COLOR"] = "1"


def load(name):
    spec = importlib.util.spec_from_file_location("m_" + name[:2], os.path.join(ROOT, name))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


m = load("07_full_agent.py")
msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "get_order", "args": {"order_id": "KM-1", "why": "x"}}]},
        {"role": "tool", "tool_call_id": "c1", "name": "get_order", "content": '{"ok": 1}'}]
tools = m.tool_specs(["get_order", "issue_refund"])

# ── OpenAI ──
seen = {}
class FakeOpenAI:
    class chat:
        class completions:
            @staticmethod
            def create(**kw):
                seen.update(kw)
                tc = types.SimpleNamespace(id="t9", function=types.SimpleNamespace(name="get_order", arguments='{"order_id":"KM-2","why":"w"}'))
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=None, tool_calls=[tc]))],
                                             usage=types.SimpleNamespace(prompt_tokens=11, completion_tokens=3))
    def __init__(self, *a, **k): pass
with mock.patch.dict(sys.modules, {"openai": types.SimpleNamespace(OpenAI=FakeOpenAI)}):
    out = m._openai(msgs, tools, False)
assert out["tool_calls"] == [{"id": "t9", "name": "get_order", "args": {"order_id": "KM-2", "why": "w"}}], out
assert out["usage"] == {"in": 11, "out": 3}
assert seen["messages"][2]["tool_calls"][0]["function"]["arguments"] == json.dumps({"order_id": "KM-1", "why": "x"})
assert seen["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": '{"ok": 1}'}
assert seen["tools"][0]["function"]["name"] == "get_order" and "response_format" not in seen
with mock.patch.dict(sys.modules, {"openai": types.SimpleNamespace(OpenAI=FakeOpenAI)}):
    seen.clear()
    m._openai(msgs[:2], None, True)
assert seen["response_format"] == {"type": "json_object"} and "tools" not in seen
print("OpenAI adapter: OK")

# ── Groq = the OpenAI protocol pointed at Groq's URL, with its own key and model ──
made = {}
class FakeOpenAIKw(FakeOpenAI):
    def __init__(self, *a, **k): made.update(k)
os.environ["GROQ_API_KEY"] = "gsk_test"
with mock.patch.dict(sys.modules, {"openai": types.SimpleNamespace(OpenAI=FakeOpenAIKw)}):
    seen.clear()
    out = m._groq(msgs, tools, False)
assert made == {"base_url": m.GROQ_BASE_URL, "api_key": "gsk_test"}, made
assert seen["model"] == m.GROQ_MODEL and out["tool_calls"][0]["name"] == "get_order"
del os.environ["GROQ_API_KEY"]
try:
    m._groq(msgs, tools, False); raise SystemExit("expected LLMError without GROQ_API_KEY")
except m.LLMError:
    pass
print("Groq adapter: OK")

# ── Gemini (real SDK types, fake network) ──
from google.genai import types as gt
import google.genai as genai
captured = {}
class FakeModels:
    def generate_content(self, model, contents, config):
        captured.update(model=model, contents=contents, config=config)
        part = gt.Part(function_call=gt.FunctionCall(name="get_order", args={"order_id": "KM-3", "why": "w"}), thought_signature=b"sig")
        return types.SimpleNamespace(candidates=[types.SimpleNamespace(content=gt.Content(role="model", parts=[part]))],
                                     usage_metadata=types.SimpleNamespace(prompt_token_count=20, candidates_token_count=5))
class FakeClient:
    def __init__(self, **k): self.models = FakeModels()
with mock.patch.object(genai, "Client", FakeClient):
    out = m._gemini(msgs, tools, False)
assert out["tool_calls"][0]["name"] == "get_order" and out["tool_calls"][0]["args"]["order_id"] == "KM-3"
assert out["usage"] == {"in": 20, "out": 5}
assert [c.role for c in captured["contents"]] == ["user", "model", "user"]       # tool result goes back as a user turn
assert captured["contents"][2].parts[0].function_response.name == "get_order"
# echo the model's own turn (with thought signature) back on the next call
assistant = {"role": "assistant", "content": "", "tool_calls": out["tool_calls"], "gemini_content": out["gemini_content"]}
msgs2 = msgs[:2] + [assistant, {"role": "tool", "tool_call_id": out["tool_calls"][0]["id"], "name": "get_order", "content": "{}"}]
with mock.patch.object(genai, "Client", FakeClient):
    m._gemini(msgs2, tools, True)
assert captured["contents"][1].parts[0].thought_signature == b"sig", "thought signature lost"
assert captured["config"].response_mime_type == "application/json"
print("Gemini adapter: OK")

# ── cache key ignores ids ──
a = m._cache_key(msgs, tools, False)
msgs_b = json.loads(json.dumps(msgs)); msgs_b[2]["tool_calls"][0]["id"] = "zzz"; msgs_b[3]["tool_call_id"] = "zzz"
assert a == m._cache_key(msgs_b, tools, False)
print("Cache key: OK")
