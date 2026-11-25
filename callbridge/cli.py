"""callbridge: an AI voice agent on your own iPhone number.

  callbridge doctor                          check everything a call needs
  callbridge call +15551234567 "context"     the outbound agent calls this number now
  callbridge answer                          receptionist: answer incoming calls until Ctrl-C
  callbridge menubar                         the same, switched on and off from the Mac's menu bar
  callbridge restore                         give the Mac its own mic and speakers back
  callbridge agent create receptionist|sales --business ... --owner ... --about ...
  callbridge agent push receptionist|sales   upload your edited prompt (agents/*.md)
  callbridge agent calls [N]                 recent calls: length, credits, summary
  callbridge dnc add|list [NUMBER]           the do-not-call list
  callbridge cables build|install            the two virtual audio cables
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import __version__, dnc
from .config import Settings

ROOT = Path(__file__).resolve().parent.parent


def cmd_doctor(s: Settings, _a) -> int:
    from . import macos
    ok = True

    def check(label: str, good: bool, fix: str = "") -> None:
        nonlocal ok
        ok &= good
        print(f"{'✅' if good else '❌'} {label}" + ("" if good else f"\n   → {fix}"))

    check("macOS", sys.platform == "darwin", "CallBridge runs on a Mac (Calls from iPhone)")
    check("ELEVENLABS_API_KEY set", bool(s.api_key), "add it to .env (see .env.example)")
    check("an agent configured", bool(s.outbound_agent or s.inbound_agent), "run: callbridge agent create receptionist ...")
    try:
        names = macos.devices()["all"]
    except Exception as e:  # noqa: BLE001
        names = []
        print(f"   (audio device check failed: {e})")
    check(f"cable '{s.call_in}'", s.call_in in names, "run: callbridge cables build && callbridge cables install")
    check(f"cable '{s.agent_out}'", s.agent_out in names, "same as above")
    check("Mac screen unlocked", not macos.screen_locked(), "unlock it and keep it awake (docs/setup.md#keep-awake)")
    check("Phone app present", Path("/System/Applications/Phone.app").exists() or Path("/Applications/Phone.app").exists()
          or Path("/System/Applications/FaceTime.app").exists(), "update macOS")
    check("sinks: " + ", ".join(s.sinks), all(x in ("jsonl", "telegram", "slack", "webhook", "hubspot") for x in s.sinks),
          "CALLBRIDGE_SINKS takes jsonl,telegram,slack,webhook,hubspot")
    print("\nAlso check by hand (docs/setup.md): iPhone → Settings → Phone → Calls on Other Devices → this Mac;"
          "\nMac → Phone/FaceTime → Settings → Calls from iPhone; System Settings → Privacy → Accessibility and"
          "\nMicrophone → your terminal app.")
    return 0 if ok else 1


def cmd_call(s: Settings, a) -> int:
    from .call import exit_hard, preflight, run_call
    preflight(s)
    try:
        run_call(s, "outbound", "".join(c for c in a.number if c.isdigit() or c == "+"), a.context or "")
    finally:
        exit_hard(0)
    return 0


def cmd_answer(s: Settings, _a) -> int:
    from . import macos
    from .call import answer_forever
    try:
        answer_forever(s)
    except KeyboardInterrupt:
        macos.restore_devices((s.call_in, s.agent_out))
        print("stopped", flush=True)
    return 0


def cmd_restore(s: Settings, _a) -> int:
    from . import macos
    changed = macos.restore_devices((s.call_in, s.agent_out))
    print(", ".join(f"{k}: {v}" for k, v in changed.items()) or "nothing to restore: the Mac already uses its own devices")
    return 0


def cmd_menubar(s: Settings, _a) -> int:
    from . import macos
    app = macos.menubar_app()
    exe = Path(sys.argv[0]).resolve()   # the menu bar runs `<this callbridge> answer` here, so ./.env still loads
    subprocess.run(["open", "-n", str(app), "--args", str(exe), str(Path.cwd()), str(s.data_dir)], check=True)
    print("CallBridge is in the menu bar (the phone icon). Switch the agent on and off from there.")
    return 0


def _agent_id(s: Settings, template: str) -> str:
    return s.inbound_agent if template == "receptionist" else s.outbound_agent


def cmd_agent(s: Settings, a) -> int:
    from . import elevenlabs as el
    c = el.Client(s.api_key)
    if a.action == "create":
        values = {"business": a.business, "owner": a.owner, "agent_name": a.agent_name, "about": a.about}
        prompt, first = el.render(a.template, **values)
        body = el.agent_body(f"CallBridge {a.template} · {a.business}", prompt, first, language=a.language,
                             voice_id=a.voice or el.DEFAULT_VOICE)
        agent_id = c.create_agent(body)
        var = "CALLBRIDGE_INBOUND_AGENT_ID" if a.template == "receptionist" else "CALLBRIDGE_OUTBOUND_AGENT_ID"
        print(f"created {a.template} agent. Add this line to your .env:\n{var}={agent_id}")
        return 0
    if a.action == "push":
        agent_id = _agent_id(s, a.template)
        values = {"business": a.business, "owner": a.owner, "agent_name": a.agent_name, "about": a.about}
        prompt, first = el.render(a.template, **values)
        c.update_prompt(agent_id, prompt, first if a.template == "receptionist" else None)
        print("pushed: the next call uses the new prompt")
        return 0
    if a.action == "show":
        cfg = c.agent(_agent_id(s, a.template))["conversation_config"]
        print(json.dumps({"voice": cfg["tts"].get("voice_id"), "tts": cfg["tts"].get("model_id"),
                          "llm": cfg["agent"]["prompt"].get("llm"), "language": cfg["agent"].get("language"),
                          "first_message": cfg["agent"].get("first_message")}, ensure_ascii=False, indent=1))
        return 0
    if a.action == "calls":
        for x in c.calls(_agent_id(s, a.template), a.n):
            d = c.conversation(x["conversation_id"])
            m, an = d.get("metadata") or {}, d.get("analysis") or {}
            print(f"{datetime.fromtimestamp(x['start_time_unix_secs']):%d/%m %H:%M}  {m.get('call_duration_secs')}s  "
                  f"{m.get('cost')} credits  {(an.get('transcript_summary') or '')[:120]}")
        return 0
    return 2


def cmd_dnc(s: Settings, a) -> int:
    if a.action == "add":
        dnc.add(s.dnc_file, a.number)
        print(f"added; {s.dnc_file}")
    else:
        print(s.dnc_file.read_text() if s.dnc_file.is_file() else "(empty)")
    return 0


def cmd_cables(_s: Settings, a) -> int:
    script = ROOT / "scripts" / ("build-cables.sh" if a.action == "build" else "install-cables.sh")
    cmd = ["/bin/bash", str(script)]
    if a.action == "install" and os.geteuid() != 0:
        cmd = ["sudo", *cmd]
    return subprocess.call(cmd)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="callbridge", description="An AI voice agent on your own iPhone number.")
    p.add_argument("--version", action="version", version=f"callbridge {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check everything a call needs")
    c = sub.add_parser("call", help="the outbound agent calls a number now")
    c.add_argument("number")
    c.add_argument("context", nargs="?", help="who they are and why you're calling; the agent hears it first")
    sub.add_parser("answer", help="receptionist mode: answer incoming calls")
    sub.add_parser("menubar", help="a menu-bar switch that turns the receptionist on and off")
    sub.add_parser("restore", help="give the Mac its own mic and speakers back")
    ag = sub.add_parser("agent", help="create and tune the ElevenLabs agents")
    ag.add_argument("action", choices=["create", "push", "show", "calls"])
    ag.add_argument("template", nargs="?", default="receptionist", choices=["receptionist", "sales"])
    ag.add_argument("n", nargs="?", type=int, default=10)
    ag.add_argument("--business", default="our business")
    ag.add_argument("--owner", default="the owner")
    ag.add_argument("--agent-name", default="Ava")
    ag.add_argument("--about", default="(add what callers usually ask about: services, hours, location)")
    ag.add_argument("--language", default="en")
    ag.add_argument("--voice", default="")
    d = sub.add_parser("dnc", help="the do-not-call list")
    d.add_argument("action", choices=["add", "list"])
    d.add_argument("number", nargs="?")
    cb = sub.add_parser("cables", help="build or install the virtual audio cables")
    cb.add_argument("action", choices=["build", "install"])
    return p


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    s = Settings.from_env()
    return {"doctor": cmd_doctor, "call": cmd_call, "answer": cmd_answer, "agent": cmd_agent,
            "dnc": cmd_dnc, "cables": cmd_cables,
            "menubar": cmd_menubar, "restore": cmd_restore}[a.cmd](s, a)


if __name__ == "__main__":
    raise SystemExit(main())
