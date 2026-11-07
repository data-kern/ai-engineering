# The same KernMart agent, on the OpenAI Agents SDK

**DataKern AI Engineering · Session 8.** In Session 7 you built the agent from an empty file with `requests`. Here the *framework* does the plumbing, so each step is about where the SDK lets you hang a control. The model is the same real model, the data is the same real SQLite database. Nothing is mocked or scripted in what you run.

## What is in this folder

| File | What it adds |
|---|---|
| `step01_agent_runner.py` | `Agent` + `Runner` + `@function_tool`: Session 7's steps 03-05 in about 20 lines. Still trusts everything |
| `step02_context_session.py` | `context=` (who is asking is **our** fact, hidden from the model) and `SQLiteSession` (memory is a table we own) |
| `step03_guardrails.py` | four guardrails: input, tool input (**the rules for money**), tool output (untrusted text), output (claims vs the ledger). `--without` switches each off |
| `step04_approval.py` | `needs_approval`: the run **pauses**, is saved as JSON, and resumes in a **new process** |
| `step05_handoffs_tracing.py` | `handoffs`: Triage (reads) → Refund specialist (the dangerous tool). Traces in Phoenix |
| `kernmart_tools.py` | the business logic as plain Python: tools, rules, idempotent ledger write |
| `test_sdk_controls.py` | 17 checks, no LLM: each control tested ON (it blocks) and OFF (it goes through) |
| `llm.py`, `show.py`, `db.py` | plumbing: model + tracing setup, coloured printing, the sample database. Not part of the agent |

Run the steps in order. Every step file starts with **Add / Issue / See / Notice / Next**: read it first.

## Start here: the plain versions

Each step also has a `_plain` twin. It is the same agent with nothing around it: no `show.py`, no coloured loop output, no PREDICT / OBSERVE pauses. You get a normal chat with the agent, and the file shows how little code the SDK needs. Read these first; use the other files when you want to *watch* the loop run.

| File | What it adds | Try (the file lists more) |
|---|---|---|
| `step01_agent_runner_plain.py` | tools + `Agent` + `Runner` + `SQLiteSession`: a chat agent in one file | "Show me order KM-60001" works for the wrong customer |
| `step02_context_session_plain.py` | login, and `context=`: who is asking is our fact, hidden from the model | the same question returns "not found" |
| `step03_guardrails_plain.py` | the four guardrails: speed bump, rules for money, carrier-note cleanup, claims vs the ledger | "Refund me EUR 500" is refused |
| `step04_approval_plain.py` | `needs_approval`: EUR 89 pauses and **you** approve or reject in the terminal | |
| `step05_handoffs_tracing_plain.py` | Triage (read only) hands refunds to a Refund specialist | one line shows who answered |

Each plain file lists the problem in the last step, the fix, the lines marked `NEW`, and the messages to type. Steps 01-04 are complete files. Step 05 imports step 04's tools and guardrails, so only the handoff is new on the page.

```bash
python db.py reset
export GROQ_API_KEY="gsk_..."
python step01_agent_runner_plain.py          # then step02, 03, 04, 05
```

The plain steps keep their conversations in `chat_sessions.db` (type `/new` to start over). The two plain-step limits that matter: the approval is asked in the same process (the original `step04_approval.py` shows pause, save and resume in a new process), and tracing is off (the original step 05 sends it to Phoenix).

## Setup (once)

Python 3.10+ and a free Groq key (https://console.groq.com).

```bash
cd session_08/agents_sdk_demo
python3 -m venv .venv && source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."                              # Windows: $env:GROQ_API_KEY = "gsk_..."
python db.py reset
python step01_agent_runner.py
```

Default model `openai/gpt-oss-120b` on Groq. Override with `LLM_MODEL`; any OpenAI-compatible endpoint with tool calling works through `LLM_BASE_URL` and `LLM_API_KEY`. `python db.py reset` resets the data before each scene; `python db.py ledger` shows the refunds and escalations the agent wrote. `NO_COLOR=1` turns colour off.

Each step runs a few **scenes** (a real customer message sent to the real model, with a PREDICT before and an OBSERVE after). Add `--chat` to any of steps 01-05 to try your own questions instead.

## The SDK, mapped to what you built in Session 7

| You built (Session 7) | The SDK gives you | Step |
|---|---|---|
| tool JSON schema, written by hand | `@function_tool`: schema from signature + docstring | 01 |
| the `while` loop | `Runner.run()`; `max_turns` is the step budget | 01 |
| `messages` list | `session=SQLiteSession(...)` | 02 |
| `CUSTOMER_ID` global set by our code | `context=` + `ctx: RunContextWrapper` | 02 |
| `rules` control (EUR 500 on an EUR 89 order) | tool input guardrail | 03 |
| `guards` control (carrier note, false claim) | tool output guardrail, output guardrail | 03 |
| `approval` control, `runs` table | `needs_approval=`, `RunState` | 04 |
| router + specialist | `handoffs=` | 05 |
| hand-written Phoenix spans (~40 lines) | built-in tracing + `OpenAIAgentsInstrumentor` | 05 |

What the SDK does **not** give you, so you still write it: the rules for money themselves, the idempotency key, the login, the approval inbox, the evals. The framework removes typing, not responsibility.

## Things to try

```bash
python db.py reset
python step03_guardrails.py --without rules,fence,claims,speedbump     # everything off: EUR 500 goes out
python db.py ledger
python db.py reset && python step03_guardrails.py                      # everything on: the same message is refused
python step04_approval.py                                              # pauses at EUR 89 and saves pending_run.json
python step04_approval.py --resume                                     # a NEW process: approve, or reject with feedback
python test_sdk_controls.py                                            # 17 checks, no LLM
```

## See every step in Phoenix

Phoenix is optional. In a second terminal run `phoenix serve` and open http://localhost:6006; the project `kernmart-agents-sdk` fills up as you run the steps. One trace per run: agent → model calls → tools → handoffs, with the input and output guardrail verdicts. Point Phoenix elsewhere with `PHOENIX_COLLECTOR_ENDPOINT`.

The SDK exports its trace to the OpenAI dashboard by default. `llm.start_tracing()` replaces that exporter with Phoenix's, so nothing leaves your machine for a service you have no key for.

## Honest limits

- A customer id typed at a prompt is a *claim*, not a login (production: password, SSO, one-time code). `kernmart_tools.login` stands in for that.
- The SDK's approval stops the run and gives you the state. *Who* is asked, how, and for how long is your system (a queue, Slack, a ticket). Here `input()` stands in.
- Output guardrails see the final reply only. `claims_match_ledger` is a regex speed bump, not a proof; the ledger and the rules are the real walls.
- Models vary run to run. A scene may take a different path from the one described in a step header: that is the point of the evals slide, not a bug.
