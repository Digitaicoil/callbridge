// audiodev get | set-input NAME | set-output NAME | running: the Mac's default audio devices.
// Calls from iPhone use the default devices, so callbridge points them at its two virtual cables during a call.
import CoreAudio
import Foundation

func devices() -> [(AudioDeviceID, String)] {
    var addr = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDevices, mScope: kAudioObjectPropertyScopeGlobal,
                                          mElement: kAudioObjectPropertyElementMain)
    var size: UInt32 = 0
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size)
    var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &ids)
    return ids.map { id in
        var a = AudioObjectPropertyAddress(mSelector: kAudioObjectPropertyName, mScope: kAudioObjectPropertyScopeGlobal,
                                           mElement: kAudioObjectPropertyElementMain)
        var name: Unmanaged<CFString>?
        var s = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
        AudioObjectGetPropertyData(id, &a, 0, nil, &s, &name)
        return (id, (name?.takeRetainedValue() as String?) ?? "?")
    }
}

func defaultDevice(_ sel: AudioObjectPropertySelector) -> String {
    var addr = AudioObjectPropertyAddress(mSelector: sel, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var id = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &id)
    return devices().first { $0.0 == id }?.1 ?? "?"
}

func setDefault(_ sel: AudioObjectPropertySelector, _ name: String) -> Bool {
    guard var id = devices().first(where: { $0.1 == name })?.0 else { return false }
    var addr = AudioObjectPropertyAddress(mSelector: sel, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    return AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil,
                                      UInt32(MemoryLayout<AudioDeviceID>.size), &id) == noErr
}

func running(_ id: AudioDeviceID) -> Bool {
    var addr = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyDeviceIsRunningSomewhere,
                                          mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var v: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    AudioObjectGetPropertyData(id, &addr, 0, nil, &size, &v)
    return v != 0
}

let args = CommandLine.arguments
switch args.count > 1 ? args[1] : "get" {
case "set-input": exit(setDefault(kAudioHardwarePropertyDefaultInputDevice, args[2]) ? 0 : 1)
case "set-system-output": exit(setDefault(kAudioHardwarePropertyDefaultSystemOutputDevice, args[2]) ? 0 : 1)
case "get-system-output": print(defaultDevice(kAudioHardwarePropertyDefaultSystemOutputDevice))
case "running": for d in devices() where running(d.0) { print("running\t" + d.1) }
case "set-output": exit(setDefault(kAudioHardwarePropertyDefaultOutputDevice, args[2]) ? 0 : 1)
default:
    print("input\t" + defaultDevice(kAudioHardwarePropertyDefaultInputDevice))
    print("output\t" + defaultDevice(kAudioHardwarePropertyDefaultOutputDevice))
    for d in devices() { print("device\t" + d.1) }
}
