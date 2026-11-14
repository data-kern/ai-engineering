"""The human side of "escalate to a human". This is where a service-desk person sees what the agent handed over.

In a real company this screen is your ticketing tool (ServiceNow, Jira Service Management, Zendesk). Here it is a
small page over the same PostgreSQL database. It does NOT go through MCP: MCP is how AGENTS reach the system.
People use the system's own screen.
"""
import os

import pandas as pd
import streamlit as st

from servicedesk_core import desk

STAFF_ID = os.getenv("STAFF_ID", "S-9001")
MAILPIT_URL = os.getenv("MAILPIT_PUBLIC_URL", "http://localhost:8025")
URGENCY_ICON = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}

st.set_page_config(page_title="Service desk staff console", page_icon="🧑‍💻", layout="wide")
st.title("🧑‍💻 Service desk staff console")
st.caption(f"Signed in as {STAFF_ID}. Tickets the AI agent could not solve land here, most urgent first.")

queue_tab, audit_tab = st.tabs(["Escalated tickets", "Audit log: every tool call"])

with queue_tab:
    if st.button("Refresh"):
        st.rerun()
    tickets = desk.staff_list_tickets(only_escalated=True)
    if not tickets:
        st.success("The queue is empty.")

    for ticket in tickets:
        icon = URGENCY_ICON.get(ticket["urgency"], "")
        title = f"{icon} {ticket['ticket_id']}  |  {ticket['urgency']}  |  {ticket['employee_name']}  |  {ticket['summary']}"
        with st.expander(title):
            st.markdown(f"**Employee:** {ticket['employee_name']} ({ticket['employee_id']}, {ticket['employee_email']})")
            st.markdown(f"**Why the agent escalated:** {ticket['escalation_reason']}")
            st.markdown("**What the agent knew:**")
            st.text(ticket["details"])

            reply_text = st.text_area("Your reply to the employee", key=f"reply-{ticket['ticket_id']}")
            send_only, send_and_resolve = st.columns(2)
            if send_only.button("Send reply", key=f"send-{ticket['ticket_id']}") and reply_text:
                desk.staff_reply(ticket["ticket_id"], STAFF_ID, reply_text, resolve=False)
                st.rerun()
            if send_and_resolve.button("Send reply and resolve", key=f"resolve-{ticket['ticket_id']}") and reply_text:
                desk.staff_reply(ticket["ticket_id"], STAFF_ID, reply_text, resolve=True)
                st.rerun()
    st.caption(f"Replies are emailed to the employee. See them in Mailpit: {MAILPIT_URL}")

with audit_tab:
    st.write("Written by the MCP server for every tool call, whichever client made it.")
    audit_rows = desk.recent_audit(100)
    if audit_rows:
        st.dataframe(pd.DataFrame(audit_rows)[["at", "employee_id", "tool", "outcome", "detail", "arguments", "duration_ms"]],
                     width="stretch", hide_index=True)
    else:
        st.info("No tool calls yet.")
