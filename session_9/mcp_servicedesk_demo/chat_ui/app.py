"""The employee's chat window. A thin client: it knows nothing about tools, MCP or the database.
It only sends a message to the agent API and shows the answer (same decoupled client as Session 3)."""
import os
import uuid

import requests
import streamlit as st

AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8020/api/v1/chat")
PHOENIX_URL = os.getenv("PHOENIX_PUBLIC_URL", "http://localhost:6006")
MAILPIT_URL = os.getenv("MAILPIT_PUBLIC_URL", "http://localhost:8025")
STAFF_URL = os.getenv("STAFF_PUBLIC_URL", "http://localhost:8502")

# The demo's "login": pick who you are. A real company would put single sign-on here.
EMPLOYEES = {
    "E-1001": "Priya Nair (account locked)",
    "E-1002": "Rahul Mehta",
    "E-1003": "Meera Iyer (account locked, security hold)",
}

EXAMPLE_MESSAGES = [
    "I'm locked out of my account",
    "My VPN keeps disconnecting",
    "I need Figma",
    "I got a new phone and need my authenticator moved",
    "I clicked a link in a strange email and typed my password",
    "What's the status of my tickets?",
]

st.set_page_config(page_title="KernMart IT Service Desk", page_icon="🛠️")
st.title("🛠️ KernMart IT Service Desk")
st.caption("An AI assistant that solves what it can and hands the rest to a human.")


def start_new_conversation():
    st.session_state.messages = []
    st.session_state.conversation_id = uuid.uuid4().hex[:12]


if "messages" not in st.session_state:
    start_new_conversation()

# ---- sidebar: who you are, example messages, links to the other tools -----------------------------
with st.sidebar:
    employee_id = st.selectbox("Signed in as", list(EMPLOYEES), format_func=lambda id: f"{id}  {EMPLOYEES[id]}")
    if st.session_state.get("last_employee") != employee_id:
        st.session_state.last_employee = employee_id
        start_new_conversation()
    if st.button("New conversation"):
        start_new_conversation()
        st.rerun()

    st.markdown("**Try one of these**")
    clicked_example = None
    for example in EXAMPLE_MESSAGES:
        if st.button(example, key=example):
            clicked_example = example

    st.markdown("---")
    st.markdown(f"[Staff console (humans)]({STAFF_URL})  \n[Traces (Phoenix)]({PHOENIX_URL})  \n"
                f"[Emails sent (Mailpit)]({MAILPIT_URL})")


def show_tool_calls(tool_calls):
    with st.expander(f"What the agent did ({len(tool_calls)} tool calls)"):
        for call in tool_calls:
            arguments = ", ".join(f"{key}={value!r}" for key, value in call["arguments"].items())
            st.code(f"{call['name']}({arguments})", language="python")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["text"])
        if message.get("tool_calls"):
            show_tool_calls(message["tool_calls"])

typed_message = st.chat_input("Describe your IT problem...")
user_message = clicked_example or typed_message

if user_message:
    st.session_state.messages.append({"role": "user", "text": user_message})
    with st.chat_message("user"):
        st.write(user_message)

    with st.chat_message("assistant"):
        with st.spinner("The assistant is working on it..."):
            try:
                response = requests.post(
                    AGENT_API_URL,
                    json={"employee_id": employee_id, "conversation_id": st.session_state.conversation_id,
                          "message": user_message},
                    timeout=120,
                )
                response.raise_for_status()
                answer = response.json()
            except requests.HTTPError:
                answer = None
                st.error(response.json().get("detail", "Something went wrong."))
            except requests.RequestException as problem:
                answer = None
                st.error(f"Could not reach the agent service: {problem}")

        if answer:
            st.write(answer["reply"])
            if answer["escalated"]:
                st.warning("This was handed to a human colleague. You will get an email when they reply.")
            show_tool_calls(answer["tool_calls"])
            st.session_state.messages.append(
                {"role": "assistant", "text": answer["reply"], "tool_calls": answer["tool_calls"]})
