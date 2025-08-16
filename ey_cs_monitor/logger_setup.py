import json
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import colorlog


def setup_logger(log_path: str) -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ey_cs_monitor")
    logger.setLevel(logging.INFO)

    if not any(isinstance(h, colorlog.StreamHandler) for h in logger.handlers):
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] %(levelname)s:%(reset)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
    file_handler.setLevel(logging.INFO)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            data = {
                "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "msg": record.getMessage(),
            }
            if hasattr(record, "extra") and isinstance(record.extra, dict):
                data.update(record.extra)
            return json.dumps(data)

    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    return logger
