"""rumps menu bar app owning the main thread; worker thread runs the pipeline."""

from __future__ import annotations

import logging
import queue
import threading

import rumps
from PyObjCTools import AppHelper

from sotto import sounds
from sotto.config import SottoConfig
from sotto.fsm import Action, HotkeyFSM
from sotto.injector import make_mac_injector
from sotto.recorder import Recorder
from sotto.tap import HotkeyTap

log = logging.getLogger("sotto")

ICON_LOADING = "…"
ICON_IDLE = "🎙"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"
ICON_PAUSED = "⏸"


class SottoApp(rumps.App):
    def __init__(self, cfg: SottoConfig):
        super().__init__(ICON_LOADING, quit_button="Quit")
        self.cfg = cfg
        self.fsm = HotkeyFSM(min_hold_seconds=cfg.min_hold_seconds)
        self.recorder = Recorder()
        self.injector = make_mac_injector()
        self.transcriber = None  # loaded on worker at startup
        self.cleaner = None
        self.last_text = ""
        self.paused = False
        self.load_failed = False

        self.item_last = rumps.MenuItem("Last: (none)", callback=self.on_copy_last)
        self.item_cleanup = rumps.MenuItem("Cleanup: on", callback=self.on_toggle_cleanup)
        self.item_pause = rumps.MenuItem("Pause", callback=self.on_toggle_pause)
        self.menu = [self.item_last, self.item_cleanup, self.item_pause]
        self.cleanup_enabled = cfg.cleanup_enabled
        self.item_cleanup.title = f"Cleanup: {'on' if self.cleanup_enabled else 'off'}"

        self._queue: queue.Queue[Action] = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

        self.tap = HotkeyTap(self.fsm, cfg.keycode, self._queue.put)
        self.tap.start()

    # --- UI helpers: marshal worker-thread updates onto the main thread ---

    def _ui(self, fn, *args):
        AppHelper.callAfter(fn, *args)

    def _set_title(self, s):
        if self.load_failed:
            self.title = "⚠️"
            return
        if s == ICON_IDLE and self.paused:
            s = ICON_PAUSED
        self.title = s

    def _set_last(self, text):
        self.item_last.title = f"Last: {text[:48]}"

    def _notify_load_failed(self):
        try:
            rumps.notification("sotto", "", "Model load failed; see ~/Library/Logs/sotto.log")
        except Exception:
            log.exception("notification failed")

    # --- menu callbacks (main thread) ---

    def on_copy_last(self, _):
        if self.last_text:
            self.injector.clipboard.write(self.last_text)

    def on_toggle_cleanup(self, _):
        self.cleanup_enabled = not self.cleanup_enabled
        self.item_cleanup.title = f"Cleanup: {'on' if self.cleanup_enabled else 'off'}"

    def on_toggle_pause(self, _):
        self.paused = not self.paused
        self.item_pause.title = "Resume" if self.paused else "Pause"
        self._set_title(ICON_PAUSED if self.paused else ICON_IDLE)

    # --- worker thread ---

    def _worker_loop(self):
        try:
            log.info("loading models...")
            from sotto.asr import Transcriber
            from sotto.cleanup import Cleaner

            self.transcriber = Transcriber(self.cfg.asr_model)
            self.cleaner = Cleaner(self.cfg.llm_model)
            log.info("models loaded")
            self._ui(self._set_title, ICON_IDLE)
        except Exception:
            log.exception("model load failed")
            self.load_failed = True
            self._ui(self._set_title, "⚠️")
            self._ui(self._notify_load_failed)
            return

        while True:
            action = self._queue.get()
            try:
                self._handle(action)
            except Exception:
                log.exception("pipeline error on %s", action)
                # Restore state first (mic release, busy flag) so the app is
                # never left stuck; cosmetic feedback (sound, title) follows
                # and is guarded so it can't re-raise past state restoration.
                self.recorder.stop()
                self.fsm.set_busy(False)
                try:
                    self._ui(sounds.play, self.cfg.sound_error)
                except Exception:
                    log.exception("error sound failed")
                self._ui(self._set_title, ICON_IDLE)

    def _handle(self, action: Action):
        if self.paused:
            self.recorder.stop()  # discard anything captured
            self.fsm.set_busy(False)  # STOP set busy in the tap; release it
            self._ui(self._set_title, ICON_PAUSED)
            return
        if action is Action.START:
            self._ui(sounds.play, self.cfg.sound_start)
            self._ui(self._set_title, ICON_RECORDING)
            self.recorder.start()
        elif action in (Action.DISCARD, Action.CANCEL):
            self.recorder.stop()
            self._ui(self._set_title, ICON_IDLE)
        elif action is Action.IGNORED_BUSY:
            self._ui(sounds.play, self.cfg.sound_error)
        elif action is Action.STOP:
            self._ui(sounds.play, self.cfg.sound_stop)
            self.fsm.set_busy(True)  # defense-in-depth: tap already set this at dispatch
            self._ui(self._set_title, ICON_PROCESSING)
            try:
                audio = self.recorder.stop()
                raw = self.transcriber.transcribe(audio)
                log.debug("raw: %r", raw)  # verbatim dictation is sensitive; debug only
                log.info("dictation: %d chars", len(raw))
                text = (
                    self.cleaner.clean(raw)
                    if (self.cleanup_enabled and raw)
                    else raw
                )
                if text:
                    self.last_text = text
                    self._ui(self._set_last, text)
                    # Deliberately off-main: inject() sleeps (paste
                    # settle/restore delays) which would block the main run
                    # loop; the NSPasteboard/CGEvent calls it makes are
                    # contained by inject()'s own try/finally.
                    self.injector.inject(text)
            finally:
                self.fsm.set_busy(False)
                self._ui(self._set_title, ICON_IDLE)
