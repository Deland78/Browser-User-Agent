"""Logging configuration utilities."""

from __future__ import annotations

import json
import logging
from logging.config import dictConfig
from pathlib import Path
from typing import Any

from .settings import settings


class JsonFormatter(logging.Formatter):
    """Serialize log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            data["stack_info"] = record.stack_info

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in data:
                continue
            if key in {"args", "msg"}:
                continue
            try:
                json.dumps({key: value})
                data[key] = value
            except (TypeError, ValueError):
                data[key] = str(value)

        return json.dumps(data, ensure_ascii=False)


def _build_handlers(log_dir: Path) -> dict[str, Any]:
    """Return handler configuration for both console and rotating file logs."""
    file_path = log_dir / "backend.log"
    log_dir.mkdir(parents=True, exist_ok=True)

    return {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.log_level,
            "formatter": "json",
        },
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": "json",
            "filename": str(file_path),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    }


def configure_logging() -> None:
    """Configure application logging with structured JSON output."""
    handlers = _build_handlers(settings.log_directory)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
            },
            "handlers": handlers,
            "root": {
                "level": settings.log_level,
                "handlers": list(handlers.keys()),
            },
        }
    )


# Configure logging when module is imported to ensure early availability.
configure_logging()
