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
            return event

        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )
        if type_ == Quartz.kCGEventFlagsChanged and keycode == self.keycode:
            flags = Quartz.CGEventGetFlags(event)
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
            # worker has even seen this STOP; worker clears busy when done
            self.fsm.set_busy(True)
        if action is not Action.NONE:
            self.on_action(action)
        return event

    def start(self) -> None:
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
