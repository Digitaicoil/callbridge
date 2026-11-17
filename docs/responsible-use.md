# Responsible use

An agent that holds a natural phone conversation on your real number is useful and easy to abuse. CallBridge is
for calls people expect or welcome: your own customers, people who asked to hear from you, people calling you.

## Built in

- **AI disclosure.** Every agent says it's an AI in its opening. `callbridge agent create` and `push` refuse a prompt
  without it. Don't remove this.
- **Do-not-call.** A caller who asks not to be called again is added to the do-not-call list (from the call's
  outcome, or by hand with `callbridge dnc add`). `callbridge call` refuses those numbers.
- **One call at a time.** CallBridge is not a dialer for lists. There is no bulk mode, on purpose.

## Your responsibility

Laws differ by country and change. Before outbound calls, check at least:

- **Consent for automated or AI calls.** In the US, the FCC treats AI-generated voices as "artificial" under the TCPA:
  calling someone with one generally needs their prior express consent. Many countries regulate marketing calls
  similarly (e.g. the EU's ePrivacy rules and national do-not-call registers, Israel's Communications Law section 30A).
- **Do-not-call registers** in your country.
- **Call recording.** Some places need consent from everyone on the call. `CALLBRIDGE_RECORD` is off by default.
- **Data protection.** Transcripts and recordings are personal data (GDPR and similar). Store them only as long as you need.

This page is not legal advice. When in doubt, ask a lawyer before you call people who didn't call you first.

## Don't

- Pretend the agent is a person.
- Call lists of people who never asked to hear from you.
- Impersonate another business or person.
