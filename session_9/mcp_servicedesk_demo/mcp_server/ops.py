"""Operations plumbing for the MCP server: who is asking, audit log, traces.

This is NOT the tools. The tools are in server.py. This file is the part an enterprise adds around
them, once, so every tool gets it for free:

    @governed          wrap a tool so every call is timed, audited and traced (the trace goes to Phoenix)
    who_is_asking(ctx) find out which employee this request belongs to
"""
import functools
import json
import logging
import os
import time

import anyio
from mcp.server.fastmcp import Context
from opentelemetry import trace

from servicedesk_core import db
from servicedesk_core.desk import DeskError

tracer = trace.get_tracer("kernmart.mcp_server")
log = logging.getLogger("kernmart.mcp_server")


def start_tracing():
    """Send traces to Phoenix if it is configured. Phoenix is our only window into what the agent and the
    server did: every tool call is a span, with its outcome, its duration and who asked.

    The MCP instrumentor picks up the trace that the agent started, so the agent's span and this
    server's span end up in ONE trace."""
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        return "tracing off (PHOENIX_COLLECTOR_ENDPOINT not set)"
    from openinference.instrumentation.mcp import MCPInstrumentor
    from phoenix.otel import register

    provider = register(project_name=os.getenv("PHOENIX_PROJECT_NAME", "kernmart-servicedesk"),
                        endpoint=endpoint.rstrip("/") + "/v1/traces", batch=True, verbose=False,
                        set_global_tracer_provider=True, auto_instrument=False)
    MCPInstrumentor().instrument(tracer_provider=provider)
    return f"tracing to {endpoint}"


# ---- identity -------------------------------------------------------------------------------
def who_is_asking(ctx: Context) -> str:
    """The employee this request is for.

    Over HTTP the agent service sends it as a header on the MCP connection. Over stdio (a program
    started on your laptop) it comes from the EMPLOYEE_ID environment variable.

    DEMO LIMIT: nothing proves the header is true. Anyone who can reach this port could send
    'X-Employee-Id: E-1003'. In production this is a signed token from your identity provider
    that this server verifies (slide 13). The important part is already right: the employee id is
    NEVER a tool argument, so the model cannot choose whose account it acts on.
    """
    request = ctx.request_context.request
    employee_id = request.headers.get("x-employee-id") if request is not None else os.getenv("EMPLOYEE_ID")
    if not employee_id:
        raise DeskError("Unknown requester: no employee id was sent with this request.")
    return employee_id


# ---- the wrapper every tool goes through ------------------------------------------------
def governed(tool_function):
    """Decorator. Runs the tool in a worker thread (our database code is blocking), then records
    what happened: a trace span for Phoenix and an audit row in PostgreSQL.

    The span carries what a dashboard would otherwise count. In Phoenix, open the project, click the
    Filter box above the trace table, and type one of these:
        tool.outcome == 'refused'                      the rules said no (a normal answer)
        tool.outcome == 'error'                        a bug or an outage
        servicedesk.event == 'ticket_resolved_by_agent'
        servicedesk.event == 'ticket_escalated'
        employee.id == 'E-1003'                        everything one employee's chats caused
    The span's own start and end time give the tool's duration.
    """
    tool_name = tool_function.__name__

    @functools.wraps(tool_function)          # keeps the signature, so FastMCP still builds the right schema
    async def wrapper(*args, **kwargs):
        ctx = kwargs.get("ctx")
        employee_id = _safe_employee_id(ctx)
        arguments = {name: value for name, value in kwargs.items() if name != "ctx"}
        started = time.perf_counter()
        outcome, detail, result = "ok", "", None

        with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("employee.id", employee_id or "unknown")
            try:
                result = await anyio.to_thread.run_sync(functools.partial(tool_function, *args, **kwargs))
                if isinstance(result, dict) and result.get("done") is False:
                    outcome, detail = "refused", result.get("reason", "")
                event = _business_event(tool_name, arguments, result)
                if event:
                    span.set_attribute("servicedesk.event", event)
            except DeskError as problem:
                outcome, detail = "error", str(problem)
                raise
            except Exception as problem:     # a bug or an outage: record it, then let FastMCP report it
                outcome, detail = "error", f"{type(problem).__name__}: {problem}"
                raise
            finally:
                seconds = time.perf_counter() - started
                span.set_attribute("tool.outcome", outcome)
                _write_audit_row(employee_id, tool_name, arguments, outcome, detail, seconds)

        return result

    return wrapper


def _safe_employee_id(ctx):
    if ctx is None:
        return None
    try:
        return who_is_asking(ctx)
    except DeskError:
        return None


def _write_audit_row(employee_id, tool_name, arguments, outcome, detail, seconds):
    try:
        db.execute(
            "INSERT INTO audit_log (employee_id, tool, arguments, outcome, detail, duration_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (employee_id, tool_name, json.dumps(arguments, default=str), outcome, detail, int(seconds * 1000)),
        )
    except Exception:
        # An audit outage must not break the tool, but it must not be silent either.
        log.exception("could not write the audit row for %s", tool_name)


def _business_event(tool_name, arguments, result):
    """The thing the service-desk manager cares about (not the platform team), as a label on the span.
    Returns None when the call was not one of those events."""
    if not isinstance(result, dict) or result.get("done") is not True:
        return None
    if tool_name == "create_ticket":
        return "ticket_created"
    if tool_name == "close_ticket_as_resolved":
        return "ticket_resolved_by_agent"
    if tool_name == "escalate_to_human" and not result.get("already_escalated"):
        return "ticket_escalated"
    return None
