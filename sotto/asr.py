"""Parakeet ASR: numpy waveform in, text out. Model loaded once."""

from __future__ import annotations

import numpy as np


class Transcriber:
    def __init__(self, model_id: str):
        from parakeet_mlx import from_pretrained  # deferred: heavy import

        self.model = from_pretrained(model_id)

    def transcribe(self, audio: np.ndarray) -> str:
        import mlx.core as mx
        from parakeet_mlx.audio import get_logmel

        if audio.size == 0:
            return ""
        mel = get_logmel(mx.array(audio), self.model.preprocessor_config)
        results = self.model.generate(mel)
        return results[0].text.strip() if results else ""
