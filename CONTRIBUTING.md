# Contributing

Thanks for helping. CallBridge is small on purpose: one call at a time, plain Python, few dependencies.

## Dev setup

```bash
git clone https://github.com/Digitaicoil/callbridge && cd callbridge
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest && .venv/bin/ruff check .
```

Tests don't need a phone, cables or an API key. Anything that touches hardware lives in `macos.py` and `call.py`;
keep logic you can test (audio, records, sinks, agents) out of them.

## Good first contributions

- A new sink (Pipedrive, Google Sheets, Notion, Airtable…): one file in `callbridge/sinks/`, one test with
  `httpx.MockTransport`. See [docs/integrations.md](docs/integrations.md#write-your-own-sink).
- Banner button labels for macOS in your language.
- Ring-back tones of your country, if the ring gate misses them.
- Agent templates for a kind of business (`agents/*.md`), with the AI disclosure kept.

## Pull requests

- One change per PR, with a test when there's logic.
- `pytest` and `ruff check .` pass (CI runs both).
- Never commit `.env`, keys, phone numbers, device ids or recordings. CI scans for them.
- Describe how you tested a hardware change (macOS version, iPhone model, what you called).

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
