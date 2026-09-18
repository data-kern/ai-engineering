import os
import streamlit as st
from groq import Groq

# SOLUTION 1 & 2: Imports for Observability
from phoenix.otel import register
from openinference.instrumentation.groq import GroqInstrumentor

# -----------------------------------------------------------------------
# OBSERVABILITY SETUP
# -----------------------------------------------------------------------

# SOLUTION 3: Initialize tracer
tracer_provider = register(
    project_name="streamlit-chatbot"
)

# SOLUTION 4: Instrument Groq
GroqInstrumentor().instrument(tracer_provider=tracer_provider)


# -----------------------------------------------------------------------
# APP SETUP
# -----------------------------------------------------------------------

if not os.environ.get("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY not found. Please export it in your terminal.")
    st.stop()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"
SYSTEM_PROMPT = "You are a helpful AI Engineering tutor at DataKern."

st.title("🤖 DataKern Chatbot (with Observability)")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# Draw previous messages
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Wait for input
if prompt := st.chat_input("Type your message here..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
        
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 💡 API call is automatically tracked!
    response = client.chat.completions.create(
        messages=st.session_state.messages,
        model=MODEL
    )
    
    reply = response.choices[0].message.content
    
    with st.chat_message("assistant"):
        st.markdown(reply)
        
    st.session_state.messages.append({"role": "assistant", "content": reply})
