# Session 4 — RAG Demo
## Retrieval-Augmented Generation: Hands-On with Apex Financial

**DataKern AI Engineering · Session 4**

This demo lets you run the RAG pipeline step by step and see exactly what
each step produces — from a plain-text question to a policy-grounded answer.
All scripts run in **Observe Mode**, pausing at key moments to let you predict
outcomes and observe the live behavior of the system.

---

## The Core Idea

The same question. The same LLM. Two completely different answers.

**Without RAG** — the LLM answers from its training knowledge only:
```
Q: "Should Mr. Peterson add more NVDA to his portfolio?"
A: "Nvidia is a strong AI infrastructure play with substantial growth potential..."
```
❌ Wrong. Mr. Peterson is a **Conservative** client. NVDA violates his risk rules.

**With RAG** — the service retrieved the relevant policy sections first:
```
Q: "Should Mr. Peterson add more NVDA to his portfolio?"
A: "I cannot recommend adding NVDA to Mr. Peterson's portfolio. Per Section 2.3
    of the Apex Financial Risk Policy: Conservative clients must not be recommended
    any individual equity with a 12-month beta greater than 1.5..."
```
✅ Correct. The policy was retrieved and the LLM applied it.

**Why the difference?** The system prompt. That's it. The RAG pipeline retrieved
the relevant policy sections and placed them in the prompt before calling the LLM.
The LLM itself is identical in both cases.

---

## The Five-Step Pipeline

```
Step 1: RECEIVE   — question enters the pipeline
Step 2: EMBED     — question → 384-float vector (its mathematical meaning)
Step 3: SEARCH    — vector → top 3 policy chunks (cosine similarity in pgvector)
Step 4: INJECT    — chunks embedded into the system prompt
Step 5: GENERATE  — LLM answers using the augmented prompt
```

Direct mode skips Steps 2 and 3 and uses a prompt with no policy context.

---

## Code Structure

```
demo/
├── data/
│   ├── apex_risk_policy.txt         ← The mock Apex Financial policy (plain text)
│   └── client_profile.txt           ← Mr. Peterson's client profile
│
├── scripts/                         ← Run these in order
│   ├── 01_setup_vector_db.py        ← Create rag schema + HNSW index (run once)
│   ├── 02_index_documents.py        ← Chunk, embed, store the policy (run once)
│   ├── 03_rag_pipeline_walkthrough.py ← THE KEY SCRIPT: pipeline step by step
│   └── 04_demo_comparison.py        ← Side-by-side comparison (requires API running)
│
├── app/
│   ├── schema.py                    ← Request/response shapes (Pydantic)
│   ├── step2_embed.py               ← Step 2: text → 384-float vector
│   ├── step3_search.py              ← Step 3: vector → top-k policy chunks
│   ├── step4_inject.py              ← Step 4: build direct or RAG system prompt
│   ├── step5_generate.py            ← Step 5: call the LLM, return answer
│   ├── pipeline.py                  ← Orchestrator: wires steps 2→3→4→5
│   └── main.py                      ← FastAPI: /ask and /ask/rag HTTP endpoints
│
├── requirements.txt
├── Dockerfile
└── k8s/
    ├── 01-secret.yaml
    ├── 02-deployment.yaml
    └── 03-service.yaml
```

**Start by reading `app/pipeline.py`** — it shows the full five-step flow in one file.
Each step imports from its corresponding `stepN_*.py` module.

---

## Prerequisites

You completed Session 3. Check that you have:

- [ ] Python 3.11+
- [ ] Docker Desktop running (for Kubernetes option)
- [ ] Minikube running — verify with `minikube status`
- [ ] A local PostgreSQL database running with the `pgvector` extension installed (see Setup below)
- [ ] A Groq API key — get one free at [console.groq.com](https://console.groq.com)

---

## Setup — Run These Steps Once

### Step 0 — Install pgvector (if using local Postgres)

If you are running Postgres locally, you MUST install the `pgvector` extension first. Otherwise, the database setup script will fail with the error `extension "vector" is not available`.

**🍎 On Mac (with Homebrew):**
```bash
brew install pgvector
brew services restart postgresql
```

**🪟 On Windows:**
Native installation of `pgvector` on Windows is complex. The standard and most reliable method is to use Docker to run a Postgres instance that already has `pgvector` pre-installed:
```bash
docker run --name pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d pgvector/pgvector:pg16
```
*(Note: If you already have a local Postgres running on port 5432, you will need to stop it first, or map this container to a different port like `-p 5433:5432` and update the `DB_PORT` variable).*

---

### Step 1 — Create a virtual environment and install dependencies

```bash
cd session_04/demo

python -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

> ⚠️ The first install downloads `sentence-transformers` and its PyTorch dependency — about 500MB. This only happens once.

---

### Step 2 — Set your Groq API key

```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

> Mac tip: add this to `~/.zshrc` so you don't have to set it every session.

---

## Running the Interactive Pipeline

Run each script from the `demo/` folder:

```bash
cd demo

python scripts/01_setup_vector_db.py
python scripts/02_index_documents.py
python scripts/03_rag_pipeline_walkthrough.py
```

Each script runs in **Observe Mode**. 
Instead of instantly dumping a wall of text, the scripts will pause at each major step.

You will see prompts like this:
```
PREDICT: Before we can search the database, we must embed the question.
Will the question vector be the same dimension?
🔍 Press ENTER to continue ➔
OBSERVE: Open your dashboard...
```

**Keep DBeaver and Phoenix open.** 
*(Note: Phoenix will automatically start when you run the `03_rag_pipeline_walkthrough.py` script or the FastAPI service in Step 4. You can view it at `http://localhost:6006`).*

The scripts will explicitly tell you when to look at the UI and what to observe as you press Enter to execute the actions.

---

### Step 4 — Start the API Service & Phoenix Server

To test the actual web endpoints (and see the traces in Phoenix), you must start the FastAPI service. 

**⚠️ IMPORTANT: This must be done in a SEPARATE, NEW terminal window!** 
Because the web server needs to run continuously in the background, you cannot use your original terminal window.

1. Open a **new terminal window** or tab.
2. Navigate to the demo folder and activate your virtual environment:
   ```bash
   cd path/to/session_04/demo
   source venv/bin/activate
   ```
3. Start the FastAPI service (this command automatically launches the Phoenix observability server as well!):
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

*(Leave this new terminal running! It is now hosting your API at `http://localhost:8000/docs` and Phoenix at `http://localhost:6006`).*

---

### Step 5 — Compare both modes side by side

Switch back to your **original terminal window** (where you ran the python scripts earlier), and run:

```bash
python scripts/04_demo_comparison.py
```

This sends the same three questions to both endpoints and prints the answers
side by side, letting you predict the outcomes before they appear.

You can also ask your own question:
```bash
python scripts/04_demo_comparison.py "Can a conservative client hold 80% in tech stocks?"
```

---

### Step 6 (optional) — Run on Kubernetes

```bash
eval $(minikube docker-env)
docker build -t rag-demo:latest .

kubectl create secret generic groq-secret \
  --from-literal=GROQ_API_KEY=$GROQ_API_KEY

kubectl apply -f k8s/01-secret.yaml
kubectl apply -f k8s/02-deployment.yaml
kubectl apply -f k8s/03-service.yaml

kubectl get pods -w
minikube service rag-demo-service --url
```

---

## Phoenix — LLM Trace Observability

Phoenix records every LLM call as a trace. It starts automatically when
the service starts (as long as the `arize-phoenix` package is installed).

Open `http://localhost:6006` in your browser.

For each LLM call you can see:
- The **exact system prompt** sent to the LLM (for RAG calls, you will see the retrieved chunks embedded in the prompt)
- The **token count** — RAG calls use more tokens because the chunks add context
- The **latency** breakdown — how long each part of the call took

This complements the walkthrough script: the walkthrough shows you the pipeline
in a terminal; Phoenix shows you the same data in a visual trace UI.

> If Phoenix fails to start, the service continues normally — it prints a warning and carries on.

---

## Troubleshooting

| Problem | What to try |
|---|---|
| `extension "vector" is not available` | `pgvector` is not installed on your system. Run `brew install pgvector` and restart Postgres. |
| `sentence_transformers not found` | `pip install sentence-transformers` |
| `GROQ_API_KEY environment variable is not set` | `export GROQ_API_KEY="gsk_your_key_here"` |
| `Connection refused` on setup/indexing | Check Postgres is running: `brew services start postgresql@18` or `docker ps` |
| Kubernetes pods stuck in `Pending` | `kubectl describe pod <pod-name>` — likely image not built inside Minikube: `eval $(minikube docker-env) && docker build -t rag-demo:latest .` |
| Pods running but `/health` returns 503 | Embedding model still loading. Wait 20–30s and retry. |
| Port 8000 already in use | `uvicorn app.main:app --port 8001` |
| Phoenix not loading at 6006 | This is non-blocking — the service still works. Check if `arize-phoenix` installed. |

---

*Don't focus on getting the answer. Focus on learning how to engineer the solution.*
**— Uma Kiran | DataKern | www.data-kern.com**
