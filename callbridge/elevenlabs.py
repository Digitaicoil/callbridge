"""The ElevenLabs side: create an agent from a template, push prompt edits, list calls, fetch a call's analysis."""
from __future__ import annotations

import time
from pathlib import Path
from string import Template

import httpx

API = "https://api.elevenlabs.io/v1/convai"
AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"       # a public ElevenLabs voice; swap for any voice in your library
AI_DISCLOSURE = ("AI", "artificial intelligence")

DATA_COLLECTION = {
    "caller_name": {"type": "string", "description": "The other person's name, if they said it."},
    "reason": {"type": "string", "description": "Why they called or what they need, in one short sentence."},
    "callback_time": {"type": "string", "description": "When they want to be called back, if they said."},
    "outcome": {"type": "string", "description": "One of: meeting_booked, message_taken, callback_requested, "
                                                 "not_interested, do_not_call, no_answer, other."},
}

FIRST_MESSAGE = {
    "receptionist": "Hi, you've reached $business. This is $agent_name, the AI assistant. How can I help?",
    "sales": "",     # outbound: wait for their "hello", then the prompt's opening line
}


def render(template: str, **values: str) -> tuple[str, str]:
    """(prompt, first_message) for a template, with $business / $owner / $agent_name / $about filled in."""
    prompt = Template((AGENTS_DIR / f"{template}.md").read_text()).safe_substitute(values)
    first = Template(FIRST_MESSAGE.get(template, "")).safe_substitute(values)
    return prompt, first


def check_disclosure(prompt: str, first_message: str) -> None:
    """Every CallBridge agent says it's an AI. Refuse to upload one that doesn't."""
    text = (prompt + " " + first_message).lower()
    if not any(w.lower() in text for w in AI_DISCLOSURE):
        raise ValueError("the agent must tell people it's an AI: keep 'AI' in its opening")


def agent_body(name: str, prompt: str, first_message: str, language: str = "en", voice_id: str = DEFAULT_VOICE,
               llm: str = "claude-haiku-5-5") -> dict:
    check_disclosure(prompt, first_message)
    return {
        "name": name,
        "conversation_config": {
            "agent": {"first_message": first_message, "language": language,
                      "prompt": {"prompt": prompt, "llm": llm, "temperature": 0.0,
                                 "built_in_tools": {"end_call": {
                                     "type": "system", "name": "end_call",
                                     "description": "End the call when the conversation is over or they asked to stop.",
                                     "params": {"system_tool_type": "end_call"}}}}},
            "tts": {"voice_id": voice_id, "model_id": "eleven_v4_turbo", "optimize_streaming_latency": 4,
                    "agent_output_audio_format": "pcm_16000"},
            "asr": {"user_input_audio_format": "pcm_16000"},
            "turn": {"turn_eagerness": "eager", "initial_wait_time": 30},
            "conversation": {"max_duration_seconds": 600},
        },
        "platform_settings": {"data_collection": DATA_COLLECTION},
    }


class Client:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        if not api_key:
            raise SystemExit("ELEVENLABS_API_KEY is not set (see .env.example)")
        self.http = http or httpx.Client(headers={"xi-api-key": api_key}, timeout=60)

    def create_agent(self, body: dict) -> str:
        r = self.http.post(f"{API}/agents/create", json=body)
        r.raise_for_status()
        return r.json()["agent_id"]

    def update_prompt(self, agent_id: str, prompt: str, first_message: str | None = None) -> None:
        check_disclosure(prompt, first_message or "")
        agent: dict = {"prompt": {"prompt": prompt}}
        if first_message is not None:
            agent["first_message"] = first_message
        self.http.patch(f"{API}/agents/{agent_id}", json={"conversation_config": {"agent": agent}}).raise_for_status()

    def agent(self, agent_id: str) -> dict:
        r = self.http.get(f"{API}/agents/{agent_id}")
        r.raise_for_status()
        return r.json()

    def script(self, agent_id: str) -> str:
        """The agent's system prompt, for the call record. Empty if it can't be read: a record never fails on it."""
        try:
            return self.agent(agent_id)["conversation_config"]["agent"]["prompt"]["prompt"] or ""
        except (httpx.HTTPError, KeyError, TypeError):
            return ""

    def calls(self, agent_id: str, n: int = 10) -> list[dict]:
        r = self.http.get(f"{API}/conversations", params={"agent_id": agent_id, "page_size": n})
        r.raise_for_status()
        return r.json().get("conversations", [])

    def conversation(self, conv_id: str) -> dict:
        r = self.http.get(f"{API}/conversations/{conv_id}")
        r.raise_for_status()
        return r.json()

    def analysis(self, conv_id: str, tries: int = 12, wait_s: float = 10) -> tuple[str, dict, int]:
        """(summary, collected data, cost in credits). ElevenLabs analyses a call within about a minute."""
        for i in range(tries):
            try:
                d = self.conversation(conv_id)
                a = d.get("analysis") or {}
                summary = (a.get("transcript_summary") or "").strip()
                if summary:
                    data = {k: (v or {}).get("value") for k, v in (a.get("data_collection_results") or {}).items()}
                    return summary, data, int((d.get("metadata") or {}).get("cost") or 0)
            except httpx.HTTPError:
                pass
            if i < tries - 1:
                time.sleep(wait_s)
        return "", {}, 0
