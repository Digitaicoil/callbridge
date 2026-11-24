"""The Mac side of a call: default audio devices, the call banners, dialing, answering and hanging up."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

NATIVE = Path(__file__).resolve().parent / "native"
AUDIODEV = Path.home() / "Library" / "Caches" / "callbridge" / "audiodev"
CALLBANNER = AUDIODEV.with_name("callbanner")


def audiodev(*args: str) -> str:
    if not AUDIODEV.exists():
        AUDIODEV.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(NATIVE / "audiodev.swift"), "-o", str(AUDIODEV)], check=True)
    return subprocess.run([str(AUDIODEV), *args], capture_output=True, text=True).stdout


def devices() -> dict:
    """{'input': name, 'output': name, 'all': [names]}"""
    d: dict = {"all": []}
    for line in audiodev("get").splitlines():
        k, _, v = line.partition("\t")
        if k == "device":
            d["all"].append(v)
        else:
            d[k] = v
    return d


def banner(*args: str) -> str:
    """List, read or press buttons on macOS call banners (Notification Center). The Swift helper reads them in
    ~50 ms; the AppleScript fallback (no swiftc) takes 1-2 s per look, which costs the caller several rings."""
    if not CALLBANNER.exists():
        CALLBANNER.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(NATIVE / "callbanner.swift"), "-o", str(CALLBANNER)], capture_output=True)
    cmd = [str(CALLBANNER)] if CALLBANNER.exists() else ["osascript", str(NATIVE / "callbanner.applescript")]
    return subprocess.run([*cmd, *args], capture_output=True, text=True).stdout.strip()


def screen_locked() -> bool:
    out = subprocess.run(["ioreg", "-l", "-d1"], capture_output=True, text=True).stdout
    return '"CGSSessionScreenIsLocked"=Yes' in out


def release_iphone(udid: str) -> None:
    """Optional. A UI-automation agent (Appium's WebDriverAgent) running on the iPhone pulls the call onto the
    phone and the line goes silent. If you automate the iPhone, set CALLBRIDGE_IPHONE_UDID and callbridge stops it first."""
    if not udid:
        return
    subprocess.run(["pkill", "-f", "appium"], capture_output=True)
    procs = subprocess.run(["xcrun", "devicectl", "device", "info", "processes", "--device", udid],
                           capture_output=True, text=True).stdout
    for line in procs.splitlines():
        if "WebDriverAgent" in line:
            subprocess.run(["xcrun", "devicectl", "device", "process", "terminate", "--device", udid,
                            "--pid", line.split()[0]], capture_output=True)
    time.sleep(2)


def dial(number: str, timeout_s: int = 30) -> None:
    subprocess.run(["open", "-a", "Phone", f"tel://{number}"], check=True)
    for _ in range(timeout_s):           # the "Call" prompt takes a few seconds to appear
        time.sleep(1)
        if banner("press", "Call").startswith("pressed"):
            return
    raise RuntimeError("no call prompt appeared: is 'Calls from iPhone' on, and the Mac unlocked?")


def incoming(accept_labels: list[str]) -> str | None:
    """The caller shown on an incoming-call banner, or None when nothing is ringing."""
    buttons = banner("list").splitlines()
    if not any(b in buttons for b in accept_labels):
        return None
    bidi = dict.fromkeys(map(ord, "\u202a\u202b\u202c\u200e\u200f\u2066\u2067\u2068\u2069"))   # direction marks around names
    texts = [t.translate(bidi).strip() for t in banner("texts", *accept_labels).splitlines()]   # the call's banner only
    texts = [t for t in texts if t and t != "missing value"]
    return texts[0] if texts else "unknown caller"


def accept(accept_labels: list[str]) -> bool:
    return banner("press", *accept_labels).startswith("pressed")


def hang_up() -> None:
    """End the call. The Mac's call panel hides a few seconds into a call, so its End button can't be relied on.
    Restarting the Mac's call service ends the call on the Mac and the iPhone; launchd brings it straight back."""
    if banner("press", "Cancel").startswith("pressed"):     # still at the outgoing prompt
        return
    subprocess.run(["killall", "callservicesd"], capture_output=True)
