import os
import streamlit as st
from groq import Groq

"""
╔══════════════════════════════════════════════════════════════╗
║  Exercise 02 — Move the Chat to a Web UI                    ║
║  Topic: Streamlit · session_state · chat_message            ║
╚══════════════════════════════════════════════════════════════╝

Real-world story
────────────────
The terminal chat from Exercise 1 works — but nobody ships
a terminal app to users. You need a real web interface.

Streamlit lets you build a live web UI in pure Python.
There's one catch: Streamlit reruns your ENTIRE script
from top to bottom every single time the user presses Enter.

That means normal Python variables get wiped out on every rerun.
Your `messages` list would start fresh every single turn —
the AI would forget everything instantly.

The fix: store your messages in `st.session_state`.
This is a special dictionary that SURVIVES reruns.

────────────────────────────────────────────────────────────────
What to build  (8 steps)
────────────────────────────────────────────────────────────────
  TODO 1 — Initialise session_state (only on first load)
  TODO 2 — Draw the existing chat history on screen
  TODO 3 — Wait for user input with st.chat_input()
  TODO 4 — Display the user's message immediately
  TODO 5 — Append user message to session_state
  TODO 6 — Call the Groq API, extract the reply
  TODO 7 — Display the AI's reply
  TODO 8 — Append AI reply to session_state

────────────────────────────────────────────────────────────────
Thinking hints  💡
────────────────────────────────────────────────────────────────
  Initialising safely (only on first load):
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", ...}]

  Drawing a message bubble:
    with st.chat_message("user"):
        st.markdown("Hello!")

  Getting user input (also acts as an if-check):
    if prompt := st.chat_input("Type here..."):
        # user typed something — prompt holds the text

  Skip drawing the system prompt (users shouldn't see it):
    if msg["role"] != "system":
        # draw it

────────────────────────────────────────────────────────────────
Run it with:   streamlit run exercise_02_streamlit_chat.py
────────────────────────────────────────────────────────────────
"""

# ── API setup — do NOT change ─────────────────────────────────────────────────

if not os.environ.get("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY not found. Please export it in your terminal.")
    st.stop()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "You are a helpful AI Engineering tutor at DataKern."

st.title("🤖 DataKern AI Chatbot")

# ── Streamlit reruns this ENTIRE file on every user interaction ───────────────
# Normal variables get wiped. Store messages in session_state so they survive.

# ── TODO 1 ────────────────────────────────────────────────────────────────────
# If "messages" isn't in session_state yet, create the list with the system
# prompt inside it. This runs ONCE on first load, then never again.
# → Write your code below:


# ── TODO 2 ────────────────────────────────────────────────────────────────────
# Loop through session_state.messages and draw each one as a chat bubble.
# Skip any message where role == "system" (keep it hidden from the user).
# → Write your code below:


# ── TODO 3 ────────────────────────────────────────────────────────────────────
# Wait for user input using st.chat_input().
# The walrus operator  :=  assigns AND checks in one line.
# → Write your code below:

    # ── Everything below runs ONLY when the user submits a message ────────────

    # ── TODO 4 ────────────────────────────────────────────────────────────────
    # Show the user's message as a chat bubble immediately.
    # → Write your code below:


    # ── TODO 5 ────────────────────────────────────────────────────────────────
    # Append the user's message dict to session_state.messages.
    # → Write your code below:


    # ── TODO 6 ────────────────────────────────────────────────────────────────
    # Call the Groq API, passing st.session_state.messages.
    # Extract the reply text from the response.
    # → Replace the placeholder below:
    reply = "..."   # ← change this line


    # ── TODO 7 ────────────────────────────────────────────────────────────────
    # Display the AI's reply as an "assistant" chat bubble.
    # → Write your code below:


    # ── TODO 8 ────────────────────────────────────────────────────────────────
    # Append the AI's reply to session_state.messages.
    # Without this, the AI forgets what it just said on the next rerun!
    # → Write your code below:
