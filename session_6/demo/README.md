# KernMart Support Agent — a seven-script live demo (plain Python, no frameworks)

**DataKern AI Engineering · Session 6 lab (the hands-on follow-up to the agents slides)**

A customer-support agent for a fictional online retailer (orders, late deliveries, refunds), built **one capability per script**
so students can watch each agent concept appear, break, and get fixed. Script 07 connects everything into the finished agent.
The next session maps the same pieces onto LangGraph and the OpenAI Agents SDK.

**Teaching aid:** open [`../animations/kernmart_agent_flow.html`](../animations/kernmart_agent_flow.html) in a browser.
It is a swimlane flow of one customer request (Customer · Model · Code · Human · Data) with every box tagged by the script that adds it. Use *Previous / Next / Play* (or the ← → keys) to walk through it. Two scenarios: a refund that takes several laps of the agent loop and then answers, and a run that never finishes and is cut off by the limit check.

## Run the scripts in this order

| # | Script | Adds | The moment that lands |
|---|---|---|---|
| 01 | `01_loop_and_tools.py` | agent loop, tools, router, stop conditions (read-only) | the model *asks*, code *acts*; it recovers from a wrong order id |
| 02 | `02_state_and_resume.py` | write tools, SQLite state, idempotency | kill the process mid-refund: **double refund** → fixed with one idempotency key |
| 03 | `03_human_approval.py` | risk-tiered approval gate | reject with feedback → the agent re-plans (replacement instead of refund) |
| 04 | `04_guardrails.py` | input/output guards, policy engine | prompt injection **works**, filters get bypassed, code policy holds |
| 05 | `05_memory.py` | context trimming, long-term memory, erasure | "two weeks later" it remembers; memory poisoning rejected |
| 06 | `06_observability_and_eval.py` | traces (Phoenix), audit log, trajectory evals | a harmless-looking prompt tweak turns the eval red |
| 07 | `07_full_agent.py` | **nothing new: connects 01–06** | one request through every layer, then the finished agent under attack, then the scoreboard |

Each script contains everything from the one before it, plus its new layer, so every file runs on its own (copy it anywhere).
Each ends with a **clean reference** printout of the agent without the teaching, and tells you which script comes next.
Console colours: 🧠 orange = model decided · ⚙️ teal = code decided · 🙋 yellow = human decided · 🛡️ red = blocked.

How the scripts map to the slides (agents deck, slides 11–16): tools and loop (12, 13) → **01** · state and checkpoints (14) → **02** ·
human-in-the-loop (15) → **03** · guardrails (15) → **04** · long-term memory (14) → **05** · traces and evals (16) → **06** · the full skeleton (11) → **07**.
Memory comes after guardrails on purpose: memory is a write path into the future, so it needs the guards first.

## Setup (once)

You need **Python 3.10 or newer** and a free **Groq API key** (https://console.groq.com, the same provider as Sessions 4–5). No key yet? The script stops and asks: paste a key for this run, see how to get and set one, or (only if you choose it) rehearse with an offline mock model, which is *not* a real LLM.

**macOS / Linux**
```bash
cd session_06/demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
python 01_loop_and_tools.py
```

**Windows (PowerShell, VS Code terminal)**
```powershell
cd session_06\demo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GROQ_API_KEY = "gsk_..."
python 01_loop_and_tools.py
```

**Google Colab:** upload the files, `!pip install -q openai`, put the key in *Secrets* and `os.environ["GROQ_API_KEY"] = userdata.get("GROQ_API_KEY")`, then `%run 01_loop_and_tools.py` (not `!python`: it cannot answer ENTER prompts).

**Providers.** Auto-picked in this order: `GROQ_API_KEY` → Groq, `OPENAI_API_KEY` → OpenAI, `GEMINI_API_KEY` → Gemini. If none is set, the script asks what to do and never silently falls back to the mock. Force one with `LLM_PROVIDER=groq|openai|gemini|mock`.
Models: `GROQ_MODEL` (default `openai/gpt-oss-120b`, served by Groq), `OPENAI_MODEL`, `GEMINI_MODEL`. For Gemini also run `pip install google-genai`.
Use a model that supports **tool calling**: the small `llama-3.1-8b-instant` from Sessions 4–5 is a weak choice for an agent loop.

> **Before you teach: run every script once with a real key.** I could only test offline (mock model and fake SDK clients), never with a live API. Model names change often: if one is rejected, set `GROQ_MODEL` (or the others) to a current tool-calling model. The default model names are the first thing to verify.

### Open while it runs
* **SQLite viewer**: VS Code extension "SQLite Viewer", or DB Browser for SQLite. Files appear in `demo_data/`: `kernmart.db` (the business: `orders`, `shipment_events`, **`ledger`**) and `agent_state.db` (the agent: `runs`, `audit`, `approvals`, `memory`). Refresh the table after each scene.
* **Phoenix (scripts 06 and 07)**: open a *second* terminal, activate the same venv, then `pip install arize-phoenix` and `phoenix serve`. Open http://localhost:6006 → project `kernmart-agent`. Start it **before** running 06. Without Phoenix the scripts print the same span tree in the terminal.

## How to run a script in class

Scripts pause between steps: **ENTER** = continue, **Ctrl+C** = stop (nothing breaks). Every scene asks a 🔮 PREDICT question first: ask it out loud and take 2–3 answers before pressing ENTER. That is where students engage.
Pick scenes with `--scenes 1,3,4` (or `DEMO_SCENES=1,3,4`). Each file has more scenes than a slot allows; the rest are for students to replay.
`python 01_loop_and_tools.py --help` prints the header of any script (goal, what is new, how to run).

**Scenes that stop for YOUR decision** (type `a` approve · `e` edit the amount · `r` reject with feedback, or just ENTER to approve): script 03 scenes 3, 4 and 5 (scene 5 is answered for you) · script 05 scenes 3 and 5 · script 06 scene 2 · script 07 scene 3.

**Scenes that need an earlier scene in the same run** (each script wipes the data when it starts, so run them together): 05 scene 3 needs scene 2 (the memory it recalls) · 06 scene 3 needs scene 2 (the audit rows it shows) · 07 scene 4 needs scene 3, and scene 3 needs scene 2.

## 90-minute run of show

The times are **estimates, not measured**: rehearse once with your model and adjust.

| Min | Script · `--scenes` | What students see | Say this |
|---|---|---|---|
| 0–5 | flow diagram | one request, both scenarios, in the browser | "The model only asks. Code and humans decide what runs." |
| 5–15 | `01_loop_and_tools.py --scenes 1,2,3,4` | tool schema · router · loop · wrong order id | "Watch the colours: who decided each line?" |
| 15–27 | `02_state_and_resume.py --scenes 2,3,4` | agent pays a refund · crash, naive retry · crash, idempotent | "It works, and nobody is watching. Now kill it at the worst moment." |
| 27–37 | `03_human_approval.py --scenes 1,3,5` | risk tiers · **you are the reviewer** · crash after approval | First time, type `r` then `Please offer a replacement instead`. |
| 37–51 | `04_guardrails.py --scenes 2,3,4,5` | attack with guards off · filters bypassed · policy holds · output guard | "Filters are speed bumps. Make a fooled model unable to do damage." |
| 51–61 | `05_memory.py --scenes 2,3,4` | learns a preference · adapts · memory poisoning | Scene 3 needs scene 2 first. |
| 61–71 | `06_observability_and_eval.py --scenes 2,4,5` | one traced run · evals green · prompt tweak → red | "Safety nets hide regressions; evals expose them." |
| 71–88 | `07_full_agent.py` (all scenes) | every layer on one request · trace + audit · attack · scoreboard | "This is the whole agent. You built every box." |
| 88–90 | diagram again | frameworks next session | "Frameworks save typing, not thinking." |

**30-minute version** (if you only get a slot inside a slide session): 01 `--scenes 1,3,4` · 02 `--scenes 2,3,4` · 03 `--scenes 3,5` · 04 `--scenes 2,3,4` · 05 `--scenes 2,3,4` · 06 `--scenes 2,4,5`, about 5 minutes each.

## Things that can go wrong live (and what to do)
* **A real model refuses the injection (script 04 scene 2/3).** Good news for the model, bad for the demo. Say so honestly: "this one resisted today; nothing guarantees it tomorrow, so we don't depend on it", then run that scene with `LLM_PROVIDER=mock` (the mock is deliberately naive) or a smaller model via `GROQ_MODEL`. Don't present the mock as a real model: the banner says what it is.
* **Rate limits / flaky answers.** Record once, replay live: run the whole show once with `LLM_CACHE=on` and your real key. In class keep `LLM_CACHE=on` and identical answers are replayed instantly (misses fall through to the live model). Cache file: `demo_data/llm_cache.json`.
* **Model skips a step or calls tools in a different order.** The loop handles several tool calls per turn. A different path is a teaching moment ("nobody scripted this"), but the PREDICT answers assume the typical path, so rehearse with your model.
* **Reset everything:** delete `demo_data/`. Each script also resets the data when it starts.
* **Offline rehearsal:** `DEMO_AUTO=1 LLM_PROVIDER=mock python 03_human_approval.py` runs every pause and approval with scripted answers (`DEMO_ANSWERS="reject:use a replacement;approve"`; unanswered approvals default to approve).

## Design choices worth defending (and honest limits)
* **Customer identity comes from the session, never from the model**; tools enforce ownership. There is no "refund to another account" parameter. Least privilege beats clever prompts.
* **Eligibility rules live in code** (`check_refund_eligibility`), not in the prompt.
* **Write-ahead checkpoints + idempotency keys** make crash/resume safe. The crash is simulated with `os._exit` in a child process, which is a faithful `kill -9`.
* **"Why" is a stated rationale**, forced as a tool argument for audit and debugging. It is not the model's real internal reasoning; say so.
* **Simplified on purpose:** regex scan (bypassable by design: that's script 04 scene 3), keyword router rules inside the mock, a daily refund cap using wall-clock date, SQLite (single writer; production: Postgres + a queue), no authentication layer, `search_policy` is a lookup not RAG (you covered RAG already).
* **Not covered:** multi-agent patterns, long-running async approvals (the gate blocks on `input()`; in production it's a ticket + webhook), cost dashboards, red-teaming at scale.

## Maintaining the scripts
The seven scripts are **generated** from `tools/parts/*.py` (shared code with `#@if v>=N` blocks) by `python tools/build_versions.py`, so a fix lands in every script. Edit the parts, rebuild, never edit the numbered files directly.
`python tools/test_invariants.py` (8 safety invariants, mock model) and `python tools/test_adapters.py` (Groq / OpenAI / Gemini message translation with fake clients) should stay green.

## Next session: what the frameworks replace
agent loop → graph nodes/edges or a Runner · tool registry → `@tool` / function tools · router → conditional edges / handoffs ·
`runs` table → checkpointer · approval gate → interrupt / tool approvals · guards → built-in guardrails (your policy code stays) ·
`memory` table → store / sessions · spans + audit → built-in tracing (Phoenix, Langfuse, LangSmith). Check current docs for exact names.
