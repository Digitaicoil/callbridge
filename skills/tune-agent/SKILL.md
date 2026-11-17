---
name: tune-agent
description: Shape what the CallBridge phone agent says - its opening, questions, what it offers, how it handles objections - by editing agents/receptionist.md or agents/sales.md and pushing it live, then checking recent calls to see how it went. Use when the user wants to change how their AI receptionist or sales agent talks, or asks why a call went badly.
---

# Tune the CallBridge agent

1. Ask what they want changed, or read the last calls first: `callbridge agent calls receptionist 10` (or `sales`)
   and the transcripts in `~/Library/Logs/callbridge/calls.jsonl`. Quote the exact lines that went wrong.
2. Edit the template (`agents/receptionist.md` or `agents/sales.md`). Keep it short; phone agents do best with
   plain numbered steps and a few hard rules. Change the smallest thing that fixes what they saw.
3. Keep the AI disclosure in the opening. `callbridge agent push` refuses a prompt without it.
4. Push it: `callbridge agent push receptionist --business ... --owner ... --about ...` (same values as at create).
5. Suggest one test call to hear the change.

Lessons that hold for most phone agents:
- One question at a time; replies under ~20 words.
- Build on the caller's last answer; never return to the script mid-conversation.
- Never claim to see a calendar or system the agent doesn't have.
- End the call with the end_call tool right after goodbye.
- For outbound calls, leave the first message empty so the agent waits for "hello".
