"""POST the whole call record as JSON to any URL: Zapier, Make, n8n, Pipedrive/Monday/Salesforce automations,
or your own backend. CALLBRIDGE_WEBHOOK_URL, optional CALLBRIDGE_WEBHOOK_SECRET (sent as X-CallBridge-Secret)."""
import httpx


def send(record, env: dict) -> None:
    headers = {"X-CallBridge-Secret": env["CALLBRIDGE_WEBHOOK_SECRET"]} if env.get("CALLBRIDGE_WEBHOOK_SECRET") else {}
    httpx.post(env["CALLBRIDGE_WEBHOOK_URL"], json=record.as_dict(), headers=headers, timeout=30).raise_for_status()
