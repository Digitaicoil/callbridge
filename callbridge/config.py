"""Settings come from environment variables, or from a .env file (./.env, then ~/.config/callbridge/.env).
Nothing secret lives in the code or the repo. See .env.example for every option."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ENV_FILES = (Path.cwd() / ".env", Path.home() / ".config" / "callbridge" / ".env")


def load_env(files=ENV_FILES) -> None:
    """Fill os.environ from the first .env files found. Real environment variables always win."""
    for f in files:
        if not f.is_file():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = re.split(r"(?:^|\s)#", v, maxsplit=1)[0]          # inline comments
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _list(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


@dataclass
class Settings:
    api_key: str = ""
    outbound_agent: str = ""
    inbound_agent: str = ""
    call_in: str = "CallBridgeCall 2ch"      # the caller's voice: the Mac's default OUTPUT during a call
    agent_out: str = "CallBridgeAgent 2ch"   # the agent's voice: the Mac's default INPUT during a call
    gain: float = 12.0
    max_call_s: int = 600
    silence_hangup_s: float = 6.0
    accept_labels: list[str] = field(default_factory=lambda: ["Accept", "Answer"])
    iphone_udid: str = ""                  # optional: stop WebDriverAgent on this iPhone before a call
    record: bool = False
    data_dir: Path = Path.home() / "Library" / "Logs" / "callbridge"
    dnc_file: Path = Path.home() / ".config" / "callbridge" / "do-not-call.txt"
    sinks: list[str] = field(default_factory=lambda: ["jsonl"])

    @classmethod
    def from_env(cls) -> Settings:
        load_env()
        e = os.environ.get
        s = cls(
            api_key=e("ELEVENLABS_API_KEY", ""),
            outbound_agent=e("CALLBRIDGE_OUTBOUND_AGENT_ID", ""),
            inbound_agent=e("CALLBRIDGE_INBOUND_AGENT_ID", ""),
            call_in=e("CALLBRIDGE_CALL_DEVICE", cls.call_in),
            agent_out=e("CALLBRIDGE_AGENT_DEVICE", cls.agent_out),
            gain=float(e("CALLBRIDGE_CALL_GAIN", cls.gain)),
            max_call_s=int(e("CALLBRIDGE_MAX_CALL_SECONDS", cls.max_call_s)),
            silence_hangup_s=float(e("CALLBRIDGE_SILENCE_HANGUP_SECONDS", cls.silence_hangup_s)),
            iphone_udid=e("CALLBRIDGE_IPHONE_UDID", ""),
            record=e("CALLBRIDGE_RECORD", "0").lower() in ("1", "true", "yes"),
            sinks=_list("CALLBRIDGE_SINKS", "jsonl"),
        )
        if e("CALLBRIDGE_ACCEPT_LABELS"):
            s.accept_labels = _list("CALLBRIDGE_ACCEPT_LABELS")
        if e("CALLBRIDGE_DATA_DIR"):
            s.data_dir = Path(e("CALLBRIDGE_DATA_DIR")).expanduser()
        if e("CALLBRIDGE_DNC_FILE"):
            s.dnc_file = Path(e("CALLBRIDGE_DNC_FILE")).expanduser()
        return s
