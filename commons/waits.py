"""Deterministic condition and element waiting primitives."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class RequiredElementNotFound(TimeoutError):
    """Raised when a required UI element does not appear before its deadline."""


def wait_until(
    predicate: Callable[[], T],
    *,
    timeout: float,
    interval: float = 0.1,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> T | bool:
    """Poll a predicate with a monotonic deadline."""
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
    if interval <= 0:
        raise ValueError("interval must be positive")
    deadline = clock() + timeout
    while True:
        result = predicate()
        if result:
            return result
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        sleeper(min(interval, remaining))


def find_optional(driver, locator, *, timeout: float, interval: float = 0.1):
    """Return the first matching element, or ``None`` after timeout."""

    def locate():
        elements = driver.find_elements(*locator)
        return elements[0] if elements else None

    result = wait_until(locate, timeout=timeout, interval=interval)
    return result if result is not False else None


def find_required(
    driver,
    locator,
    *,
    timeout: float,
    action: str,
    interval: float = 0.1,
):
    """Return a required element or raise an actionable timeout."""
    element = find_optional(driver, locator, timeout=timeout, interval=interval)
    if element is None:
        raise RequiredElementNotFound(
            f"Required element not found action={action!r} by={locator[0]!r} "
            f"value={locator[1]!r} timeout={timeout}"
        )
    return element
