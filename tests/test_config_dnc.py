from callbridge import dnc
from callbridge.config import Settings, load_env


def test_env_file_fills_missing_values_only(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nCALLBRIDGE_SINKS=jsonl,telegram   # inline comment\nELEVENLABS_API_KEY="from-file"\n'
                 "TELEGRAM_THREAD_ID=            # optional\n")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "from-env")
    monkeypatch.delenv("CALLBRIDGE_SINKS", raising=False)
    monkeypatch.delenv("TELEGRAM_THREAD_ID", raising=False)
    load_env([f])
    import os
    assert os.environ["ELEVENLABS_API_KEY"] == "from-env"
    assert os.environ["CALLBRIDGE_SINKS"] == "jsonl,telegram"
    assert os.environ["TELEGRAM_THREAD_ID"] == ""


def test_settings_defaults(monkeypatch):
    for k in ("CALLBRIDGE_SINKS", "CALLBRIDGE_ACCEPT_LABELS", "CALLBRIDGE_RECORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr("callbridge.config.ENV_FILES", ())
    s = Settings.from_env()
    assert s.sinks == ["jsonl"] and s.accept_labels == ["Accept", "Answer"] and s.record is False


def test_do_not_call_matches_formatting_variants(tmp_path):
    p = tmp_path / "dnc.txt"
    assert not dnc.blocked(p, "+1 555 123 4567")
    dnc.add(p, "+1 (555) 123-4567")
    dnc.add(p, "+15551234567")
    assert dnc.blocked(p, "+1 555 123 4567")
    assert p.read_text() == "+15551234567\n"
