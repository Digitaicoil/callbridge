import json

import httpx

from callbridge.record import CallRecord
from callbridge.sinks import dispatch, hubspot, jsonl, telegram, webhook


def rec(**kw):
    base = dict(direction="inbound", number="+15551234567", started_at="2026-11-17T10:00:00", duration_s=42,
                summary="Wants a cleaning on Tuesday.", data={"caller_name": "Dana Levi", "outcome": "message_taken"},
                transcript=["Agent: Hi", "Caller: Hello"])
    base.update(kw)
    return CallRecord(**base)


def test_text_has_headline_summary_fields_and_transcript():
    t = rec().text()
    assert t.startswith("📞 ← Dana Levi · 42s")
    assert "Wants a cleaning" in t and "• outcome: message_taken" in t and "Caller: Hello" in t


def test_jsonl_appends(tmp_path):
    p = tmp_path / "calls.jsonl"
    jsonl.send(rec(), {"CALLBRIDGE_JSONL": str(p)})
    jsonl.send(rec(number="+2"), {"CALLBRIDGE_JSONL": str(p)})
    lines = p.read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["data"]["caller_name"] == "Dana Levi"


def test_dispatch_isolates_failures(tmp_path):
    out = dispatch(rec(), ["jsonl", "telegram", "nope"], {"CALLBRIDGE_JSONL": str(tmp_path / "c.jsonl")})
    assert out["jsonl"] == "ok" and out["telegram"].startswith("failed") and out["nope"] == "unknown sink"


def test_telegram_posts_to_topic(monkeypatch):
    seen = {}

    def post(url, json, timeout):
        seen.update(url=url, body=json)
        return httpx.Response(200, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    telegram.send(rec(), {"TELEGRAM_BOT_TOKEN": "T", "TELEGRAM_CHAT_ID": "-100", "TELEGRAM_THREAD_ID": "7"})
    assert seen["url"].endswith("/botT/sendMessage") and seen["body"]["message_thread_id"] == 7


def test_webhook_sends_full_record_and_secret(monkeypatch):
    seen = {}

    def post(url, json, headers, timeout):
        seen.update(body=json, headers=headers)
        return httpx.Response(200, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    webhook.send(rec(), {"CALLBRIDGE_WEBHOOK_URL": "https://example.com/hook", "CALLBRIDGE_WEBHOOK_SECRET": "s"})
    assert seen["body"]["number"] == "+15551234567" and seen["headers"] == {"X-CallBridge-Secret": "s"}


def test_hubspot_creates_contact_then_note(monkeypatch):
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.url.path, json.loads(req.content)))
        if req.url.path.endswith("/contacts/search"):
            return httpx.Response(200, json={"results": []})
        if req.url.path.endswith("/contacts"):
            return httpx.Response(201, json={"id": "c1"})
        return httpx.Response(201, json={"id": "n1"})
    monkeypatch.setattr(hubspot, "_client", lambda env: httpx.Client(transport=httpx.MockTransport(handler)))
    hubspot.send(rec(), {"HUBSPOT_TOKEN": "x"})
    paths = [p for p, _ in calls]
    assert paths == ["/crm/v3/objects/contacts/search", "/crm/v3/objects/contacts", "/crm/v3/objects/notes"]
    assert calls[1][1]["properties"] == {"phone": "+15551234567", "firstname": "Dana", "lastname": "Levi"}
    assert calls[2][1]["associations"][0]["to"]["id"] == "c1"


def test_webhook_sends_bearer_token_for_crm_apis(monkeypatch):
    seen = {}

    def post(url, json, headers, timeout):
        seen.update(headers=headers)
        return httpx.Response(200, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    webhook.send(rec(), {"CALLBRIDGE_WEBHOOK_URL": "https://example.com/hook", "CALLBRIDGE_WEBHOOK_TOKEN": "k"})
    assert seen["headers"] == {"Authorization": "Bearer k"}
