import os
import streamlit as st
from groq import Groq

"""
╔══════════════════════════════════════════════════════════════╗
║  Exercise 03 — Make Your AI Visible (Observability)         ║
║  Topic: Phoenix · OpenTelemetry · GroqInstrumentor          ║
╚══════════════════════════════════════════════════════════════╝

Real-world story
────────────────
Your chatbot is live. Users are talking to it. But questions
start arriving from your manager:

  "Why did the AI give a weird answer to that one user?"
  "How many tokens did we use this week?"
  "Which questions take the longest to respond to?"

You cannot answer any of these by just reading code.
You need observability — a way to record and inspect every
single AI call your app makes.

Phoenix is an open-source AI observability platform.
With just 4 lines of code, it will automatically record
every call your app makes to Groq and show it in a dashboard.

────────────────────────────────────────────────────────────────
What to add  (4 TODOs at the top of the file)
────────────────────────────────────────────────────────────────
The rest of the chatbot (from Exercise 2) is already written.
You only need to add the 4 observability lines at the top.

  TODO 1 — Import  register  from phoenix.otel
  TODO 2 — Import  GroqInstrumentor  from openinference.instrumentation.groq
  TODO 3 — Call  register()  to start the tracer
  TODO 4 — Call  GroqInstrumentor().instrument()  to attach it to Groq

After that, every Groq API call below is AUTOMATICALLY tracked.
You don't need to change any other code.

────────────────────────────────────────────────────────────────
Thinking hints  💡
────────────────────────────────────────────────────────────────
  TODO 1 & 2 — Imports go at the very top, like any other import:
    from phoenix.otel import register
    from openinference.instrumentation.groq import GroqInstrumentor

  TODO 3 — Start the tracer and save it:
    tracer_provider = register(project_name="streamlit-chatbot")

  TODO 4 — Wire it to the Groq library:
    GroqInstrumentor().instrument(tracer_provider=tracer_provider)

  💡 After these 4 lines, Phoenix intercepts every Groq call
     and logs the prompt, response, model, tokens, and latency.

────────────────────────────────────────────────────────────────
Run it with:   streamlit run exercise_03_phoenix_tracing.py
Then open:     http://localhost:6006  to see Phoenix dashboard
────────────────────────────────────────────────────────────────
"""

# ── TODO 1 — Import `register` from phoenix.otel ─────────────────────────────
# → Write your code below:


# ── TODO 2 — Import `GroqInstrumentor` from openinference.instrumentation.groq ─
# → Write your code below:


# ── TODO 3 — Start the tracer (save it to `tracer_provider`) ─────────────────
# → Write your code below:


# ── TODO 4 — Instrument Groq so all API calls are tracked ────────────────────
# → Write your code below:


# ── APP SETUP (identical to Exercise 2 — do NOT change) ──────────────────────

if not os.environ.get("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY not found. Please export it in your terminal.")
    st.stop()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "You are a helpful AI Engineering tutor at DataKern."

st.title("🤖 DataKern Chatbot (with Observability)")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("Type your message here..."):

    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    # 💡 Because you instrumented Groq above, this call is now tracked in Phoenix!
    response = client.chat.completions.create(
        messages=st.session_state.messages,
        model=MODEL
    )

    reply = response.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
