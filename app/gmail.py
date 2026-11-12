
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from . import config as C


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _svc():
    """Create Gmail API service using server-side OAuth refresh token."""

    required = {
        "GMAIL_CLIENT_ID": C.GMAIL_CLIENT_ID,
        "GMAIL_CLIENT_SECRET": C.GMAIL_CLIENT_SECRET,
        "GMAIL_REFRESH_TOKEN": C.GMAIL_REFRESH_TOKEN,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            "Missing Gmail OAuth environment variables: "
            + ", ".join(missing)
        )

    creds = Credentials(
        token=None,
        refresh_token=C.GMAIL_REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=C.GMAIL_CLIENT_ID,
        client_secret=C.GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )

    creds.refresh(Request())

    return build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )


def _body(payload):
    """Extract the first available plain-text email body."""

    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode(
                "utf-8", "ignore"
            )

    for part in payload.get("parts", []):
        content = _body(part)
        if content:
            return content

    return ""


def _headers(message):
    return {
        h["name"].lower(): h["value"]
        for h in message.get("payload", {}).get("headers", [])
    }


def unread(limit=20):
    service = _svc()

    messages = (
        service.users()
        .messages()
        .list(
            userId="me",
            q="is:unread in:inbox -from:me",
            maxResults=limit,
        )
        .execute()
        .get("messages", [])
    )

    for item in messages:
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="full",
            )
            .execute()
        )

        headers = _headers(message)

        yield {
            "id": message["id"],
            "text": (
                headers.get("subject", "")
                + "\n"
                + (
                    _body(message.get("payload", {}))
                    or message.get("snippet", "")
                )
            ),
        }


def mark_read(message_id):
    _svc().users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def reply(message_id, body):
    """Send a reply in the original Gmail conversation."""

    service = _svc()

    message = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Reply-To", "Subject", "Message-ID"],
        )
        .execute()
    )

    headers = _headers(message)

    recipient = headers.get("reply-to") or headers.get("from")

    if not recipient:
        raise RuntimeError("Original email sender address not found.")

    email = EmailMessage()
    email["To"] = recipient

    subject = headers.get("subject", "")
    email["Subject"] = (
        subject
        if subject.lower().startswith("re:")
        else "Re: " + subject
    )

    if "message-id" in headers:
        email["In-Reply-To"] = headers["message-id"]
        email["References"] = headers["message-id"]

    email.set_content(body)

    raw = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode("utf-8")

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw,
                "threadId": message["threadId"],
            },
        )
        .execute()
    )

    return result.get("id")
