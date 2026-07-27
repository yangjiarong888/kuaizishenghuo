"""UTF-8 logging with managed handlers and keyed-secret redaction."""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


_log_file_path_cache: Optional[Path] = None
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|verification[_ -]?code|pay[_ -]?password|token)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


def _sanitize_log_file_tag(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", (raw or "").strip()).strip("_")
    return value[:48] if value else ""


def _log_file_tag_from_env_or_argv() -> str:
    configured = (os.environ.get("CHOPSTICKLIFE_LOG_FILE_TAG") or "").strip()
    if configured:
        return _sanitize_log_file_tag(configured)
    for index, argument in enumerate(sys.argv):
        if argument.lower() == "--method" and index + 1 < len(sys.argv):
            return _sanitize_log_file_tag(sys.argv[index + 1])
    return ""


def redact_text(value: object) -> str:
    """Redact values paired with known secret-bearing keys."""
    return _SECRET_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>",
        str(value),
    )


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True


def _build_log_path() -> Path:
    log_dir = Path(os.environ.get("CHOPSTICKLIFE_LOG_DIR") or "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = _log_file_tag_from_env_or_argv()
    suffix = f"_{tag}" if tag else ""
    return log_dir / f"chopsticklife{suffix}_{timestamp}.log"


def setup_logger(name=None, log_level=logging.INFO) -> logging.Logger:
    """Return a logger with exactly one managed file and console handler."""
    global _log_file_path_cache
    if _log_file_path_cache is None:
        _log_file_path_cache = _build_log_path()

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, "_chopsticks_managed", False):
            logger.removeHandler(handler)
            handler.close()

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    redactor = RedactingFilter()
    file_handler = logging.FileHandler(_log_file_path_cache, encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)
    for handler in (file_handler, console_handler):
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        handler.addFilter(redactor)
        handler._chopsticks_managed = True
        logger.addHandler(handler)
    return logger
