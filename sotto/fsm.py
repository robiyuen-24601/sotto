"""Pure hotkey state machine. No macOS imports; the event tap drives it."""

from __future__ import annotations

import enum


class Action(enum.Enum):
    NONE = "none"
    START = "start"            # begin recording
    STOP = "stop"              # end recording, run pipeline
    DISCARD = "discard"        # held too briefly; drop recording
    CANCEL = "cancel"          # another key pressed; drop recording
    IGNORED_BUSY = "ignored_busy"  # pipeline mid-flight; refuse new dictation


class _State(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"


class HotkeyFSM:
    def __init__(self, min_hold_seconds: float = 0.3):
        self.min_hold_seconds = min_hold_seconds
        self._state = _State.IDLE
        self._busy = False
        self._down_at = 0.0

    def set_busy(self, busy: bool) -> None:
        """Set pipeline busy state.

        Called from the worker thread. All other methods must be called from the
        event-tap thread only. Safe because this is a single atomic bool store
        under the GIL.
        """
        self._busy = busy

    def on_hotkey_down(self, t: float) -> Action:
        """Handle hotkey press.

        Args:
            t: monotonic seconds (time.monotonic()), same clock for down and up.
        """
        if self._state is not _State.IDLE:
            return Action.NONE
        if self._busy:
            return Action.IGNORED_BUSY
        self._state = _State.RECORDING
        self._down_at = t
        return Action.START

    def on_hotkey_up(self, t: float) -> Action:
        """Handle hotkey release.

        Args:
            t: monotonic seconds (time.monotonic()), same clock for down and up.
        """
        if self._state is not _State.RECORDING:
            return Action.NONE
        self._state = _State.IDLE
        if t - self._down_at < self.min_hold_seconds:
            return Action.DISCARD
        return Action.STOP

    def on_other_key(self) -> Action:
        if self._state is not _State.RECORDING:
            return Action.NONE
        self._state = _State.IDLE
        return Action.CANCEL
