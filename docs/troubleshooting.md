# Troubleshooting

Start with `callbridge doctor`. Then find the symptom below. Every one of these happened to us while building it.

### The call connects but there's total silence (both sides)
- **The iPhone took the call.** A *locked* iPhone, or a UI-automation agent running on it (Appium's WebDriverAgent),
  can pull a Mac-placed call onto the phone. Keep the iPhone unlocked and charging during calls; if you use Appium,
  set `CALLBRIDGE_IPHONE_UDID` (from `xcrun devicectl list devices`) and CallBridge stops WebDriverAgent first.
- **Your terminal has no Microphone permission.** The input stream opens but never delivers audio. System Settings →
  Privacy & Security → Microphone → your terminal → on, then restart the terminal.

### "the Mac's screen is locked"
The *Call* / *Accept* buttons can't be pressed on a locked screen. Unlock it and install the
[keep-awake agent](setup.md#keep-awake).

### "no call prompt appeared"
- Calls from iPhone is off, or the iPhone isn't nearby / on the same Wi-Fi. Place a normal call from the Mac to check.
- Your terminal lacks **Accessibility** permission, so the banner button can't be pressed.
- macOS in another language: the button isn't called *Call*. Run `osascript callbridge/native/callbanner.applescript list`
  while the prompt is showing and tell us the label (PRs welcome); for incoming calls set `CALLBRIDGE_ACCEPT_LABELS`.

### The agent talks before anyone answers / talks to the ringing
The ring gate should hold it. If your network's ring-back tone sits outside 350–500 Hz, open an issue with your
country. Outbound agents must have an **empty first message** (the `sales` template does).

### The agent doesn't hear the caller well
The call audio arrives quiet; CallBridge lifts it ×12. If transcripts are poor, try `CALLBRIDGE_CALL_GAIN=18`; if the
caller sounds clipped, lower it.

### Replies feel slow
Most of the ~1.5 s is ElevenLabs' turn detection + LLM + TTS. In the agent's settings: turn eagerness *eager*,
streaming latency optimisation 4, a fast LLM (Haiku-class), a turbo TTS model. The templates already set these.

### The call doesn't end when the other side hangs up
CallBridge ends it after `CALLBRIDGE_SILENCE_HANGUP_SECONDS` (default 6) of pure digital silence. If your line
carries comfort noise after hang-up, open an issue.

### My Mac's microphone / speakers are still the cables after a crash
CallBridge restores them on exit, including Ctrl-C, `kill` and the menu-bar Off switch, and again the next time
`answer` starts. After a hard crash run `callbridge restore`, or pick your devices in System Settings → Sound.

### "another call is in progress"
One call per Mac. If nothing is running, a stale process holds the lock: `pkill -f "callbridge (call|answer)"`.
