"""Post the call summary to a Telegram chat (a group topic too). Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID;
TELEGRAM_THREAD_ID is optional (a forum topic)."""
import httpx


def send(record, env: dict) -> None:
    body = {"chat_id": env["TELEGRAM_CHAT_ID"], "text": record.text()[:4000]}
    if env.get("TELEGRAM_THREAD_ID"):
        body["message_thread_id"] = int(env["TELEGRAM_THREAD_ID"])
    r = httpx.post(f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/sendMessage", json=body, timeout=30)
    r.raise_for_status()
