from app import llm
from app.pii import redact


def test_redact():
    r = redact("mail a.b@x.com call +91 98765 43210 card 4111 1111 1111 1111 PAN ABCDE1234F")
    for leak in ("a.b@x.com", "98765", "4111", "ABCDE1234F"):
        assert leak not in r


def test_parse_strips_think_and_validates():
    raw = '<think>hmm</think>```json\n{"category":"Billing","priority":"urgent","confidence":2,"reply":" Hi "}```'
    assert llm.parse(raw) == {"category": "billing", "priority": "medium", "confidence": 1.0, "reply": "Hi"}


def test_rules():
    base = {"category": "billing", "priority": "low", "confidence": 0.9, "reply": "x"}
    assert not llm.apply_rules(dict(base), "refund please", 0.5)["needs_human"]
    assert llm.apply_rules(dict(base), "refund please", 5)["needs_human"]
    r = llm.apply_rules(dict(base), "my account was hacked", 0.5)
    assert r["priority"] == "critical" and r["needs_human"]
