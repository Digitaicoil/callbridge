-- osascript callbanner.applescript list | texts | press NAME [NAME...]
-- Reads and presses the buttons on macOS call banners (Notification Center), e.g. "Call" / "Cancel" on the
-- outgoing prompt and "Accept" / "Decline" on an incoming call. The buttons sit ~20 levels deep, so search recursively.
on walk(e, depth, wantRole)
	tell application "System Events"
		set found to {}
		if depth > 30 then return found
		try
			set kids to UI elements of e
		on error
			return found
		end try
		repeat with f in kids
			try
				if role of f is wantRole then set end of found to (contents of f)
				set found to found & my walk(f, depth + 1, wantRole)
			end try
		end repeat
		return found
	end tell
end walk

on run argv
	set cmd to item 1 of argv
	tell application "System Events" to tell process "NotificationCenter"
		set wantRole to "AXButton"
		if cmd is "texts" then set wantRole to "AXStaticText"
		set els to {}
		repeat with w in windows
			set els to els & my walk(w, 0, wantRole)
		end repeat
		if cmd is "list" or cmd is "texts" then
			set out to ""
			repeat with b in els
				try
					if cmd is "list" then
						set out to out & (description of b) & linefeed
					else
						set out to out & (value of b) & linefeed
					end if
				end try
			end repeat
			return out
		end if
		repeat with i from 2 to count of argv
			set want to item i of argv
			repeat with b in els
				try
					if (description of b) is want then
						perform action "AXPress" of b
						return "pressed " & want
					end if
				end try
			end repeat
		end repeat
		return "not found"
	end tell
end run
