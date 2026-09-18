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

# SOLUTION 1: Check and initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# SOLUTION 2: Loop through and draw history
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# SOLUTION 3: Wait for user input
if prompt := st.chat_input("Type your message here..."):
    
    # SOLUTION 4: Draw user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # SOLUTION 5: Append user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # SOLUTION 6: Call API
    response = client.chat.completions.create(
        messages=st.session_state.messages,
        model=MODEL
    )
    reply = response.choices[0].message.content
    
    # SOLUTION 7: Draw AI reply
    with st.chat_message("assistant"):
        st.markdown(reply)
        
    # SOLUTION 8: Append AI reply to history
    st.session_state.messages.append({"role": "assistant", "content": reply})
