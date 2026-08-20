"""Explicit, non-submitting-by-default takeout workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from workflows.login_workflow import (
    LoginAction,
    StateDetector,
    detect_login_state,
    ensure_logged_in,
)
from workflows.result import WorkflowResult, WorkflowStage, WorkflowStatus


def _default_open_shop(driver: object) -> bool:
    from pages.takeout_page import open_wangwang_supermarket_from_takeout_home

    return bool(open_wangwang_supermarket_from_takeout_home(driver))


def _build_takeout_page(driver: object):
    from pages.takeout_page import TakeoutPageBase

    return TakeoutPageBase(driver)


def run_takeout_order_flow(
    *,
    login_page: object,
    driver: object | None = None,
    takeout_page: object | None = None,
    submit_order: bool = False,
    checkout_kwargs: Mapping[str, Any] | None = None,
    state_detector: StateDetector = detect_login_state,
    login_action: LoginAction | None = None,
    open_shop: Callable[[], bool] | None = None,
) -> WorkflowResult:
    """Open a shop and run checkout with an explicit submission gate."""
    login_result = ensure_logged_in(
        login_page,
        state_detector=state_detector,
        login_action=login_action,
    )
    if not login_result.ok:
        return login_result

    opener = open_shop
    if opener is None and driver is not None:
        opener = lambda: _default_open_shop(driver)
    if opener is None:
        return WorkflowResult.failure(
            status=WorkflowStatus.OPEN_SHOP_FAILED,
            stage=WorkflowStage.OPEN_SHOP,
            message="缺少可验证的进店动作",
        )
    try:
        opened = bool(opener())
    except Exception:
        opened = False
    if not opened:
        return WorkflowResult.failure(
            status=WorkflowStatus.OPEN_SHOP_FAILED,
            stage=WorkflowStage.OPEN_SHOP,
            message="外卖店铺打开失败",
        )

    page = takeout_page
    if page is None and driver is not None:
        page = _build_takeout_page(driver)
    if page is None:
        return WorkflowResult.failure(
            status=WorkflowStatus.CHECKOUT_FAILED,
            stage=WorkflowStage.CHECKOUT,
            message="缺少外卖页面对象",
        )

    options = dict(checkout_kwargs or {})
    options["submit_order"] = bool(submit_order)
    try:
        checkout_ok = bool(page.run_shop_checkout_pay_and_cancel_flow(**options))
    except Exception:
        checkout_ok = False
    submitted = bool(getattr(page, "_takeout_order_submitted", False))

    if not checkout_ok:
        if submitted:
            return WorkflowResult.failure(
                status=WorkflowStatus.ORDER_PLACED_CLEANUP_FAILED,
                stage=WorkflowStage.CLEANUP,
                message="订单已提交，但结果确认或取消清理失败",
            )
        return WorkflowResult.failure(
            status=WorkflowStatus.CHECKOUT_FAILED,
            stage=WorkflowStage.CHECKOUT,
            message="外卖结算失败，未确认订单提交",
        )

    return WorkflowResult.success(
        stage=WorkflowStage.CLEANUP if submitted else WorkflowStage.CHECKOUT,
        message="外卖流程完成" if submitted else "外卖结算预览完成",
    )
