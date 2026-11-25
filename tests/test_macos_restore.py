import os
import signal

import pytest

from callbridge import call, macos

CABLES = ("CallBridge Call In", "CallBridge Agent Out")


@pytest.fixture
def mac(tmp_path, monkeypatch):
    """A fake Mac: default devices in a dict, audiodev calls recorded."""
    state = {"input": "MacBook Pro Microphone", "output": "MacBook Pro Speakers",
             "all": ["MacBook Pro Microphone", "MacBook Pro Speakers", *CABLES]}
    calls = []

    def audiodev(cmd, name=None):
        calls.append((cmd, name))
        if cmd in ("set-input", "set-output"):
            state[cmd[4:]] = name
        return ""

    monkeypatch.setattr(macos, "SAVED", tmp_path / "saved.json")
    monkeypatch.setattr(macos, "audiodev", audiodev)
    monkeypatch.setattr(macos, "devices", lambda: dict(state))
    return state, calls


def test_restore_does_nothing_when_the_mac_uses_its_own_devices(mac):
    _, calls = mac
    assert macos.restore_devices(CABLES) == {}
    assert calls == []


def test_restore_brings_back_the_saved_devices_after_a_killed_call(mac):
    state, _ = mac
    macos.remember_devices(dict(state), CABLES)
    state.update(input=CABLES[1], output=CABLES[0])          # the call pointed the Mac at the cables, then died
    assert macos.restore_devices(CABLES) == {"input": "MacBook Pro Microphone", "output": "MacBook Pro Speakers"}
    assert state["output"] == "MacBook Pro Speakers"


def test_a_cable_is_never_saved_as_the_mac_own_device(mac):
    state, _ = mac
    macos.remember_devices({"input": CABLES[1], "output": CABLES[0]}, CABLES)
    assert macos._saved() == {}
    state.update(input=CABLES[1], output=CABLES[0])
    assert macos.restore_devices(CABLES) == {"input": "MacBook Pro Microphone", "output": "MacBook Pro Speakers"}


def test_sigterm_stops_like_ctrl_c():
    old = signal.getsignal(signal.SIGTERM)
    try:
        call.stop_on_sigterm()
        with pytest.raises(KeyboardInterrupt):
            os.kill(os.getpid(), signal.SIGTERM)
    finally:
        signal.signal(signal.SIGTERM, old)
