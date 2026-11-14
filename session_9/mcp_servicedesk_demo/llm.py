"""Plumbing, not part of the agent: which model the SDK talks to, where the traces go, how to print tool calls.

Same real model as Sessions 7 and 8: the Agents SDK speaks the OpenAI API, and Groq speaks the same
Chat Completions dialect, so one client with a different base URL is all it takes.

    GROQ_API_KEY   (or LLM_API_KEY)      your key, free at https://console.groq.com
    LLM_MODEL      default openai/gpt-oss-120b
    LLM_BASE_URL   default https://api.groq.com/openai/v1   (any OpenAI-compatible endpoint with tool calling)
"""
import json
import os
import sys

from agents import ModelSettings, OpenAIChatCompletionsModel
from agents.tracing import set_trace_processors
from openai import AsyncOpenAI

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")      # empty = no tracing
PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT_NAME", "kernmart-servicedesk")

SETTINGS = ModelSettings(temperature=0)    # the same question should take the same path


def require_key():
    if not API_KEY:
        sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")


def model():
    """The model object every Agent gets: `Agent(model=llm.model())`."""
    require_key()
    return OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY))


def start_tracing():
    """Send the SDK's built-in trace to Phoenix. Returns one line for the start-up banner.

    The SDK uploads traces to the OpenAI dashboard by default. We have no OpenAI key, so we replace
    that exporter and add Phoenix's. The MCP instrumentor does one more thing: it passes the trace
    id to the MCP server with every tool call, so the server's work shows up INSIDE the agent's trace.
    """
    set_trace_processors([])
    if not PHOENIX_ENDPOINT:
        return "tracing off. To see every step, start Phoenix and set PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006"
    from openinference.instrumentation.mcp import MCPInstrumentor
    from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
    from phoenix.otel import register

    provider = register(project_name=PHOENIX_PROJECT, endpoint=PHOENIX_ENDPOINT.rstrip("/") + "/v1/traces",
                        batch=True, verbose=False, set_global_tracer_provider=True, auto_instrument=False)
    OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)
    MCPInstrumentor().instrument(tracer_provider=provider)
    return f"tracing to {PHOENIX_ENDPOINT}  project: {PHOENIX_PROJECT}"


def tool_calls_made(result):
    """What the agent actually DID in this run: [(tool name, arguments), ...] in order."""
    calls = []
    for item in result.new_items:
        if item.type == "tool_call_item":
            calls.append((item.raw_item.name, json.loads(item.raw_item.arguments or "{}")))
    return calls


def print_tool_calls(result):
    for name, arguments in tool_calls_made(result):
        shown = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
        print(f"   \033[36m-> {name}({shown})\033[0m")
