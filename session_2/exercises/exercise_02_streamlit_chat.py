import os
import streamlit as st
from groq import Groq

# ── Guard: API key ──────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY not found. Please export it in your terminal.")
    st.stop()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "You are a helpful AI Engineering tutor at DataKern."

st.title("🤖 DataKern AI Chatbot")

# Streamlit reruns this ENTIRE file from top to bottom every time a user interacts.
# Because of this, normal variables get wiped out.
# We must store our `messages` list in `st.session_state` so it survives reruns.

# TODO 1: Check if "messages" is NOT inside `st.session_state`.
# If it isn't, initialize it as a list containing the system prompt dictionary.
# -> Write your code below:


# TODO 2: Loop through every message in `st.session_state.messages`.
# Draw them on the screen using `with st.chat_message(msg["role"]): st.markdown(msg["content"])`
# (Hint: skip the system prompt so it stays hidden from the user).
# -> Write your code below:


# TODO 3: Wait for user input using `st.chat_input("Type your message here...")`.
# Store the result in a variable called `prompt`.
# (Hint: `if prompt := st.chat_input(...):`)
# -> Write your code below:


    # ── Inside the if-block (when user types something): ──
    
    # TODO 4: Immediately draw the user's message on the screen
    # -> Write your code below:
    
    
    # TODO 5: Append the user's message dictionary to `st.session_state.messages`
    # -> Write your code below:
    
    
    # TODO 6: Call the Groq API and pass `st.session_state.messages`
    # Extract the AI's reply from the response.
    # -> Write your code below:
    reply = "..." # Replace with actual reply
    
    # TODO 7: Draw the AI's reply on the screen
    # -> Write your code below:
    
    
    # TODO 8: Append the AI's reply to `st.session_state.messages` so it remembers for next time!
    # -> Write your code below:
    
