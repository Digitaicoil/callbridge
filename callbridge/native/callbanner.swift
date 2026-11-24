// callbanner list | texts [BUTTON...] | press NAME [NAME...]
// The same job as callbanner.applescript, through the Accessibility API directly: ~50 ms instead of 1-2 s,
// so an incoming call is answered within a ring instead of several.
import AppKit
import ApplicationServices

func attr(_ e: AXUIElement, _ name: String) -> String? {
    var v: CFTypeRef?
    guard AXUIElementCopyAttributeValue(e, name as CFString, &v) == .success, let s = v as? String, !s.isEmpty else { return nil }
    return s
}

func walk(_ e: AXUIElement, _ depth: Int, _ role: String, _ out: inout [AXUIElement]) {
    if depth > 30 { return }
    if attr(e, kAXRoleAttribute) == role { out.append(e) }
    var kids: CFTypeRef?
    guard AXUIElementCopyAttributeValue(e, kAXChildrenAttribute as CFString, &kids) == .success,
          let list = kids as? [AXUIElement] else { return }
    for k in list { walk(k, depth + 1, role, &out) }
}

let argv = Array(CommandLine.arguments.dropFirst())
guard let cmd = argv.first,
      let nc = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.notificationcenterui").first
else { exit(0) }
let app = AXUIElementCreateApplication(nc.processIdentifier)
var roots = [app]
if cmd == "texts" && argv.count > 1 {   // texts Accept Answer: only the banner holding those buttons, never other notifications
    var wins: CFTypeRef?
    if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &wins) == .success, let ws = wins as? [AXUIElement] {
        roots = ws.filter { w in
            var bs: [AXUIElement] = []
            walk(w, 0, kAXButtonRole, &bs)
            return bs.contains { b in argv.dropFirst().contains(attr(b, kAXDescriptionAttribute) ?? "") }
        }
    }
}
var els: [AXUIElement] = []
for r in roots { walk(r, 0, cmd == "texts" ? kAXStaticTextRole : kAXButtonRole, &els) }

switch cmd {
case "list":
    for b in els { if let d = attr(b, kAXDescriptionAttribute) { print(d) } }
case "texts":   // the caller's name/number sits in value, title or description depending on the macOS version
    for t in els {
        if let s = [attr(t, kAXValueAttribute), attr(t, kAXTitleAttribute), attr(t, kAXDescriptionAttribute)]
            .compactMap({ $0 }).first(where: { $0 != "text" }) { print(s) }
    }
case "press":
    for want in argv.dropFirst() {
        if let b = els.first(where: { attr($0, kAXDescriptionAttribute) == want }) {
            AXUIElementPerformAction(b, kAXPressAction as CFString)
            print("pressed \(want)"); exit(0)
        }
    }
    print("not found")
default:
    exit(2)
}
