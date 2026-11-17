"""Post the call summary to Slack through an incoming webhook (SLACK_WEBHOOK_URL)."""
import httpx


def send(record, env: dict) -> None:
    httpx.post(env["SLACK_WEBHOOK_URL"], json={"text": record.text()[:3500]}, timeout=30).raise_for_status()
