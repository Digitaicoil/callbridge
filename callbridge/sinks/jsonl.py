"""Append every call to a local JSON Lines file (the default; nothing leaves your Mac)."""
import json
from pathlib import Path


def send(record, env: dict) -> None:
    path = Path(env.get("CALLBRIDGE_JSONL", Path.home() / "Library" / "Logs" / "callbridge" / "calls.jsonl")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")
