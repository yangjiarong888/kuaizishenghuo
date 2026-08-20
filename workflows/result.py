"""Stable machine-readable workflow outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowStatus(str, Enum):
    SUCCESS = "success"
    LOGIN_REQUIRED = "login_required"
    LOGIN_FAILED = "login_failed"
    LOGIN_STATE_UNKNOWN = "login_state_unknown"
    OPEN_SHOP_FAILED = "open_shop_failed"
    CHECKOUT_FAILED = "checkout_failed"
    ORDER_PLACED_CLEANUP_FAILED = "order_placed_cleanup_failed"


class WorkflowStage(str, Enum):
    LOGIN = "login"
    OPEN_SHOP = "open_shop"
    CHECKOUT = "checkout"
    CLEANUP = "cleanup"


@dataclass(frozen=True)
class WorkflowResult:
    status: WorkflowStatus
    stage: WorkflowStage
    message: str
    order_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is WorkflowStatus.SUCCESS

    @classmethod
    def success(
        cls,
        *,
        stage: WorkflowStage,
        message: str,
        order_id: str | None = None,
    ) -> "WorkflowResult":
        return cls(
            status=WorkflowStatus.SUCCESS,
            stage=stage,
            message=message,
            order_id=order_id,
        )

    @classmethod
    def failure(
        cls,
        *,
        status: WorkflowStatus,
        stage: WorkflowStage,
        message: str,
        order_id: str | None = None,
    ) -> "WorkflowResult":
        if status is WorkflowStatus.SUCCESS:
            raise ValueError("failure status cannot be SUCCESS")
        return cls(
            status=status,
            stage=stage,
            message=message,
            order_id=order_id,
        )
