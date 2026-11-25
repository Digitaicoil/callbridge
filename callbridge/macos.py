"""The Mac side of a call: default audio devices, the call banners, dialing, answering and hanging up."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

NATIVE = Path(__file__).resolve().parent / "native"
AUDIODEV = Path.home() / "Library" / "Caches" / "callbridge" / "audiodev"
CALLBANNER = AUDIODEV.with_name("callbanner")
MENUBAR = AUDIODEV.with_name("CallBridge.app")
SAVED = AUDIODEV.with_name("devices-before-call.json")


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


def remember_devices(before: dict, cables: tuple[str, ...]) -> None:
    """Save the Mac's own mic and speakers before a call points them at the cables (never a cable itself)."""
    keep = {k: before[k] for k in ("input", "output") if before.get(k) and before[k] not in cables}
    if keep:
        SAVED.parent.mkdir(parents=True, exist_ok=True)
        SAVED.write_text(json.dumps({**_saved(), **keep}))


def _saved() -> dict:
    try:
        return json.loads(SAVED.read_text())
    except (OSError, ValueError):
        return {}


def _fallback(kind: str, names: list[str], cables: tuple[str, ...]) -> str | None:
    words = ("Speakers", "Headphones", "AirPods") if kind == "output" else ("Microphone", "AirPods")
    return next((n for n in names if n not in cables and any(w in n for w in words)), None)


def restore_devices(cables: tuple[str, ...]) -> dict:
    """Give the Mac its mic and speakers back if a cable is still the default (a call that was stopped or crashed).
    Returns {kind: device} for what it changed."""
    now, saved, changed = devices(), _saved(), {}
    for kind in ("input", "output"):
        if now.get(kind) not in cables:
            continue
        target = saved.get(kind) if saved.get(kind) in now["all"] else _fallback(kind, now["all"], cables)
        if target:
            audiodev(f"set-{kind}", target)
            if kind == "output":
                audiodev("set-system-output", target)
            changed[kind] = target
    return changed


def menubar_app() -> Path:
    """Build the menu-bar app (Swift, no Xcode project) once; rebuilt when the source is newer."""
    src, exe = NATIVE / "menubar.swift", MENUBAR / "Contents" / "MacOS" / "CallBridge"
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        (MENUBAR / "Contents" / "Info.plist").write_text(INFO_PLIST)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True)
    return MENUBAR


INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>CallBridge</string>
  <key>CFBundleIdentifier</key><string>dev.callbridge.menubar</string>
  <key>CFBundleExecutable</key><string>CallBridge</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
</dict></plist>
"""


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
