import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".gymmanager" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # opcional: seguir viendo logs en consola durante desarrollo
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root_logger.addHandler(console)