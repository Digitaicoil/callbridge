import json
import re
import subprocess
from pathlib import Path

import pytest

from callbridge import elevenlabs as el

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("template", ["receptionist", "sales"])
def test_templates_render_and_disclose_ai(template):
    prompt, first = el.render(template, business="Bright Smile Dental", owner="Dana", agent_name="Ava", about="x")
    assert "$" not in prompt + first and "Bright Smile Dental" in prompt
    body = el.agent_body("t", prompt, first)
    assert body["platform_settings"]["data_collection"]["outcome"]
    assert body["conversation_config"]["agent"]["prompt"]["built_in_tools"]["end_call"]


def test_agent_without_ai_disclosure_is_refused():
    with pytest.raises(ValueError):
        el.agent_body("t", "You are Ava, a receptionist.", "Hello, Ava speaking.")


def test_receptionist_greets_first_and_sales_waits():
    assert el.render("receptionist", business="B")[1]
    assert el.render("sales", business="B")[1] == ""


def test_plugin_manifests_are_valid():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "callbridge" and market["plugins"][0]["name"] == "callbridge"
    for skill in (ROOT / "skills").iterdir():
        head = (skill / "SKILL.md").read_text().split("---")[1]
        assert "name:" in head and "description:" in head


SECRET_PATTERNS = [
    r"sk_[a-f0-9]{20,}",                       # ElevenLabs key
    r"agent_[0-9a-z]{20,}",                    # a real ElevenLabs agent id
    r"\b\d{8,10}:AA[\w-]{30,}",                # Telegram bot token
    r"pat-[a-z0-9]{2,4}-[0-9a-f-]{30,}",       # HubSpot token
    r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",   # device UDIDs
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"/Users/[a-z]",                           # someone's home folder
]


def test_no_secrets_or_personal_ids_in_tracked_files():
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    hits = []
    for f in files:
        p = ROOT / f
        if p.suffix in (".png", ".jpg", ".gif", ".mp4") or not p.is_file() or f == "tests/test_agents_and_repo.py":
            continue
        text = p.read_text(errors="ignore")
        hits += [f"{f}: {m.group(0)}" for pat in SECRET_PATTERNS for m in re.finditer(pat, text)]
    assert not hits, hits
