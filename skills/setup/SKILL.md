---
name: setup
description: Set up CallBridge end to end on this Mac - install the package, build and install the two virtual audio cables, create the ElevenLabs agent (receptionist or sales), connect where call summaries go (Telegram, Slack, HubSpot, any CRM via webhook) and run a first test call with the user. Use when the user wants CallBridge running, or asks to set up an AI phone agent / AI receptionist on their iPhone number.
---

# Set up CallBridge

You are setting up CallBridge with the user, on their Mac. Go step by step, check each step worked before the next,
and explain each step in one plain sentence. The full manual is `docs/setup.md` in this plugin; read it first.

## Rules
- The user types secrets (API keys, tokens) into `.env` themselves. Never ask them to paste a key into the chat, and
  never print a key back. Tell them which line to fill and wait.
- `sudo` steps (installing the cables) are run by the user. Give them the exact command.
- Only call numbers the user gives you, for a test call: their own other phone, or someone who agreed.
- The agent must say it's an AI in its opening. Keep that in every prompt you write.

## Steps
1. **Check the machine.** macOS, an iPhone signed into the same Apple Account, Xcode installed (`xcodebuild -version`),
   Python 3.10+. Install with `pipx install git+https://github.com/Digitaicoil/callbridge` (or `uv tool install`), or
   `pip install -e .` from a clone.
2. **Calls from iPhone.** Walk them through: iPhone → Settings → Apps → Phone → Calls on Other Devices → their Mac on;
   Mac → Phone (or FaceTime) app → Settings → Calls from iPhone on. Ask them to place one normal call from the Mac
   to confirm it works.
3. **Cables.** Run `callbridge cables build`, then ask the user to run `sudo bash scripts/install-cables.sh` (from
   the repo, or `callbridge cables install`, which asks for their password).
4. **Permissions.** Their terminal app needs Microphone and Accessibility (System Settings → Privacy & Security).
   Without Microphone the audio stream hangs; without Accessibility the call buttons can't be pressed.
5. **ElevenLabs.** They create an API key at elevenlabs.io and put it in `~/.config/callbridge/.env` as
   `ELEVENLABS_API_KEY=` (copy `.env.example` there first). Then interview them briefly: business name, owner name,
   what callers usually ask, which language, inbound receptionist, outbound sales or both. Run
   `callbridge agent create receptionist --business ... --owner ... --about ... --language ...` and have them add
   the printed id line to `.env`.
6. **Where calls go.** Ask where they want summaries: Telegram, Slack, HubSpot, or another CRM through a webhook
   (Zapier/Make/n8n). Set `CALLBRIDGE_SINKS` and the matching lines (see `docs/integrations.md`).
7. **Keep awake.** A locked Mac can't press call buttons. Offer the keep-awake launch agent (`scripts/keep-awake.plist`).
8. **Doctor.** `callbridge doctor` until everything is green.
9. **Test call.** Receptionist: run `callbridge answer` and ask them to call their iPhone number from another phone.
   Sales: `callbridge call <their other phone> "test call"`. Afterwards check the summary arrived where they chose.
10. Point them to `/callbridge:tune-agent` to shape what the agent says.
