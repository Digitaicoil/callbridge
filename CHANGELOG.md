# Changelog

## 0.1.0 (2026-11-17)

First public release.

- Outbound calls (`callbridge call`) and receptionist mode for incoming calls (`callbridge answer`) on your iPhone
  number through macOS *Calls from iPhone*.
- Two virtual audio cables built from BlackHole's source (`callbridge cables build|install`).
- Ring gate (the agent never talks to the ring tone), barge-in, remote hang-up detection, reliable hang-up.
- Agent templates (receptionist, sales) with enforced AI disclosure; `callbridge agent create|push|show|calls`.
- Structured call records (name, reason, callback time, outcome) via ElevenLabs data collection.
- Sinks: JSONL, Telegram, Slack, HubSpot, webhook (Zapier, Make, n8n, any CRM).
- Do-not-call list, optional stereo call recording, `callbridge doctor`.
- Claude Code plugin: `/callbridge:setup`, `/callbridge:tune-agent`.
