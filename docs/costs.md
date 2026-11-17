# Costs

CallBridge itself is free and runs on your Mac. Three things can cost money:

| What | Cost |
|---|---|
| **ElevenLabs agent** (voice + speech recognition + LLM, billed together) | credits per call-second, see below |
| **Phone minutes** | your normal mobile plan; the call is an ordinary cellular call from your SIM |
| **Your CRM / Zapier / Slack** | whatever plan you already have |

## ElevenLabs credits

Measured on our own calls (Hebrew, `eleven_v4_turbo` voice, `claude-haiku-5-5` LLM, November 2026):

| Call length | Credits |
|---|---|
| 30–40 s | ~200–280 |
| 1 min | ~400 |
| 2.5–3 min | ~1,100 |

That's **about 6.7 credits per second**, LLM included. To turn it into money: `credits used ÷ credits in your plan ×
your monthly plan price`. Prices and the credit rate change; check [elevenlabs.io/pricing](https://elevenlabs.io/pricing)
and your own numbers with:

```bash
callbridge agent calls receptionist 20      # each call's length and credits
```

## Keeping it down

- Short replies (the templates cap them at ~20 words) and an `end_call` right after goodbye.
- `CALLBRIDGE_MAX_CALL_SECONDS` caps a runaway call (default 600).
- A cheaper LLM or TTS model in the ElevenLabs dashboard; test that the voice still sounds right in your language.
