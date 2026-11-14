"""Telling humans. Two real channels:

  email  an SMTP server. In this demo it is Mailpit (a real SMTP server that keeps every message
         and shows it at http://localhost:8025). At work you point SMTP_HOST at your mail relay.
  slack  an incoming webhook. Optional: set SLACK_WEBHOOK_URL to your own Slack webhook.

Each function returns a short status text instead of raising: a failed alert must never hide
the fact that the ticket was escalated. The caller decides what to tell the user.
"""
import os
import smtplib
from email.message import EmailMessage

import httpx

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "0") == "1"
MAIL_FROM = os.getenv("MAIL_FROM", "servicedesk-agent@kernmart.example")
SERVICE_DESK_EMAIL = os.getenv("SERVICE_DESK_EMAIL", "servicedesk@kernmart.example")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_email(to, subject, body):
    message = EmailMessage()
    message["From"] = MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as smtp:
            if SMTP_STARTTLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
        return "sent"
    except (OSError, smtplib.SMTPException) as problem:
        return f"failed: {problem}"


def post_to_slack(text):
    if not SLACK_WEBHOOK_URL:
        return "not_configured"
    try:
        response = httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        response.raise_for_status()
        return "sent"
    except httpx.HTTPError as problem:
        return f"failed: {problem}"


def alert_service_desk(ticket, employee, reason, urgency):
    """Email and Slack the human queue. Returns what happened on each channel."""
    headline = f"[{urgency.upper()}] {ticket['ticket_id']}: {ticket['summary']}"
    body = (
        f"{headline}\n\n"
        f"Employee: {employee['name']} ({employee['employee_id']}, {employee['email']})\n"
        f"Category: {ticket['category']}\n"
        f"Why the agent escalated: {reason}\n\n"
        f"Details from the conversation:\n{ticket['details']}\n"
    )
    channels = {
        "email": send_email(SERVICE_DESK_EMAIL, headline, body),
        "slack": post_to_slack(f":rotating_light: {headline}\nEmployee: {employee['name']}\nReason: {reason}"),
    }
    channels["any_sent"] = "sent" in (channels["email"], channels["slack"])
    return channels
