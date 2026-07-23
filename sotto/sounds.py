"""System sound cues via NSSound (low latency, non-blocking)."""

from __future__ import annotations


def play(name: str) -> None:
    from AppKit import NSSound

    sound = NSSound.soundNamed_(name)
    if sound is not None:
        sound.play()
