"""In-memory microphone capture at 16kHz mono float32."""

from __future__ import annotations

import logging
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # matches parakeet's preprocessor_config.sample_rate

log = logging.getLogger("sotto")


class Recorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._chunks = []

        def callback(indata, frames, time_info, status):
            if status:
                log.warning("audio status: %s", status)
            with self._lock:
                self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        try:
            self._stream.start()
        except Exception:
            self._stream.close()
            self._stream = None
            raise

    def stop(self) -> np.ndarray:
        """Stop and return the mono float32 waveform (may be empty)."""
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks)[:, 0]
            self._chunks = []
        return audio
