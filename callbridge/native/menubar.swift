// CallBridge menu-bar switch: runs `<callbridge> answer` while On, stops it (SIGTERM = Ctrl-C) when Off.
// Launched by `callbridge menubar` as: CallBridge <callbridge-exe> <working-dir> <call-log-dir>
import AppKit

final class App: NSObject, NSApplicationDelegate {
    let args = CommandLine.arguments
    var item: NSStatusItem!
    let status = NSMenuItem(title: "Off", action: nil, keyEquivalent: "")
    let toggle = NSMenuItem(title: "Turn on", action: #selector(flip), keyEquivalent: "")
    var proc: Process?
    var lastError = ""

    func applicationDidFinishLaunching(_ n: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        let menu = NSMenu()
        status.isEnabled = false
        toggle.target = self
        let log = NSMenuItem(title: "Open call log", action: #selector(openLog), keyEquivalent: "")
        log.target = self
        let quit = NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q")
        quit.target = self
        [status, .separator(), toggle, log, .separator(), quit].forEach(menu.addItem)
        item.menu = menu
        start()
    }

    func show(_ text: String, on: Bool) {
        status.title = text
        toggle.title = on ? "Turn off" : "Turn on"
        item.button?.image = NSImage(systemSymbolName: on ? "phone.fill" : "phone", accessibilityDescription: "CallBridge")
    }

    func start() {
        guard args.count > 1 else { show("Start me with: callbridge menubar", on: false); return }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: args[1])
        p.arguments = ["answer"]
        if args.count > 2 { p.currentDirectoryURL = URL(fileURLWithPath: args[2]) }   // so ./.env is found
        let out = Pipe(), err = Pipe()
        p.standardOutput = out
        p.standardError = err
        out.fileHandleForReading.readabilityHandler = { h in self.lines(h) { self.onLine($0) } }
        err.fileHandleForReading.readabilityHandler = { h in self.lines(h) { self.lastError = $0 } }
        p.terminationHandler = { p in DispatchQueue.main.async {
            if self.proc === p { self.proc = nil }
            let failed = p.terminationReason == .exit && p.terminationStatus != 0
            self.show(failed ? "Stopped: \(self.lastError.isEmpty ? "error \(p.terminationStatus)" : self.lastError)" : "Off",
                      on: false)
        } }
        do {
            try p.run()
            proc = p
            lastError = ""
            show("Starting…", on: true)
        } catch {
            show("Could not start: \(error.localizedDescription)", on: false)
        }
    }

    func lines(_ h: FileHandle, _ each: @escaping (String) -> Void) {
        let data = h.availableData
        guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { h.readabilityHandler = nil; return }
        for l in text.split(separator: "\n") where !l.trimmingCharacters(in: .whitespaces).isEmpty {
            let s = String(l)
            DispatchQueue.main.async { each(s) }
        }
    }

    func onLine(_ l: String) {
        guard proc != nil else { return }
        if l.hasPrefix("waiting for calls") { show("On: waiting for calls", on: true) }
        else if l.hasPrefix("ringing: ") { show("Answering \(l.dropFirst(9))", on: true) }
        else if l.hasPrefix("sent: ") || l.hasPrefix("line went silent") { show("On: waiting for calls", on: true) }
        else if l.hasPrefix("call failed: ") { show("Last call failed, still on", on: true) }
    }

    @objc func flip() {
        if let p = proc {
            show("Stopping…", on: false)
            p.terminate()   // SIGTERM: callbridge hangs up and gives the Mac its mic and speakers back
        } else {
            start()
        }
    }

    @objc func openLog() {
        let dir = args.count > 3 ? args[3] : NSString(string: "~/Library/Logs/callbridge").expandingTildeInPath
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        NSWorkspace.shared.open(URL(fileURLWithPath: dir))
    }

    @objc func quitApp() {
        if let p = proc {
            p.terminationHandler = nil
            p.terminate()
            let deadline = Date().addingTimeInterval(5)   // let it restore the audio devices before we go
            while p.isRunning && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.1)) }
        }
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
