# Grievance RAG

Classifies grievances (category, priority), drafts a reply grounded in your knowledge base, escalates risky or uncertain ones to humans, and can auto-reply via Gmail.

```
Gmail -> [built-in poller | n8n] -> POST /grievance -> PII redaction -> Chroma retrieval -> DeepSeek-R1
         -> rules (urgent keywords, confidence, KB distance) -> SQLite ticket
         status "new" = confident reply ready; "needs_review" = a human approves via POST /tickets/{id}/approve
```

## Run
```
cp .env.example .env            # set LLM_KEY (or Ollama URL/model) and API_KEY
pip install -r requirements.txt
uvicorn app.main:app --port 8000
pytest
```
Try: `curl -X POST localhost:8000/grievance -H "X-API-Key: change-me" -H "content-type: application/json" -d '{"text":"Payment failed but money deducted"}'`

## API (header `X-API-Key`)
- `POST /grievance`
- `GET /tickets?status=needs_review` (sorted by priority)
- `GET /tickets/{id}`
- `POST /tickets/{id}/approve` (optional `{"reply": "edited"}`; sends the Gmail reply for Gmail tickets)
- `POST /kb/ingest`
- `GET /health`

## Gmail: choose one
1. **Built-in**: put OAuth `credentials.json` (Google Cloud, Gmail API, Desktop app) here and set `GMAIL_POLL_SECONDS=60`. Add `AUTO_SEND=true` to auto-reply to confident cases. The first run opens a browser for consent, so do that once outside Docker.
2. **n8n**: `docker compose up`, import `n8n_workflow.json`, attach Gmail credentials, and set the same API key in the HTTP nodes. Leave `GMAIL_POLL_SECONDS=0`.

## Knowledge base
Drop `.md` or `.txt` files in `kb/` (one policy per paragraph), then `POST /kb/ingest`.

## Safety
Emails, phones, card/ID/PAN numbers are redacted before storage or LLM calls. Message text is never logged. Critical or low-confidence tickets are never auto-sent. Keep the service on a private network.
