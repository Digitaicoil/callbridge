"""Where a finished call goes. Pick any mix with CALLBRIDGE_SINKS=jsonl,telegram,slack,webhook,hubspot.
Each sink is one function: send(record, env) -> None. Adding your own CRM is ~20 lines (docs/integrations.md)."""
from __future__ import annotations

import os
import sys
from collections.abc import Callable

from ..record import CallRecord
from . import hubspot, jsonl, slack, telegram, webhook

SINKS: dict[str, Callable[[CallRecord, dict], None]] = {
    "jsonl": jsonl.send,
    "telegram": telegram.send,
    "slack": slack.send,
    "webhook": webhook.send,
    "hubspot": hubspot.send,
}


def dispatch(record: CallRecord, names: list[str], env: dict | None = None) -> dict[str, str]:
    """Send the record everywhere asked. One failing sink never stops the others."""
    env = dict(os.environ) if env is None else env
    results = {}
    for name in names:
        fn = SINKS.get(name)
        if fn is None:
            results[name] = "unknown sink"
            continue
        try:
            fn(record, env)
            results[name] = "ok"
        except Exception as e:  # noqa: BLE001
            results[name] = f"failed: {e}"
            print(f"sink {name} failed: {e}", file=sys.stderr)
    return results
