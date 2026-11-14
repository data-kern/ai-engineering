# The KernMart IT service desk agent, built on MCP

**DataKern AI Engineering · Session 9.** An agent that answers IT requests ("I'm locked out", "my VPN drops", "I need Figma"), solves what it safely can, and **escalates to a human** when it cannot. Its tools live in an **MCP server**, not inside the agent. You build that up in four steps on your laptop, run the agent as a FastAPI service, then run the whole thing as a real system: Docker Compose, then Kubernetes. A chat UI for employees, a staff console for the humans, an audit log, and **Arize Phoenix** to see exactly what the agent and the server did.

Everything you run is real: a real model, a real PostgreSQL, a real SMTP server that receives the alert emails. Nothing is scripted.

## What is in this folder

| File / folder | What it is |
|---|---|
| `step01_without_mcp.py` | the agent with **eleven function tools inside its own file** (the Session 7 and 8 way). Where the pain starts |
| `step02_first_server.py` | your **first MCP server**: two tools, twenty lines. Started by a client, not by you |
| `step02_call_it.py` | a plain **MCP client with no LLM**: connect, list tools, call a tool. Works against any server below |
| `step03_agent_with_mcp.py` | the **same agent**, tools from the MCP server over stdio. The eleven wrappers are gone |
| `step04_remote_server.py` | the agent talks to the server as a **network service**, with an identity header and an optional `--read-only` tool filter |
| `mcp_server/` | the real server: eleven tools (`server.py`), plus audit and tracing (`ops.py`), and its Dockerfile |
| `servicedesk_core/` | the IT "system": PostgreSQL schema and sample data (`sql/`), **the business rules** (`desk.py`), email and Slack alerts (`notify.py`) |
| `agent_api/` | the agent as an HTTP service (FastAPI + Agents SDK). Holds the model key, **no database password, no tool code** |
| `chat_ui/` | the employee's chat window (Streamlit) |
| `staff_console/` | the human side: the escalated queue, reply and resolve, and the audit log (Streamlit) |
| `k8s/` | Kubernetes manifests and `deploy.sh`, `open.sh`, `teardown.sh` |
| `docker-compose.yml` | the whole stack on one machine |
| `tests/` | 29 checks, no LLM: the rules against real PostgreSQL, and the MCP server through a real MCP client |
| `llm.py`, `agent_instructions.py`, `db.py` | plumbing: model and tracing setup, the one instruction text every agent uses, a database helper. Not part of the lesson |

## The sample people (same in every step)

| Id | Who | Situation | What the agent should do |
|---|---|---|---|
| `E-1001` | Priya Nair | account locked after failed sign-ins | unlock it, close the ticket |
| `E-1002` | Rahul Mehta | fine | e.g. gets the last **Figma** seat |
| `E-1003` | Meera Iyer | locked **and the security team put a hold on it** | refuse to unlock, **escalate as critical** |
| `S-9001` | Anita Rao | service-desk staff (a human) | answers escalated tickets in the staff console |

---

# Run order

Do the parts **in this order**, top to bottom. Each part says what you should see before you go on.

| Part | What you do | Needs |
|---|---|---|
| 1 | Get a Groq API key and export it | a free Groq account |
| 2 | Python environment and `pip install` | Python 3.10+ |
| 3 | Start PostgreSQL, Mailpit and Phoenix in Docker, load the sample data | Docker Desktop running |
| 4 | Run the 29 tests (no model needed) | |
| 5 | The four steps, one at a time | the key from Part 1 |
| 6 | The agent as a FastAPI service on your laptop | |
| 7 | Docker images and the whole stack with Docker Compose | |
| 8 | The whole stack on Kubernetes | Kubernetes enabled in Docker Desktop |

The commands are for macOS, Linux, WSL, or Git Bash on Windows (the Kubernetes scripts are bash). Use **one terminal** for Parts 1 to 5 and say so when a part needs a second one. Every **new** terminal needs `source .venv/bin/activate` and the `export` lines again.

Ports used on your machine: **8501** chat · **8502** staff console · **8020** agent API · **8030** MCP server · **5433** PostgreSQL · **6006** Phoenix · **8025** Mailpit web · **1025** Mailpit SMTP. PostgreSQL is on 5433 and the MCP server on 8030 on purpose: 5432 and 8000 are very often taken already. If a port is busy, stop whatever uses it.

## Part 1. Get a Groq API key and give it to your terminal

1. Go to https://console.groq.com and sign up (free).
2. Open **API Keys** → **Create API Key** → copy the key. It starts with `gsk_`. You will not be able to see it again.
3. In your terminal:

```bash
export GROQ_API_KEY="gsk_paste_your_key_here"
```

4. Check that Groq accepts it **before** you go on:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

You must see `HTTP 200`. `HTTP 401` means the key is wrong or has a stray space or quote: export it again.

`export` lasts only for that terminal window. Open a new terminal and you must run the `export` line again. (Never put the key in a file you commit. Part 7 writes it to `.env`, which is in `.gitignore`.)

Default model: `openai/gpt-oss-120b` on Groq. Any OpenAI-compatible endpoint with tool calling works through `LLM_MODEL`, `LLM_BASE_URL` and `LLM_API_KEY`.

## Part 2. Python environment and pip install

```bash
cd session_09/mcp_servicedesk_demo
python3 -m venv .venv
source .venv/bin/activate                  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` installs everything for Parts 2 to 6: the Agents SDK, the MCP SDK, the PostgreSQL driver, FastAPI and uvicorn, the Phoenix tracing libraries, and pytest. The Docker and Kubernetes services have their own smaller `requirements.txt` inside each folder.

Check:

```bash
python -c "import agents, mcp, fastapi, psycopg, phoenix.otel; print('imports ok')"
```

You should see `imports ok`. If you see `ImportError: cannot import name 'FastMCP'`, you have `mcp` 2.x: `pip install -r requirements.txt` pins `mcp<2`.

## Part 3. Start PostgreSQL, Mailpit and Phoenix, load the sample data

Docker Desktop must be running.

```bash
docker compose up -d postgres mailpit phoenix      # the real database, the real mail server, the trace viewer
docker compose ps                                  # wait until postgres and mailpit say (healthy)
python db.py reset                                 # load the sample employees, accounts, knowledge base, software
export PHOENIX_COLLECTOR_ENDPOINT="http://localhost:6006"     # every step after this sends its traces to Phoenix
```

Check: open http://localhost:6006 (Phoenix, empty for now) and http://localhost:8025 (Mailpit, an empty inbox).

`python db.py reset` puts the data back before each scene. Other views: `python db.py tickets`, `accounts`, `audit`, `software`. The first `docker compose up` downloads the images, so it takes a minute or two.

## Part 4. Run the tests (no model needed)

```bash
pytest tests          # 29 checks. WARNING: every test resets the demo database
python db.py reset    # put the sample data back for Part 5
```

You should see `29 passed`. `test_desk_rules.py` checks each rule, ON and refusing, against real PostgreSQL (also the "mail server is down, the ticket must still be escalated and the answer must say nobody was alerted" case). `test_mcp_server.py` starts the real server, connects a real MCP client, and checks the contract: eleven tools, **no tool takes an employee id**, `urgency` is an enum, each connection sees only its own account, refusals are normal answers, every call lands in the audit log.

## Part 5. The four steps

Run them in order. Every step file starts with a plain header: the problem it leaves behind, what it changes, and the exact messages to type. Same terminal as Parts 1 to 4 (the key and `PHOENIX_COLLECTOR_ENDPOINT` must be exported).

```bash
python step01_without_mcp.py            # 1. tools inside the agent. Read the file: how much of it is tool wrappers?
python step02_call_it.py                # 2. a plain client against the tiny server: it will show you a flaw
python step02_call_it.py --server full --employee E-1001      #    the real server: the flaw is gone
python step03_agent_with_mcp.py         # 3. the same agent; the tools now come from the server (stdio)
docker compose up -d mcp-server         # 4. the server as a network service ...
python step04_remote_server.py          #    ... and the agent connecting to it by URL
python step04_remote_server.py --read-only                    #    an agent that sees only the five read tools
```

Each agent step asks you for an employee id, then for messages. An empty line quits. Run `python db.py reset` before each scene.

| Step | What changes | Notice |
|---|---|---|
| 01 | eleven `@function_tool` wrappers in the agent | the second agent would have to copy all of them |
| 02 | tools in a server; a client that discovers them | with the tiny server, any client can ask for **E-1003's** account: the employee id is an *argument*. The full server has no such argument |
| 03 | `tools=[...]` becomes `mcp_servers=[server]` | same questions, same behaviour, about 115 fewer lines in the agent |
| 04 | `MCPServerStdio(...)` becomes `MCPServerStreamableHttp(url, headers)` | one server, many users (open a second terminal as another employee); `/healthz` exists |

Messages to try in steps 01, 03 and 04 (the answers should match across all three):

1. as `E-1001`: *I'm locked out of my account.* The agent opens a ticket, unlocks, closes the ticket.
2. as `E-1001`: *How do I connect to the VPN?* Answered from the knowledge base. No invented steps.
3. as `E-1003`: *I'm locked out of my account.* `unlock_account` is **refused** (`security_hold`) and the agent escalates as critical. Check `python db.py tickets` and the Mailpit inbox.
4. as `E-1002`: *I need Figma.* Gets the last seat. Then, without resetting, ask as `E-1001` for Figma too: the server answers `no_seats_free` and the agent escalates (low urgency).
5. as `E-1002`: *I got a new phone and need my authenticator moved.* A human must verify identity: escalate.
6. as `E-1001`: *I clicked a link in a strange email and typed my password.* Security incident: escalate as critical.

After any scene: `python db.py audit` shows one row for **every tool call**, written by the server, whichever client made it. In Phoenix (project `kernmart-servicedesk`) the same calls appear as `mcp.tool.*` spans. See "Reading Phoenix" in Part 7.

One difference to know about in Phoenix: from **step 04 on** (the server on the network) each `mcp.tool.*` span sits **inside** the agent's trace, under the tool call that caused it. In **step 03** the server is a child process over stdio, and the Agents SDK does not let the trace id through that path, so there the server's `mcp.tool.*` spans show up as separate one-span traces next to the agent's trace. The filters in Part 7 work in both.

The model decides how to word things and sometimes which tool to try first, so expect small differences from the list above. The rules are in code (`servicedesk_core/desk.py`), so a refusal always happens, whatever the model does.

## Part 6. The agent as a FastAPI service, on your laptop

Steps 03 and 04 ran the agent inside a script. `agent_api/main.py` is the same agent behind an HTTP endpoint, which is how a chat UI, or any other program, talks to it. Here you run it with uvicorn; in Part 7 the same file runs in a container.

It needs the MCP server running (from Part 5 step 4) and PostgreSQL (it keeps each conversation in a table, so any replica can continue any chat):

```bash
docker compose up -d mcp-server        # already running if you did step 04
python db.py reset
uvicorn agent_api.main:app --port 8020
```

Leave that terminal running; you will see `model: ... | MCP server: http://localhost:8030/mcp | tracing to http://localhost:6006`. If it stops at `No model API key`, the `export GROQ_API_KEY` from Part 1 is missing in this terminal.

In a **second terminal** (no venv needed):

```bash
curl -s http://localhost:8020/api/v1/health
curl -s -X POST http://localhost:8020/api/v1/chat -H 'content-type: application/json' \
  -d '{"employee_id":"E-1001","conversation_id":"chat-1","message":"I am locked out of my account"}'
```

The answer is JSON: `reply`, the list of `tool_calls` the agent made, and `escalated`. Change `employee_id` to `E-1003` and the answer says `"escalated": true`. FastAPI also writes its own documentation page, where you can try the same call with a form: http://localhost:8020/docs

Then open Phoenix: one trace for the message you just sent (see "Reading Phoenix" below). Traces are sent in batches, so wait about ten seconds before you look, and before you stop uvicorn (or the last trace may never leave your laptop). Stop uvicorn with Ctrl+C before Part 7: Compose runs the same service on the same port.

## Part 7. Docker images and the whole stack with Docker Compose

Docker Compose builds one image per service from the Dockerfiles in this folder, then starts all of them:

| Image | Built from | Runs |
|---|---|---|
| `kernmart-servicedesk/mcp-server:v1` | `mcp_server/Dockerfile` | the MCP server with the tools |
| `kernmart-servicedesk/agent-api:v1` | `agent_api/Dockerfile` | the FastAPI agent from Part 6 |
| `kernmart-servicedesk/chat-ui:v1` | `chat_ui/Dockerfile` | the employee chat window |
| `kernmart-servicedesk/staff-console:v1` | `staff_console/Dockerfile` | the human side |

PostgreSQL, Mailpit and Phoenix use ready-made images. Put your key where Compose can read it (`.env` is in `.gitignore`):

```bash
printf 'GROQ_API_KEY=%s\nSLACK_WEBHOOK_URL=%s\n' "$GROQ_API_KEY" "${SLACK_WEBHOOK_URL:-}" > .env
docker compose build                 # first build takes a few minutes
docker images | grep kernmart        # the four images you just built
docker compose up -d                 # start everything (PostgreSQL, Mailpit, Phoenix, MCP server are already up)
docker compose ps                    # seven services; agent-api and mcp-server say (healthy)
```

If `agent-api` keeps restarting, run `docker compose logs agent-api`: usually the key in `.env` is missing or wrong.

| Open | What you see |
|---|---|
| http://localhost:8501 | **Chat**: pick an employee, talk to the agent. "What the agent did" shows its tool calls |
| http://localhost:8502 | **Staff console**: escalated tickets, most urgent first. Reply and resolve; the employee gets an email. Second tab: the audit log |
| http://localhost:6006 | **Phoenix**: one trace per chat message: the agent's spans and the MCP server's `mcp.tool.*` spans in the same trace |
| http://localhost:8025 | **Mailpit**: every email the system sent (escalation alerts, reset links, staff replies) |

A good class sequence: chat as Priya (solved) and as Meera (escalated) → switch to the staff console, reply and resolve Meera's ticket → read the emails in Mailpit → ask Meera "what is the status of my ticket?" and the agent reads the human's reply → open Phoenix (the traces) and the audit tab.

### Reading Phoenix

Phoenix is our one place to see what happened. Open http://localhost:6006 → project **kernmart-servicedesk** → **Traces**. One chat message is one trace; click its `POST /api/v1/chat` row to open the tree: the agent workflow, each model call (`generation`), the tool list fetch (`mcp_tools`), and the MCP server's `mcp.tool.<name>` spans inside the same trace. Each span shows its inputs, outputs, duration and, for model calls, token counts.

Type these into the **Filter** box above the trace table (they match spans):

| You want | Filter |
|---|---|
| every tool call that the rules **refused** | `tool.outcome == 'refused'` |
| tool calls that **failed** (a bug or an outage) | `tool.outcome == 'error'` |
| tickets the agent **solved without a human** | `servicedesk.event == 'ticket_resolved_by_agent'` |
| tickets **handed to a human** | `servicedesk.event == 'ticket_escalated'` |
| tickets the agent opened | `servicedesk.event == 'ticket_created'` |
| everything caused by one employee | `employee.id == 'E-1003'` |
| one conversation | `session.id == 'chat-1'` |

The **Sessions** tab groups traces by conversation. A tool's duration is the span's own duration. A failed model call (a wrong API key, say) shows as a red `generation` span with the provider's error.

Phoenix is not the audit log. It is for developers to debug and measure the agent, and it can be wiped. The **audit** table in PostgreSQL (`python db.py audit`, or the staff console's second tab) is the record of who did what, written by the server on every call.

Stop with `docker compose down` (add `-v` to also delete the database). **Do this before Part 8**: Kubernetes uses the same ports on your machine.

## Part 8. The whole stack on Kubernetes

The same four images and the same three helpers, now as Deployments and Services in a namespace called `servicedesk`: two `mcp-server` pods, two `agent-api` pods, one each of the rest.

**Before you start**

1. Stop Compose, it holds the same ports: `docker compose down`
2. Turn Kubernetes on. In Docker Desktop: **Settings → Kubernetes → Enable Kubernetes → Apply**, wait until it says it is running. (Or use kind or minikube; see the note below.)
3. Point `kubectl` at it and check:

```bash
kubectl config use-context docker-desktop
kubectl get nodes                      # one node, STATUS Ready
```

**Deploy** (from this folder, with the key from Part 1 still exported in this terminal):

```bash
export GROQ_API_KEY="gsk_paste_your_key_here"      # only if this is a new terminal
./k8s/deploy.sh                        # builds the four images, creates namespace, secret, configs, and all services
kubectl -n servicedesk get pods        # 9 pods, all Running and 1/1 Ready
```

`deploy.sh` waits for every Deployment to be ready, so when it prints `Done` the pods are up. It stops at once if `GROQ_API_KEY` is missing.

To change the key later without redeploying (pods read the secret only when they start, so restart the agent):

```bash
kubectl -n servicedesk patch secret servicedesk-secrets -p "{\"stringData\":{\"GROQ_API_KEY\":\"$GROQ_API_KEY\"}}"
kubectl -n servicedesk rollout restart deployment/agent-api
```

**Open the screens** in a second terminal and leave it running (Ctrl+C stops the port forwards):

```bash
./k8s/open.sh
```

Same addresses as Part 7: chat http://localhost:8501, staff console http://localhost:8502, Phoenix http://localhost:6006, Mailpit http://localhost:8025, and the MCP server on http://localhost:8030 (so `step02_call_it.py --url http://localhost:8030/mcp --employee E-1001` reaches the server inside the cluster).

Things to try, each one a Session 3 idea in a new setting:

```bash
kubectl -n servicedesk get pods                                  # two mcp-server pods, two agent-api pods
kubectl -n servicedesk delete pod -l app=mcp-server              # kill both: chat again, nothing visible should break
kubectl -n servicedesk scale deployment/mcp-server --replicas=4  # stateless: any replica answers any request
kubectl -n servicedesk logs deployment/mcp-server                # the server's request log
```

**Clean up:** `./k8s/teardown.sh` deletes the namespace and everything in it, including the database disk.

Note on other clusters: `deploy.sh` also works on **kind** (it copies the images into the cluster for you) and **minikube** (run `eval $(minikube docker-env)` first). `python db.py` talks to `localhost:5433`, which is the Compose database, so with Kubernetes read the audit log in the staff console's second tab.

---

## Enterprise notes (the slides explain each; here is where it lives in the code)

| Topic | Where |
|---|---|
| Stateless, scalable server | `FastMCP(..., stateless_http=True, json_response=True)` in `mcp_server/server.py`; 2 replicas in `k8s/30-mcp-server.yaml` |
| Health and readiness | `/healthz` in `server.py`; probes in the manifests and Compose |
| Identity | `who_is_asking()` in `mcp_server/ops.py`. **Demo limit: the `X-Employee-Id` header is not verified.** Replace this one function with token verification (signature, expiry, audience, scopes) |
| Rules in code, not in the prompt | `servicedesk_core/desk.py` (3 unlocks a day, no unlock under a security hold, address on file only, seats, ownership of tickets) |
| Audit | the `@governed` decorator writes one `audit_log` row per call (`mcp_server/ops.py`) |
| Observability | Arize Phoenix. Both services send traces; every tool call is a span with `tool.outcome`, `servicedesk.event` and `employee.id` (`@governed` in `mcp_server/ops.py`); the agent's own spans come from `llm.start_tracing()` |
| Traces across agent and server | `openinference-instrumentation-mcp` on both sides passes the trace id in each call, so the server's span lands inside the agent's trace |
| Least privilege per agent | `tool_filter=` in `step04_remote_server.py` (`--read-only`) |
| Secrets | a Kubernetes Secret built by `deploy.sh`; at work, a secret manager. The agent pod has the model key only; the MCP pod has the database password only |
| Not in the demo, add at work | real SSO and tokens, an API or MCP gateway, network policies (agent → server → database only), autoscaling, a managed database, log shipping, an approved-server catalogue, and **time-series metrics with alerting** (Phoenix shows each request in depth; it does not page you when the error rate climbs: that is a metrics system's job, such as Prometheus and Grafana) |

## Slack (optional)

Create an Incoming Webhook in your Slack workspace, then `export SLACK_WEBHOOK_URL=https://hooks.slack.com/...` **before** the `printf` line in Part 7 (it goes into `.env`) or before `./k8s/deploy.sh`. Escalations then also post to that channel. Without it the email still goes out and `escalate_to_human` reports `slack: not_configured`, honestly.

## What was and was not verified

Verified by running this README from a clean start (deleted `.venv`, `.env`, containers, the database volume and the built images first) on macOS with Docker Desktop, Python 3.14 on the laptop and 3.12 in the containers, `mcp` 1.30, `openai-agents` 0.24, Phoenix 21.1.0:

- **Part 2**: `pip install -r requirements.txt` and the import check.
- **Part 3**: PostgreSQL, Mailpit and Phoenix start and become ready; `python db.py reset`.
- **Part 4**: 29 passing checks.
- **Part 5**: steps 01, 03 and 04 (and `--read-only`, which shows 5 tools) through the real Agents SDK loop, the real MCP server, the real database and the real SMTP server. A refusal for `E-1003`, the escalation, and one audit row per call.
- **Part 6**: `uvicorn agent_api.main:app`, `/api/v1/health`, `/api/v1/chat`, `/docs`.
- **Part 7**: `docker compose build` makes the four images; `docker compose up -d` gives seven healthy services; the chat API solves Priya's case and escalates Meera's; the critical alert email arrives in Mailpit; both Streamlit apps answer.
- **Part 8 (Kubernetes)**: applied with `./k8s/deploy.sh` on Docker Desktop's built-in Kubernetes (v1.36): 9 pods Running and Ready, `./k8s/open.sh` forwards the ports, chat UI, staff console, Phoenix, Mailpit and the MCP server answer on localhost, the MCP server lists its 11 tools through the forward, the cluster's database holds the sample data. This found one real bug, now fixed: a Service named `phoenix` makes Kubernetes inject `PHOENIX_PORT=tcp://...`, which Phoenix refuses to start with. `enableServiceLinks: false` in `k8s/20-mailpit-phoenix.yaml` switches that off.
- **Phoenix**: each chat message is one trace, rooted at `POST /api/v1/chat`, with the server's `mcp.tool.*` spans nested under the tool calls; no health-probe spans; every filter in "Reading Phoenix" returns the right spans.

**Not verified:**

- **A real model.** There was no `GROQ_API_KEY` where this was built. For the run above, the model endpoint was a throwaway stand-in (not in this folder) that answers with a fixed tool sequence, so everything around the model was real and the model was not. A wrong key was also tried: Groq answered `401` and the chat reported "The assistant is unavailable", as the troubleshooting table says. Run each step once with your own key and expect the real model to sometimes take a different path or word things differently. The rules hold regardless: they are in code.
- **Kubernetes with a real model and a real chat.** Part 8 was applied to Docker Desktop's Kubernetes (see above), but chatting through the UI needs your Groq key.
- **Slack.** The webhook path was not run (no webhook available). The email path is verified.
- **The `mcp.tool.*` spans inside the trace over stdio (step 03)**: they do not nest (see Part 5).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `connection refused` on `localhost:5433` | Docker is not running, or `docker compose up -d postgres` was not run |
| `port is already allocated` | something else uses that port; stop it, or change the left number of the `ports:` entry in `docker-compose.yml` (and the URL in the step you run). With Kubernetes: you forgot `docker compose down` |
| `ImportError: cannot import name 'FastMCP'` | you installed `mcp` 2.x, which renamed it. `pip install -r requirements.txt` pins `mcp<2` |
| `No model API key` / `Set GROQ_API_KEY first` | the key is not exported in **this** terminal (Part 1), or `.env` has no key (Part 7) |
| `openai.AuthenticationError: 401 Invalid API Key` | the key is wrong. Re-run the `curl` check in Part 1; it must say `HTTP 200` |
| Phoenix shows no traces | in a laptop terminal, `export PHOENIX_COLLECTOR_ENDPOINT="http://localhost:6006"` before running the step; Phoenix must be up (`docker compose ps`). Traces appear a few seconds after the call |
| Phoenix returns `401 Invalid token` | Phoenix turns authentication on by default; Compose and the manifests set `PHOENIX_ENABLE_AUTH=false` for the demo. Start your own with the same variable |
| `agent-api` keeps restarting | `docker compose logs agent-api`: usually a missing key |
| The chat says "The assistant is unavailable" | `docker compose logs agent-api`: usually a wrong key, no network, or the model name |
| Tool calls fail with `Unknown requester` | the connection carried no identity: over HTTP the `X-Employee-Id` header, over stdio the `EMPLOYEE_ID` variable |
| Escalation says `human_alerted: false` | the mail server is unreachable (`SMTP_HOST`). The ticket is still in the staff queue |
| `kubectl`: `current-context is not set` or `connection refused` | Kubernetes is not enabled or not selected: Part 8, "Before you start" |
| Pods `ImagePullBackOff` for `kernmart-servicedesk/...` | the cluster cannot see your local images. kind: `deploy.sh` loads them (run it again). minikube: `eval $(minikube docker-env)`, then `deploy.sh` again |
