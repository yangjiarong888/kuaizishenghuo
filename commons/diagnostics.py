"""Sanitized Appium failure artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from commons.logger import setup_logger


logger = setup_logger(__name__)
_ACTION_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")
_KEYED_ATTRIBUTE = re.compile(
    r"(?i)((?:password|passwd|pwd|verification[_ -]?code|"
    r"pay[_ -]?password|token)\s*=\s*[\"'])(.*?)([\"'])"
)
_PHONE_LIKE = re.compile(r"(?<!\d)(?:\d[ -]?){6,14}\d(?!\d)")
_SHORT_CODE_ATTRIBUTE = re.compile(
    r"((?:text|content-desc)\s*=\s*[\"'])\d{4,8}([\"'])"
)


@dataclass(frozen=True)
class FailureArtifacts:
    activity: str
    context: str
    screenshot: Path | None
    page_source: Path | None


def _safe_driver_value(driver, attribute: str) -> str:
    try:
        return str(getattr(driver, attribute) or "")
    except Exception:
        return ""


def _safe_action(action: str) -> str:
    value = _ACTION_PATTERN.sub("_", (action or "").strip()).strip("_")
    return value[:48] or "failure"


def sanitize_xml(text: str) -> str:
    """Redact secret-like values and personal numeric identifiers."""
    sanitized = _KEYED_ATTRIBUTE.sub(r"\1<redacted>\3", text or "")
    sanitized = _PHONE_LIKE.sub("<redacted>", sanitized)
    return _SHORT_CODE_ATTRIBUTE.sub(r"\1<redacted>\2", sanitized)


def capture_failure(
    driver, action: str, artifacts_dir: str | Path = "logs"
) -> FailureArtifacts:
    """Capture independent screenshot/source evidence without raising."""
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    action_tag = _safe_action(action)
    prefix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{action_tag}"
    screenshot_path = root / f"{prefix}.png"
    source_path = root / f"{prefix}.xml"
    saved_screenshot = None
    saved_source = None

    try:
        if driver.save_screenshot(str(screenshot_path)):
            saved_screenshot = screenshot_path
    except Exception as exc:
        logger.warning(
            "failure screenshot unavailable action=%s error_type=%s",
            action_tag,
            type(exc).__name__,
        )

    try:
        source_path.write_text(sanitize_xml(driver.page_source), encoding="utf-8")
        saved_source = source_path
    except Exception as exc:
        logger.warning(
            "failure page source unavailable action=%s error_type=%s",
            action_tag,
            type(exc).__name__,
        )

    return FailureArtifacts(
        activity=_safe_driver_value(driver, "current_activity"),
        context=_safe_driver_value(driver, "current_context"),
        screenshot=saved_screenshot,
        page_source=saved_source,
    )
