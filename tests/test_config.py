from pathlib import Path

from sotto.config import SottoConfig, load_config


def test_load_config_reads_values(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text(
        """
[hotkey]
keycode = 58
min_hold_seconds = 0.5

[models]
asr = "a"
llm = "b"

[cleanup]
enabled = false

[sounds]
start = "Pop"
stop = "Tink"
error = "Basso"

[log]
level = "DEBUG"
"""
    )
    cfg = load_config(p)
    assert cfg.keycode == 58
    assert cfg.min_hold_seconds == 0.5
    assert cfg.asr_model == "a"
    assert cfg.llm_model == "b"
    assert cfg.cleanup_enabled is False
    assert cfg.log_level == "DEBUG"


def test_load_config_defaults_when_missing(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text("")
    cfg = load_config(p)
    assert cfg == SottoConfig()  # all defaults


def test_load_config_missing_file_gives_defaults(tmp_path: Path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg == SottoConfig()
