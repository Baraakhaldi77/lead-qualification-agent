"""Gmail API wrapper - send only (gmail.send scope, no inbox read access)."""

import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build


def build_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)


def send_email(service, to, subject, body, sender_name=None):
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if sender_name:
        message["from"] = sender_name
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
