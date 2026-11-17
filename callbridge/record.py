"""What a finished call leaves behind, in one shape every integration reads."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class CallRecord:
    direction: str                     # "outbound" | "inbound"
    number: str                        # who we called, or the caller ID shown on the Mac
    started_at: str                    # ISO 8601, local time
    duration_s: int = 0
    summary: str = ""                  # written by ElevenLabs after the call
    data: dict = field(default_factory=dict)   # the agent's data collection: caller_name, reason, callback_time ...
    transcript: list[str] = field(default_factory=list)   # "Agent: ..." / "Caller: ..."
    conversation_id: str | None = None
    recording: str | None = None       # path to the stereo WAV when CALLBRIDGE_RECORD=1
    context: str = ""                  # what you told the agent about this call
    script: str = ""                   # the agent's instructions (its system prompt) this call ran with

    def as_dict(self) -> dict:
        return asdict(self)

    def headline(self) -> str:
        arrow = "→" if self.direction == "outbound" else "←"
        who = self.data.get("caller_name") or self.number
        return f"📞 {arrow} {who} · {self.duration_s}s"

    def text(self, max_lines: int = 30) -> str:
        parts = [self.headline(), "", self.summary or "(no summary)"]
        fields = {k: v for k, v in self.data.items() if v not in (None, "")}
        if fields:
            parts += [""] + [f"• {k}: {v}" for k, v in fields.items()]
        if self.transcript:
            parts += ["", *self.transcript[-max_lines:]]
        return "\n".join(parts)
