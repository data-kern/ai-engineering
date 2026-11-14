"""The agent as a service: one HTTP endpoint in front of the agent from step 04.

    chat_ui  --HTTP-->  agent_api (this file)  --MCP over HTTP-->  mcp_server  -->  PostgreSQL

What lives HERE: the model, the instructions, the conversation memory.
What does NOT live here: any tool code, any database credential, any business rule. Those are the MCP server's.

The API keeps nothing in its own memory between requests, so Kubernetes can run as many replicas as
it likes: the conversation is a table in PostgreSQL (SQLAlchemySession), the tools are on the MCP server.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from agents import Agent, Runner
from agents.extensions.memory import SQLAlchemySession
from agents.mcp import MCPServerStreamableHttp
from fastapi import FastAPI, HTTPException
from openinference.instrumentation import using_attributes
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine

import llm
from agent_instructions import INSTRUCTIONS

MCP_URL = os.getenv("MCP_URL", "http://localhost:8030/mcp")
SESSION_DATABASE_URL = os.getenv("SESSION_DATABASE_URL", "postgresql+asyncpg://servicedesk:servicedesk@localhost:5433/servicedesk")
RUN_TIMEOUT_SECONDS = 90

log = logging.getLogger("kernmart.agent_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not llm.API_KEY:
        # Fail loudly at start-up. A pod that crash-loops with this message is easier to fix than one that
        # looks healthy and fails every chat.
        raise RuntimeError("No model API key. Set GROQ_API_KEY (or LLM_API_KEY).")
    log.info("model: %s | MCP server: %s | %s", llm.MODEL_NAME, MCP_URL, llm.start_tracing())
    app.state.session_engine = create_async_engine(SESSION_DATABASE_URL)       # one connection pool, shared
    yield
    await app.state.session_engine.dispose()


def _is_health_probe(scope) -> bool:
    return scope.get("path") == "/api/v1/health"


# FastAPI (0.162+) records its own OpenTelemetry spans. Once Phoenix tracing is on, they would arrive in
# Phoenix too, including one for every health probe (Docker and Kubernetes ask every few seconds).
# Keep one span per real request (it becomes the root of the chat's trace); drop the probes and the
# per-step child spans, so Phoenix shows what the agent did and not how FastAPI works inside.
app = FastAPI(
    title="KernMart IT service desk agent",
    lifespan=lifespan,
    telemetry={"exclude": _is_health_probe, "operation_spans": False},
)


class ChatRequest(BaseModel):
    employee_id: str = Field(pattern=r"^[ES]-\d{4}$", examples=["E-1001"])
    conversation_id: str = Field(min_length=1, max_length=64, examples=["chat-1"])
    message: str = Field(min_length=1, max_length=2000)


class ToolCall(BaseModel):
    name: str
    arguments: dict


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCall]
    escalated: bool


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "model": llm.MODEL_NAME}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # How long it took, whether it failed, which tools ran: all of that is in the Phoenix trace for this message.
    try:
        result = await run_agent(request)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="The assistant took too long. Please try again.")
    except Exception:
        log.exception("chat failed for %s", request.employee_id)
        raise HTTPException(status_code=502, detail="The assistant is unavailable right now. Please try again, or call the service desk.")

    tool_calls = [ToolCall(name=name, arguments=arguments) for name, arguments in llm.tool_calls_made(result)]
    escalated = any(call.name == "escalate_to_human" for call in tool_calls)
    return ChatResponse(reply=result.final_output, tool_calls=tool_calls, escalated=escalated)


async def run_agent(request: ChatRequest):
    """The same few lines as step 04, for one request."""
    # Who is asking goes to the MCP server as a header, once per connection. The model never sees it.
    mcp_server = MCPServerStreamableHttp(
        params={"url": MCP_URL, "headers": {"X-Employee-Id": request.employee_id}},
        cache_tools_list=True,
        client_session_timeout_seconds=30,
    )
    memory = SQLAlchemySession(f"{request.employee_id}:{request.conversation_id}",
                               engine=app.state.session_engine, create_tables=True)

    async with mcp_server:
        agent = Agent(
            name="KernMart IT service desk",
            instructions=INSTRUCTIONS,
            mcp_servers=[mcp_server],
            model=llm.model(),
            model_settings=llm.SETTINGS,
        )
        # These two labels make Phoenix group the traces by conversation and by employee.
        with using_attributes(session_id=request.conversation_id, user_id=request.employee_id):
            return await asyncio.wait_for(
                Runner.run(agent, request.message, session=memory, max_turns=12),
                timeout=RUN_TIMEOUT_SECONDS,
            )
