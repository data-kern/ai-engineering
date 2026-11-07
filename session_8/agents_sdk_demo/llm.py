"""Plumbing, not part of the agent: which model the SDK talks to, and where the traces go.

The Agents SDK speaks the OpenAI API. Groq (and many others) speak the same Chat Completions dialect, so we point
the SDK at Groq with one client and wrap it in `OpenAIChatCompletionsModel`. Same real model as Session 7.

    GROQ_API_KEY   (or LLM_API_KEY)      your key, free at https://console.groq.com
    LLM_MODEL      default openai/gpt-oss-120b
    LLM_BASE_URL   default https://api.groq.com/openai/v1   (any OpenAI-compatible endpoint with tool calling)
"""
import os
import sys

import requests
from agents import ModelSettings, OpenAIChatCompletionsModel
from agents.tracing import set_trace_processors
from openai import AsyncOpenAI

API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
PHOENIX_URL = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip("/")
PROJECT = os.getenv("PHOENIX_PROJECT_NAME", "kernmart-agents-sdk")

SETTINGS = ModelSettings(temperature=0)       # same as Session 7: the same question should take the same path


def require_key():
    if not API_KEY:
        sys.exit("Set GROQ_API_KEY first (free key: https://console.groq.com)")


def model():
    """The model object every Agent gets. `Agent(model=llm.model())`."""
    require_key()
    return OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY))


def start_tracing():
    """Send the SDK's built-in trace to Phoenix. Returns a one-line status for the banner.

    The SDK records every agent run, model call, tool call, handoff and guardrail as a trace by default, and ships it
    to the OpenAI dashboard. We have no OpenAI key, so we replace that exporter (set_trace_processors([])) and add
    Phoenix's. If Phoenix is not running, the agent works the same, just untraced."""
    set_trace_processors([])
    try:
        requests.get(PHOENIX_URL + "/healthz", timeout=1)                    # raises if nothing is listening
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
        from phoenix.otel import register
    except Exception:
        return f"Phoenix: not traced. To see every step:  pip install -r requirements.txt  and  phoenix serve  ({PHOENIX_URL})"
    provider = register(project_name=PROJECT, endpoint=PHOENIX_URL + "/v1/traces", batch=False, verbose=False,
                        set_global_tracer_provider=False, auto_instrument=False)
    OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)
    return f"Phoenix: tracing to {PHOENIX_URL}   project: {PROJECT}"
