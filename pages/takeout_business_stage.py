"""Ordered, evidence-producing boundaries for the full takeout journey."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from commons.diagnostics import capture_failure
from commons.logger import setup_logger


logger = setup_logger(__name__)


@dataclass(frozen=True)
class TakeoutStageResult:
    number: int
    name: str
    value: object


class TakeoutStageError(AssertionError):
    def __init__(self, number: int, name: str):
        super().__init__(f"takeout stage failed {number:02d}_{name}")
        self.number = number
        self.name = name


def run_takeout_stage(
    page, number: int, name: str, action: Callable[[], object]
) -> TakeoutStageResult:
    label = f"{number:02d}_{name}"
    logger.info("阶段开始 %s", label)
    try:
        value = action()
        if value is False or value is None:
            raise AssertionError(label)
    except Exception as exc:
        capture_failure(page.driver, label, "artifacts/takeout_full_business")
        logger.error("阶段失败 %s error=%s", label, type(exc).__name__)
        raise TakeoutStageError(number, name) from exc
    logger.info("阶段通过 %s", label)
    return TakeoutStageResult(number, name, value)
