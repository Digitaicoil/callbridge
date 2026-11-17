"""POST the whole call record as JSON to any URL: Zapier, Make, n8n, Pipedrive/Monday/Salesforce automations,
or your own backend / CRM API.
CALLBRIDGE_WEBHOOK_URL; optional CALLBRIDGE_WEBHOOK_SECRET (sent as X-CallBridge-Secret) and
CALLBRIDGE_WEBHOOK_TOKEN (sent as Authorization: Bearer ..., for APIs that take an API key)."""
import httpx


def send(record, env: dict) -> None:
    headers = {}
    if env.get("CALLBRIDGE_WEBHOOK_SECRET"):
        headers["X-CallBridge-Secret"] = env["CALLBRIDGE_WEBHOOK_SECRET"]
    if env.get("CALLBRIDGE_WEBHOOK_TOKEN"):
        headers["Authorization"] = f"Bearer {env['CALLBRIDGE_WEBHOOK_TOKEN']}"
    httpx.post(env["CALLBRIDGE_WEBHOOK_URL"], json=record.as_dict(), headers=headers, timeout=30).raise_for_status()
