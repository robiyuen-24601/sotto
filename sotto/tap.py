"""Quartz event tap: feeds Right Option and other-key events to the FSM.

Listen-only tap; it never swallows events. Runs on the main run loop
(rumps/AppKit own it). Actions are delivered via the on_action callback,
which must be thread-safe (app.py hands them to the worker queue).
"""

from __future__ import annotations

import logging
import time
from typing import Callable

import Quartz

from sotto.fsm import Action, HotkeyFSM

log = logging.getLogger("sotto")


class HotkeyTap:
    def __init__(
        self,
        fsm: HotkeyFSM,
        keycode: int,
        on_action: Callable[[Action], None],
    ):
        self.fsm = fsm
        self.keycode = keycode
        self.on_action = on_action
        self._tap = None

    def _callback(self, proxy, type_, event, refcon):
        if type_ in (
            Quartz.kCGEventTapDisabledByTimeout,
            Quartz.kCGEventTapDisabledByUserInput,
        ):
            log.warning("event tap disabled (%s); re-enabling", type_)
            Quartz.CGEventTapEnable(self._tap, True)
            # Resynchronize: a hotkey-up could have been dropped while the
            # tap was disabled, which would otherwise leave the FSM stuck
            # thinking the mic is still conceptually held. on_other_key()
            # is a no-op when idle and cancels a stuck RECORDING when not.
            action = self.fsm.on_other_key()
            if action is Action.CANCEL:
                self.on_action(action)
            return event

        try:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            if type_ == Quartz.kCGEventFlagsChanged and keycode == self.keycode:
                flags = Quartz.CGEventGetFlags(event)
                # Known limitation: kCGEventFlagMaskAlternate is the generic
                # Option-key-down flag, not specific to Right Option. If the
                # OTHER Option key (Left Option) is also held, the mask stays
                # set when Right Option is released, so that release is
                # missed. Rare in practice; flagged for manual QA.
                is_down = bool(flags & Quartz.kCGEventFlagMaskAlternate)
                action = (
                    self.fsm.on_hotkey_down(time.monotonic())
                    if is_down
                    else self.fsm.on_hotkey_up(time.monotonic())
                )
            elif type_ == Quartz.kCGEventKeyDown:
                action = self.fsm.on_other_key()
            else:
                return event

            if action is Action.STOP:
                # close the race window: refuse new dictations before the
                # worker has even seen this STOP; worker clears busy when
                # done. Invariant: every dispatched STOP must eventually
                # reach set_busy(False) on ALL worker paths -- including
                # paused and error paths.
                self.fsm.set_busy(True)
            if action is not Action.NONE:
                self.on_action(action)
        except Exception:
            log.exception("tap callback failed")
        return event

    def start(self) -> None:
        if self._tap is not None:
            return
        mask = Quartz.CGEventMaskBit(
            Quartz.kCGEventFlagsChanged
        ) | Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._callback,
            None,
        )
        if self._tap is None:
            raise RuntimeError(
                "Could not create event tap. Grant Accessibility permission "
                "to this binary in System Settings > Privacy & Security."
            )
        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetMain(), source, Quartz.kCFRunLoopCommonModes
        )
        Quartz.CGEventTapEnable(self._tap, True)
