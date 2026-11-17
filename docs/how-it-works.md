# How it works

## The call path

```
caller ──cellular──▶ iPhone ──Calls from iPhone──▶ Mac (Phone app)
                                                   │ default output = CallBridgeCall 2ch
                                                   ▼
                                       callbridge  ── 48 kHz → 16 kHz PCM ──▶ ElevenLabs agent
                                                   ◀── 16 kHz → 48 kHz ─────
                                                   │ CallBridgeAgent 2ch = default input
                                                   ▼
                                    Phone app sends it to the caller as "your microphone"
```

Everything stays digital: no speaker plays into a microphone, so there's no echo and no feedback.

## A call, step by step

**Outbound** (`callbridge call NUMBER "context"`)

1. Checks: number not on the do-not-call list, cables installed, Mac unlocked, no other call running (a file lock).
2. Remembers your audio devices and switches the defaults to the two cables.
3. Opens a session with the ElevenLabs agent and passes your context as a contextual update.
4. Opens `tel://NUMBER` in the Phone app and presses the *Call* button on the Mac's banner (AppleScript + Accessibility).
5. **Ring gate:** until someone answers, the agent hears silence. The gate opens after ~160 ms of sound that isn't a
   ring-back tone (350–500 Hz), so the agent never talks to the ringing.
6. The conversation runs. When the caller talks over the agent, its queued audio is dropped (barge-in).
7. The call ends when the agent uses its `end_call` tool, the other side hangs up (the line drops to pure digital
   silence for 6 s), or the max duration is reached.
8. **Hang up:** if the call is still at the prompt, press *Cancel*; otherwise restart `callservicesd` (the Mac's call
   panel hides a few seconds into a call, so its End button isn't reliably reachable; restarting the service ends
   the call on both devices and launchd brings it back at once).
9. Restores your audio devices, fetches ElevenLabs' analysis (summary + extracted fields), sends the record to every sink.

**Inbound** (`callbridge answer`) polls the Mac's call banners once a second. When an *Accept* button appears it reads
the caller ID, switches the audio, presses *Accept*, then starts the agent, whose first message greets the caller.
Same hang-up detection and record. Then it waits for the next call.

## Why these choices

| Choice | Why |
|---|---|
| Calls from iPhone, not a SIP trunk | Your real number, no porting, no per-minute telecom fees. |
| Two separate cables | One for each direction, so the agent never hears itself. |
| 20 ms audio blocks | Shortest round trip; most of the remaining delay (~1.5 s) is the agent's turn detection, LLM and TTS. |
| ×12 input gain | The call arrives quiet (peaks around 0.02); speech recognition does much better with it lifted. |
| `pcm_16000` both ways | No codec work in Python; ElevenLabs' native format. |
| `callservicesd` restart to hang up | The only reliable way found to end a Mac-relayed call from code. |
| Data collection on the agent | ElevenLabs extracts name / reason / callback time / outcome, so sinks get structured fields. |

## Files

| Path | What |
|---|---|
| `callbridge/call.py` | one call, inbound or outbound; the receptionist loop |
| `callbridge/audio.py` | the cable audio interface, ring gate, recorder |
| `callbridge/macos.py` | audio devices, call banners, dial / accept / hang up |
| `callbridge/elevenlabs.py` | create and update agents, fetch analysis |
| `callbridge/sinks/` | where records go |
| `callbridge/native/` | `audiodev.swift` (default devices), `callbanner.applescript` (banner buttons) |
| `agents/` | the prompt templates |
| `scripts/` | cable build/install, keep-awake |
