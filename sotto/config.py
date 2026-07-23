"""Load sotto's config.toml into a flat dataclass with defaults."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SottoConfig:
    keycode: int = 61  # Right Option
    min_hold_seconds: float = 0.3
    asr_model: str = "mlx-community/parakeet-tdt-0.6b-v2"
    llm_model: str = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    cleanup_enabled: bool = True
    sound_start: str = "Pop"
    sound_stop: str = "Tink"
    sound_error: str = "Basso"
    log_level: str = "INFO"


def load_config(path: Path) -> SottoConfig:
    if not path.exists():
        return SottoConfig()
    data = tomllib.loads(path.read_text())
    d = SottoConfig()
    hotkey = data.get("hotkey", {})
    models = data.get("models", {})
    cleanup = data.get("cleanup", {})
    sounds = data.get("sounds", {})
    log = data.get("log", {})
    return SottoConfig(
        keycode=hotkey.get("keycode", d.keycode),
        min_hold_seconds=hotkey.get("min_hold_seconds", d.min_hold_seconds),
        asr_model=models.get("asr", d.asr_model),
        llm_model=models.get("llm", d.llm_model),
        cleanup_enabled=cleanup.get("enabled", d.cleanup_enabled),
        sound_start=sounds.get("start", d.sound_start),
        sound_stop=sounds.get("stop", d.sound_stop),
        sound_error=sounds.get("error", d.sound_error),
        log_level=log.get("level", d.log_level),
    )
