# Integrations

A finished call is one `CallRecord` ([`callbridge/record.py`](../callbridge/record.py)). Sinks deliver it.
Choose any mix in your `.env`:

```bash
CALLBRIDGE_SINKS=jsonl,telegram,hubspot,webhook
```

A failing sink is logged and never stops the others.

## The record

| Field | Example |
|---|---|
| `direction` | `inbound` / `outbound` |
| `number` | `+15551234567` (the caller ID shown on the Mac for inbound calls; may be a contact name) |
| `started_at` | `2026-11-17T10:42:05` |
| `duration_s` | `74` |
| `summary` | ElevenLabs' summary of the call |
| `data.caller_name` · `data.reason` · `data.callback_time` · `data.outcome` | extracted by the agent's data collection |
| `transcript` | `["Agent: …", "Caller: …"]` |
| `conversation_id` | the ElevenLabs conversation, for the dashboard |
| `recording` | WAV path when `CALLBRIDGE_RECORD=1` |
| `context` | what you told the agent before an outbound call |
| `script` | the agent's instructions (system prompt) the call ran with, so your CRM shows which script was used |

`outcome` is one of `meeting_booked`, `message_taken`, `callback_requested`, `not_interested`, `do_not_call`,
`no_answer`, `other`. A `do_not_call` outcome also adds the number to the do-not-call list.

## Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. Add the bot to your chat or group. Get the chat id (e.g. forward a message to [@userinfobot](https://t.me/userinfobot)
   or call `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. Optional: in a group with topics, the topic's `message_thread_id` puts calls in their own topic.

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-100...
TELEGRAM_THREAD_ID=...      # optional
```

## Slack

Create an [incoming webhook](https://api.slack.com/messaging/webhooks) for a channel:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## HubSpot

1. HubSpot → Settings → Integrations → **Private Apps** → Create.
2. Scopes: `crm.objects.contacts.read`, `crm.objects.contacts.write`.
3. Copy the token:

```bash
HUBSPOT_TOKEN=pat-...
```

Each call finds the contact by phone number (or creates one, with the name the agent heard) and attaches a note with
the summary, the extracted fields and the transcript.

## Webhook: any CRM, Zapier, Make, n8n

```bash
CALLBRIDGE_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/...
CALLBRIDGE_WEBHOOK_SECRET=some-long-random-string     # optional; sent as X-CallBridge-Secret
CALLBRIDGE_WEBHOOK_TOKEN=your-crm-api-key              # optional; sent as Authorization: Bearer (for your own CRM's API)
```

The whole record is POSTed as JSON. Recipes:

- **Zapier:** trigger *Webhooks by Zapier → Catch Hook*; action *Pipedrive / Salesforce / Monday / Google Sheets → Create*.
  Map `data.caller_name`, `number`, `summary`, `data.outcome`.
- **Make:** module *Webhooks → Custom webhook*, then your CRM's module.
- **n8n:** *Webhook* node (POST) → *IF* on `data.outcome` → CRM node. Check the secret header in the Webhook node.
- **Your backend:** see [`examples/webhook_receiver.py`](../examples/webhook_receiver.py), a 30-line receiver with
  secret checking and no dependencies.

## Local JSONL (default)

Every call is appended to `~/Library/Logs/callbridge/calls.jsonl` (change with `CALLBRIDGE_JSONL`). Handy for
`jq`, spreadsheets, or training data:

```bash
jq -r '[.started_at, .number, .data.outcome, .summary] | @tsv' ~/Library/Logs/callbridge/calls.jsonl
```

## Write your own sink

A sink is one function. Example: Pipedrive.

```python
# callbridge/sinks/pipedrive.py
import httpx

def send(record, env: dict) -> None:
    base = f"https://api.pipedrive.com/v1"
    params = {"api_token": env["PIPEDRIVE_TOKEN"]}
    person = httpx.post(f"{base}/persons", params=params, timeout=30,
                        json={"name": record.data.get("caller_name") or record.number, "phone": [record.number]})
    person.raise_for_status()
    httpx.post(f"{base}/notes", params=params, timeout=30,
               json={"person_id": person.json()["data"]["id"], "content": record.text()}).raise_for_status()
```

Register it in `callbridge/sinks/__init__.py` (`SINKS["pipedrive"] = pipedrive.send`), add a test with a mocked
transport (see `tests/test_sinks.py`), and open a PR.
