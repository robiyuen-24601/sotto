"""Insert text into the focused app: clipboard swap + synthetic Cmd+V."""

from __future__ import annotations

import time
from typing import Callable, Optional, Protocol


class Clipboard(Protocol):
    def read(self) -> Optional[str]: ...
    def write(self, text: str) -> None: ...


class Injector:
    PRE_PASTE_DELAY = 0.05   # let the pasteboard settle before Cmd+V
    RESTORE_DELAY = 0.35     # let the target app finish reading the paste

    def __init__(
        self,
        clipboard: Clipboard,
        paste_fn: Callable[[], None],
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.clipboard = clipboard
        self.paste_fn = paste_fn
        self.sleep_fn = sleep_fn

    def inject(self, text: str) -> None:
        if not text.strip():
            return
        old = self.clipboard.read()
        self.clipboard.write(text)
        try:
            self.sleep_fn(self.PRE_PASTE_DELAY)
            self.paste_fn()
            self.sleep_fn(self.RESTORE_DELAY)
        finally:
            if old is not None:
                self.clipboard.write(old)


# --- macOS implementations (not unit-tested; exercised in integration) ---

class MacClipboard:
    def read(self) -> Optional[str]:
        from AppKit import NSPasteboard, NSPasteboardTypeString

        return NSPasteboard.generalPasteboard().stringForType_(
            NSPasteboardTypeString
        )

    def write(self, text: str) -> None:
        from AppKit import NSPasteboard, NSPasteboardTypeString

        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)


def mac_paste() -> None:
    """Synthesize Cmd+V (keycode 9)."""
    import Quartz

    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, 9, down)
        Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def make_mac_injector() -> Injector:
    return Injector(clipboard=MacClipboard(), paste_fn=mac_paste)
