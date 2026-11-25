# Setup

About 20 minutes, most of it waiting for Xcode. If you use Claude Code, `/callbridge:setup` does this with you.

1. [Install CallBridge](#1-install-callbridge)
2. [Turn on Calls from iPhone](#2-turn-on-calls-from-iphone)
3. [Build and install the audio cables](#3-build-and-install-the-audio-cables)
4. [Give your terminal two permissions](#4-give-your-terminal-two-permissions)
5. [Create your agent](#5-create-your-agent)
6. [Choose where calls go](#6-choose-where-calls-go)
7. [Keep the Mac awake](#keep-awake)
8. [Check and test](#8-check-and-test)

## 1. Install CallBridge

```bash
pipx install git+https://github.com/Digitaicoil/callbridge
# or
uv tool install git+https://github.com/Digitaicoil/callbridge
# or, to hack on it
git clone https://github.com/Digitaicoil/callbridge && cd callbridge && pip install -e '.[dev]'
```

## 2. Turn on Calls from iPhone

The Mac places and receives calls through your iPhone. Both must use the same Apple Account and be on the same Wi-Fi.

- **iPhone:** Settings → Apps → Phone → **Calls on Other Devices** → turn on, and switch on your Mac.
- **Mac:** open the **Phone** app (macOS 26) or **FaceTime** (older) → Settings → **Calls from iPhone** → on.
  If you have several lines, set the line the agent should use under *Start calls from*.

Place one normal call from the Mac to check it works before going on.

## 3. Build and install the audio cables

CallBridge needs two virtual audio devices:

| Device | Carries | During a call it is the Mac's… |
|---|---|---|
| `CallBridgeCall 2ch` | the caller's voice | default **output** |
| `CallBridgeAgent 2ch` | the agent's voice | default **input** |

They are [BlackHole](https://github.com/ExistentialAudio/BlackHole) drivers built from source on your Mac with
these names (BlackHole is GPL-3.0; CallBridge doesn't ship its binaries). You need **Xcode** from the App Store.

```bash
sudo xcode-select -s /Applications/Xcode.app      # once, if xcodebuild complains
callbridge cables build                            # optional: CALLBRIDGE_DEVELOPMENT_TEAM=YOURTEAMID to sign with your team
callbridge cables install                          # asks for your password; sound drops for a second
```

Check: `System Settings → Sound` now lists both devices. Remove them any time with `sudo bash scripts/uninstall-cables.sh`.

> Already have the plain BlackHole 2ch installed? Fine; CallBridge's cables live alongside it.

## 4. Give your terminal two permissions

System Settings → Privacy & Security, for the app you run `callbridge` from (Terminal, iTerm, VS Code…):

- **Microphone**: without it the audio stream silently hangs.
- **Accessibility**: CallBridge presses the *Call* / *Accept* buttons on the Mac's call banner.

macOS asks the first time; if you clicked *Don't allow*, toggle it on there and restart the terminal.

## 5. Create your agent

Get an API key at [elevenlabs.io](https://elevenlabs.io) → Settings → API Keys, then:

```bash
mkdir -p ~/.config/callbridge
cp .env.example ~/.config/callbridge/.env           # or download it from the repo
open -e ~/.config/callbridge/.env                   # fill in ELEVENLABS_API_KEY
```

Create a **receptionist** (answers calls) and/or a **sales** agent (makes calls):

```bash
callbridge agent create receptionist --business "Bright Smile Dental" --owner "Dana" --agent-name "Ava" \
  --about "Dental clinic in Austin. Sun-Thu 9-18. Cleanings, whitening, implants. Parking behind the building."

callbridge agent create sales --business "Bright Smile Dental" --owner "Dana" --agent-name "Ava" \
  --about "We remind past patients about their 6-month check-up and offer a slot."
```

Each prints a line like `CALLBRIDGE_INBOUND_AGENT_ID=...`; paste it into the `.env`.

Options: `--language` (ISO code, e.g. `he`, `es`, `de`; default `en`) and `--voice` (any voice id from your
ElevenLabs library). The prompts live in [`agents/`](../agents); see [shaping the agent](../README.md#shape-what-the-agent-says).

## 6. Choose where calls go

Set `CALLBRIDGE_SINKS` in the `.env`, e.g. `jsonl,telegram,hubspot`. See [integrations.md](integrations.md).

## Keep awake

A locked Mac can't press the call buttons, so calls fail. Keep the display awake while CallBridge runs:

```bash
cp scripts/keep-awake.plist ~/Library/LaunchAgents/audio.callbridge.keepawake.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/audio.callbridge.keepawake.plist
# undo: launchctl bootout gui/$(id -u)/audio.callbridge.keepawake
```

Also on the iPhone: keep it charging and unlocked if you can (a locked iPhone sometimes keeps the call on the phone).

## 8. Check and test

```bash
callbridge doctor
```

Then a test you control:

- **Receptionist:** `callbridge answer`, and call your iPhone number from another phone. To switch it on and off
  without a terminal, run `callbridge menubar` once from your CallBridge folder: a phone icon appears in the menu bar.
- **Outbound:** `callbridge call <your other phone> "test call"`.

The transcript prints live; the record lands wherever your sinks point.

### Run the receptionist all the time

```bash
# ~/Library/LaunchAgents/audio.callbridge.answer.plist: copy from examples/answer.plist and fix the path
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/audio.callbridge.answer.plist
```
