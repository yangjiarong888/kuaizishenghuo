"""Sanitized Appium failure artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

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
_REDACTION_TOKEN = "[REDACTED]"
_XML_CHARACTER_PATTERNS = {
    "&": r"(?:&(?:amp|#0*38|#x0*26);|&)",
    "<": r"(?:&(?:lt|#0*60|#x0*3c);|<)",
    ">": r"(?:&(?:gt|#0*62|#x0*3e);|>)",
    '"': r'(?:&(?:quot|#0*34|#x0*22);|")',
    "'": r"(?:&(?:apos|#0*39|#x0*27);|')",
}


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


def redact_explicit_values(
    text: str,
    redact_values: Iterable[str] = (),
    *,
    replacement: str = _REDACTION_TOKEN,
) -> str:
    """Replace raw or XML-entity encoded sensitive values deterministically."""
    sanitized = text or ""
    values = {
        str(value).strip() for value in redact_values if str(value).strip()
    }
    for value in sorted(values, key=len, reverse=True):
        pattern = "".join(
            _XML_CHARACTER_PATTERNS.get(character, re.escape(character))
            for character in value
        )
        sanitized = re.sub(pattern, lambda _match: replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def sanitize_xml(text: str, redact_values: Iterable[str] = ()) -> str:
    """Redact secret-like values and personal numeric identifiers."""
    sanitized = _KEYED_ATTRIBUTE.sub(rf"\1{_REDACTION_TOKEN}\3", text or "")
    sanitized = _PHONE_LIKE.sub(_REDACTION_TOKEN, sanitized)
    sanitized = _SHORT_CODE_ATTRIBUTE.sub(rf"\1{_REDACTION_TOKEN}\2", sanitized)
    return redact_explicit_values(sanitized, redact_values)


def capture_failure(
    driver,
    action: str,
    artifacts_dir: str | Path = "logs",
    include_screenshot: bool = True,
    redact_values: Iterable[str] = (),
) -> FailureArtifacts:
    """Capture sanitized source evidence and, when allowed, a screenshot."""
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    action_tag = _safe_action(action)
    prefix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{action_tag}"
    screenshot_path = root / f"{prefix}.png" if include_screenshot else None
    source_path = root / f"{prefix}.xml"
    saved_screenshot = None
    saved_source = None

    if include_screenshot:
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
        source_path.write_text(
            sanitize_xml(driver.page_source, redact_values=redact_values), encoding="utf-8"
        )
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
