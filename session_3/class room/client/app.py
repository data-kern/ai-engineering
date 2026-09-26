import streamlit as st
import requests

st.set_page_config(page_title="RiverBank AI Assistant", page_icon="🏦")
st.title("🏦 RiverBank AI Assistant")
st.caption("Powered by decoupled FastAPI on Kubernetes")

API_URL = "http://localhost:8000/api/v1/chat"

# Initialize session chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input box
user_input = st.chat_input("Ask a question about RiverBank...")

if user_input:
    # 1. Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 2. Call the Kubernetes AI Service over HTTP
    with st.chat_message("assistant"):
        with st.spinner("Contacting AI service on Kubernetes..."):
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "message": user_input,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    reply = data["reply"]
                    latency = data.get("latency_ms", 0)
                    model = data.get("model", "unknown")
                    
                    st.write(reply)
                    st.caption(f"⚡ {latency} ms | 🤖 {model}")
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    st.error(f"Service returned error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Failed to reach AI service: {e}")
