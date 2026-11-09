import base64, os
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from . import config as C

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _svc():
    creds = Credentials.from_authorized_user_file(C.GMAIL_TOKEN, SCOPES) if os.path.exists(C.GMAIL_TOKEN) else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(C.GMAIL_CREDS, SCOPES).run_local_server(port=0)
        os.makedirs(os.path.dirname(C.GMAIL_TOKEN) or ".", exist_ok=True)
        open(C.GMAIL_TOKEN, "w").write(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _body(p):
    if p.get("mimeType") == "text/plain" and p["body"].get("data"):
        return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", "ignore")
    for s in p.get("parts", []):
        if t := _body(s):
            return t
    return ""


def _headers(m):
    return {h["name"].lower(): h["value"] for h in m["payload"]["headers"]}


def unread(limit=20):
    s = _svc()
    for i in s.users().messages().list(userId="me", q="is:unread in:inbox -from:me", maxResults=limit).execute().get("messages", []):
        m = s.users().messages().get(userId="me", id=i["id"], format="full").execute()
        yield {"id": m["id"], "text": _headers(m).get("subject", "") + "\n" + (_body(m["payload"]) or m.get("snippet", ""))}


def mark_read(mid):
    _svc().users().messages().modify(userId="me", id=mid, body={"removeLabelIds": ["UNREAD"]}).execute()


def reply(mid, body):
    s = _svc()
    m = s.users().messages().get(userId="me", id=mid, format="metadata").execute()
    h = _headers(m)
    msg = EmailMessage()
    msg["To"] = h.get("reply-to") or h["from"]
    subj = h.get("subject", "")
    msg["Subject"] = subj if subj.lower().startswith("re:") else "Re: " + subj
    if "message-id" in h:
        msg["In-Reply-To"] = msg["References"] = h["message-id"]
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    s.users().messages().send(userId="me", body={"raw": raw, "threadId": m["threadId"]}).execute()
