"""Entry point: python -m sotto"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

from sotto.app import SottoApp
from sotto.config import load_config

CONFIG_PATH = Path(
    os.environ.get("SOTTO_CONFIG", Path(__file__).resolve().parent.parent / "config.toml")
)
LOG_PATH = Path.home() / "Library" / "Logs" / "sotto.log"


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=1_000_000, backupCount=2
    )
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )
    logging.getLogger("sotto").info("sotto starting")
    SottoApp(cfg).run()


if __name__ == "__main__":
    main()
