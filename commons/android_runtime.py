"""Android device discovery and post-session launch policy."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from typing import Any

from commons.logger import setup_logger


logger = setup_logger(__name__)


def _start_android_activity(driver, app_package: str, app_activity: str) -> None:
    legacy_start = getattr(driver, "start_activity", None)
    if callable(legacy_start):
        legacy_start(app_package, app_activity)
        return
    driver.execute_script(
        "mobile: startActivity",
        {
            "intent": f"{app_package}/{app_activity}",
            "wait": True,
        },
    )


def detect_first_adb_device_id(
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    """Return the first connected ADB device, or ``None`` at the boundary."""
    try:
        completed = run(
            ["adb", "devices"], capture_output=True, text=True, timeout=8
        )
    except Exception as exc:
        logger.debug("adb devices failed error_type=%s", type(exc).__name__)
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return None


def detect_launchable_activity(
    app_package: str,
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    """Resolve the package launch Activity through ADB."""
    try:
        completed = run(
            [
                "adb",
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                app_package,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        logger.debug("resolve activity failed error_type=%s", type(exc).__name__)
        return None
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines or "/" not in lines[-1]:
        return None
    package, activity = lines[-1].split("/", 1)
    if not package or not activity:
        return None
    return f"{package}{activity}" if activity.startswith(".") else activity


def post_session_android_launch(driver, config, start_mode=None) -> str:
    """Apply the configured post-session launch policy and return its mode."""
    raw_mode = (
        start_mode
        if start_mode is not None
        else os.environ.get("START_MODE", "cold")
    )
    normalized = (raw_mode or "cold").strip().lower()
    if normalized in {"off", "none", "skip", "0", "false", "no"}:
        return "off"
    if normalized == "activate":
        driver.activate_app(config.app_package)
        return "activate"
    try:
        driver.terminate_app(config.app_package)
    except Exception as exc:
        logger.debug("terminate_app failed error_type=%s", type(exc).__name__)
    if config.app_activity:
        _start_android_activity(driver, config.app_package, config.app_activity)
    else:
        activity = detect_launchable_activity(config.app_package)
        if activity:
            _start_android_activity(driver, config.app_package, activity)
        else:
            driver.activate_app(config.app_package)
    return "cold"
