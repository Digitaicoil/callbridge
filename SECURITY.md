# Security policy

Please report vulnerabilities privately, not in a public issue: use GitHub's
[private vulnerability reporting](https://github.com/Digitaicoil/callbridge/security/advisories/new). We aim to reply within 3 working days.

In scope: anything that could leak API keys, call transcripts or recordings, let a third party trigger calls, or let
the agent be used to call people who didn't agree to it.

Your keys live only in your local `.env`; CallBridge sends them only to the service they belong to (ElevenLabs,
Telegram, Slack, HubSpot, your webhook).
