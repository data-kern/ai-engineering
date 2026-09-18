import os
import streamlit as st
from groq import Groq

# TODO 1: Import `register` from `phoenix.otel`
# TODO 2: Import `GroqInstrumentor` from `openinference.instrumentation.groq`
# -> Write your code below:


# -----------------------------------------------------------------------
# OBSERVABILITY SETUP
# -----------------------------------------------------------------------

# TODO 3: Initialize the tracer by calling `register(project_name="streamlit-chatbot")`
# Save it to a variable called `tracer_provider`.
# -> Write your code below:


# TODO 4: Instrument the Groq client!
# Call `GroqInstrumentor().instrument(tracer_provider=tracer_provider)`
# -> Write your code below:


# -----------------------------------------------------------------------
# APP SETUP (Same as Exercise 2)
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
    
    # 💡 Because you instrumented Groq at the top of this file, 
    # this API call is now automatically tracked in Phoenix!
    response = client.chat.completions.create(
        messages=st.session_state.messages,
        model=MODEL
    )
    
    reply = response.choices[0].message.content
    
    with st.chat_message("assistant"):
        st.markdown(reply)
        
    st.session_state.messages.append({"role": "assistant", "content": reply})
