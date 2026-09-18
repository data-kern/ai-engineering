# AI Engineering Session 2 — In-Class Exercises
### Groq API · Streamlit · Phoenix Observability · DataKern

---

## What you will build today

By the end of these three exercises you will have:

| Exercise | What you build | Tech |
|----------|---------------|------|
| 01 | A terminal chatbot that remembers the full conversation | Groq API, Python |
| 02 | The same chatbot — but with a proper web UI | Streamlit |
| 03 | The same chatbot — but now every AI call is tracked and visible | Phoenix |

Each exercise builds directly on the previous one. Do them in order.

---

## What's inside

```
ae_session_02/
├── exercises/          ← your working files (edit these)
│   ├── exercise_01_terminal_chat.py
│   ├── exercise_02_streamlit_chat.py
│   └── exercise_03_phoenix_tracing.py
└── solutions/          ← check AFTER you've genuinely tried it
```

---

## Step 1 — Clone the DataKern repo (first time only)

```bash
git clone https://github.com/mindednet/datakern.git
cd datakern
```

> Already cloned it? Just pull the latest:
> ```bash
> git checkout main
> git pull origin main
> ```

---

## Step 2 — Create your branch

```bash
git checkout -b ae-session-2/firstname-lastname
```

**Example:**
```bash
git checkout -b ae-session-2/alice-johnson
```

> ⚠️ Never work on `main` directly. Your branch is your workspace.

---

## Step 3 — Create a virtual environment

```bash
python3 -m venv .venv
```

**Activate it:**

| OS | Command |
|----|---------|
| macOS / Linux | `source .venv/bin/activate` |
| Windows | `.venv\Scripts\activate` |

You should see `(.venv)` in your terminal prompt.

---

## Step 4 — Install the required libraries

```bash
pip install groq streamlit arize-phoenix openinference-instrumentation-groq opentelemetry-sdk opentelemetry-exporter-otlp
```

Verify:
```bash
python3 -c "import groq, streamlit; print('All good!')"
```

---

## Step 5 — Set your Groq API key

Your exercises call the Groq AI API. You need an API key to authenticate.

Get your free key at: **https://console.groq.com**

Then set it in your terminal (do this every time you open a new terminal):

```bash
export GROQ_API_KEY="your_key_here"
```

Verify it's set:
```bash
echo $GROQ_API_KEY
```

> 💡 If it prints your key, you're good. If it's blank, run the export command again.

---

## Step 6 — Solve the exercises

Work through them **in order**. Each one takes 10–15 minutes.

### Exercise 01 — Terminal Chat

```bash
cd ai_engineering_regular_sessions/ae_session_02/exercises
python3 exercise_01_terminal_chat.py
```

You are filling in **5 TODOs** to make a terminal chatbot hold a real conversation.
When it works, try asking the AI a follow-up question — it should remember what you said earlier.

---

### Exercise 02 — Streamlit Web UI

```bash
streamlit run exercise_02_streamlit_chat.py
```

You are filling in **8 TODOs** to turn the terminal chat into a real web app.
The key new concept: `st.session_state` — why is this needed?

When it works, a browser tab opens automatically at `http://localhost:8501`.

---

### Exercise 03 — Phoenix Observability

**First, start Phoenix in a separate terminal tab:**

```bash
# New terminal tab
source .venv/bin/activate
python3 -c "import phoenix as px; px.launch_app()"
```

Phoenix dashboard will be running at: `http://localhost:6006`

**Then run your chatbot:**

```bash
streamlit run exercise_03_phoenix_tracing.py
```

You are adding **4 lines** to wire observability into the chatbot.
After each message you send in the chatbot, refresh Phoenix and watch the trace appear.

---

## Step 7 — Save your work

```bash
git add ai_engineering_regular_sessions/ae_session_02/exercises/
git commit -m "ae-session-2: complete all 3 exercises"
git push origin ae-session-2/firstname-lastname
```

---

## Step 8 — Raise a Pull Request

1. Go to **github.com/mindednet/datakern**
2. Click **"Compare & pull request"**
3. Fill in the PR:

| Field | Value |
|-------|-------|
| **Title** | `AI Session 2 Exercises — Firstname Lastname` |
| **Base branch** | `main` |
| **Compare branch** | `ae-session-2/firstname-lastname` |

4. In the description, answer:
   - What happens if you forget to append the AI's reply to the messages list?
   - What new information did Phoenix show you that you couldn't see before?

---

## Rules

- ❌ No AI tools to write the code for you — the whole point is to type it yourself
- ✅ Use the hints inside each exercise file
- ✅ Peek at `solutions/` only after a genuine attempt
- ✅ Commit after each exercise, not just at the end

---

## Quick reference

```bash
# Full workflow
git clone https://github.com/mindednet/datakern.git && cd datakern
git checkout -b ae-session-2/firstname-lastname
python3 -m venv .venv && source .venv/bin/activate
pip install groq streamlit arize-phoenix openinference-instrumentation-groq opentelemetry-sdk opentelemetry-exporter-otlp
export GROQ_API_KEY="your_key_here"

# Exercise 01
python3 ai_engineering_regular_sessions/ae_session_02/exercises/exercise_01_terminal_chat.py

# Exercise 02
streamlit run ai_engineering_regular_sessions/ae_session_02/exercises/exercise_02_streamlit_chat.py

# Exercise 03 — start Phoenix first in a separate tab
python3 -c "import phoenix as px; px.launch_app()"
# then in your main tab:
streamlit run ai_engineering_regular_sessions/ae_session_02/exercises/exercise_03_phoenix_tracing.py
```
