"""One phone call with the voice agent in it, outbound (we dial) or inbound (we answer)."""
from __future__ import annotations

import fcntl
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from . import dnc, macos
from .audio import CableAudio, Recorder
from .config import Settings
from .elevenlabs import Client
from .record import CallRecord
from .sinks import dispatch

AUDIO_TAG = re.compile(r"\s*\[[a-z][a-z \-]{0,30}\]\s*", re.I)
LOCK = Path("/tmp/callbridge-call.lock")


class Busy(RuntimeError):
    pass


def preflight(s: Settings, need_screen: bool = True) -> None:
    d = macos.devices()
    missing = [n for n in (s.call_in, s.agent_out) if n not in d["all"]]
    if missing:
        raise SystemExit(f"virtual cables not installed: {', '.join(missing)} (run: callbridge cables install)")
    if need_screen and macos.screen_locked():
        raise SystemExit("the Mac's screen is locked: the call prompt can't be pressed. Unlock it (docs/setup.md#keep-awake)")


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001
        pass


def _tell(conv, text: str, wait_s: float = 8.0) -> None:
    """Give the agent background mid-call. start_session() returns before the websocket is up, so wait for it;
    a call never fails over this."""
    end = time.time() + wait_s
    while time.time() < end:
        try:
            conv.send_contextual_update(text)
            return
        except RuntimeError:       # "Session not started or websocket not connected" (yet)
            time.sleep(0.1)
    print("could not give the agent the call's context (websocket never connected)", file=sys.stderr, flush=True)


def run_call(s: Settings, direction: str, number: str, context: str = "", place=None) -> CallRecord:
    """direction "outbound": dial `number`. "inbound": the call is ringing; `place` answers it.
    Returns the finished CallRecord (also saved and sent to every configured sink)."""
    from elevenlabs.client import ElevenLabs
    from elevenlabs.conversational_ai.conversation import Conversation

    agent_id = s.outbound_agent if direction == "outbound" else s.inbound_agent
    if not agent_id:
        raise SystemExit(f"CALLBRIDGE_{direction.upper()}_AGENT_ID is not set (run: callbridge agent create ...)")
    if direction == "outbound" and dnc.blocked(s.dnc_file, number):
        raise SystemExit(f"{number} is on the do-not-call list")

    lock = LOCK.open("w")
    try:                                   # one line, one call at a time
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise Busy("another call is in progress") from None

    prev = macos.devices()
    macos.remember_devices(prev, (s.call_in, s.agent_out))
    macos.audiodev("set-input", s.agent_out), macos.audiodev("set-output", s.call_in)
    record = CallRecord(direction=direction, number=number, started_at=datetime.now().isoformat(timespec="seconds"),
                        context=context)
    rec = Recorder() if s.record else None
    audio = CableAudio(s.call_in, s.agent_out, gain=s.gain, ring_gate=(direction == "outbound"), recorder=rec)
    done = threading.Event()

    def said(who: str, text: str) -> None:
        text = " ".join(AUDIO_TAG.sub(" ", text).split())     # v3/v4 voices write delivery tags like [warm]; not words
        if not text:
            return
        record.transcript.append(f"{who}: {text}")
        print(f"{who}: {text}", flush=True)

    conv = Conversation(ElevenLabs(api_key=s.api_key), agent_id, requires_auth=True, audio_interface=audio,
                        callback_agent_response=lambda t: said("Agent", t),
                        callback_user_transcript=lambda t: said("Caller", t),
                        callback_disconnect=lambda *_: done.set())
    t0 = time.time()
    try:
        macos.release_iphone(s.iphone_udid)   # both ways: a running WebDriverAgent pulls the call onto the phone
        if direction == "outbound":
            conv.start_session()           # listening before the phone rings; the ring gate keeps it quiet
            if context:
                _tell(conv, f"About this call: {context}")
            macos.dial(number)
        else:
            if place is not None:
                place()                    # press Accept, then start talking (the greeting needs a live line)
            conv.start_session()
            _tell(conv, f"Incoming call from {number}." + (f" {context}" if context else ""))
        t0 = time.time()

        def watch() -> None:               # the other side hung up: the line drops to pure digital silence
            while not done.wait(1):
                if audio.last_sound and time.time() - audio.last_sound > s.silence_hangup_s:
                    print("line went silent: the other side hung up", flush=True)
                    done.set()
        threading.Thread(target=watch, daemon=True).start()
        done.wait(s.max_call_s)
    finally:
        record.duration_s = int(time.time() - t0)
        t = threading.Thread(target=lambda: _quiet(conv.end_session), daemon=True)
        t.start(), t.join(10)              # a dead socket can hang end_session: never let it keep the call open
        macos.hang_up()
        for kind in ("input", "output"):   # give the Mac its own mic and speakers back (never "back" to a cable)
            if prev.get(kind) and prev[kind] not in (s.call_in, s.agent_out):
                macos.audiodev(f"set-{kind}", prev[kind])
        macos.restore_devices((s.call_in, s.agent_out))   # prev was itself a cable (an earlier crash): fall back
        fcntl.flock(lock, fcntl.LOCK_UN)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    if rec is not None:
        record.recording = str(rec.save(s.data_dir / "recordings" / f"{stamp}-{direction}.wav"))
    record.conversation_id = getattr(conv, "_conversation_id", None)
    if record.conversation_id:
        client = Client(s.api_key)
        record.summary, record.data, _ = client.analysis(record.conversation_id)
        record.script = client.script(agent_id)
    if (record.data or {}).get("outcome") == "do_not_call":
        dnc.add(s.dnc_file, number)
    results = dispatch(record, s.sinks)
    print(f"sent: {results}", flush=True)
    return record


def _stop(*_) -> None:
    raise KeyboardInterrupt


def stop_on_sigterm() -> None:
    """The menu-bar Off switch sends SIGTERM: stop like Ctrl-C, so a call in progress hangs up and the Mac gets its
    own mic and speakers back (run_call's finally)."""
    signal.signal(signal.SIGTERM, _stop)


def answer_forever(s: Settings, poll_s: float = 0.25) -> None:
    """Receptionist mode: wait for incoming calls on the Mac and answer each one with the inbound agent."""
    stop_on_sigterm()
    macos.restore_devices((s.call_in, s.agent_out))      # left on the cables by a call that never finished
    preflight(s)
    print(f"waiting for calls (accept buttons: {', '.join(s.accept_labels)}). Ctrl-C to stop.", flush=True)
    while True:
        caller = macos.incoming(s.accept_labels)
        if caller:
            print(f"ringing: {caller}", flush=True)
            try:
                run_call(s, "inbound", caller, place=lambda: macos.accept(s.accept_labels))
            except Busy:
                pass
            except Exception as e:  # noqa: BLE001  one bad call never stops the receptionist
                print(f"call failed: {e}", file=sys.stderr, flush=True)
            # The SDK's websocket threads outlive a call, and a second call in the same process stayed silent
            # (keepalive ping timeout). Start every call from a fresh process.
            sys.stdout.flush(), sys.stderr.flush()
            os.execv(sys.executable, [sys.executable, *sys.argv])
        time.sleep(poll_s)


def exit_hard(code: int = 0) -> None:
    sys.stdout.flush(), sys.stderr.flush()
    os._exit(code)     # the SDK's websocket/audio threads can keep the process alive after a call
