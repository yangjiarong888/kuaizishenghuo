"""阶段：末次首页加购 → 角标 +1 校验。"""
from __future__ import annotations

import time

from commons.logger import setup_logger
from flows.shop_home_flow_types import ShopHomeFlowPage

logger = setup_logger(__name__)


def run(page: ShopHomeFlowPage) -> bool:
    logger.info("读取购物车 Tab 角标（加购前）…")
    before = page.read_cart_badge_digit()
    logger.info("加购前购物车角标解析值: %s", before)
    if not page.tap_first_add_cart_on_home():
        return False
    ok, branch = page.handle_add_cart_followups()
    if not ok:
        return False
    time.sleep(0.65)
    if not page.ensure_mall_tab():
        logger.warning("加购后未能确认商城 Tab，仍尝试读角标")
    after = page.read_cart_badge_digit_expect_increase(
        before, min_delta=1, wait_sec=26.0, step_sec=1.0
    )
    logger.info("加购后购物车角标解析值: %s（分支=%s）", after, branch)
    if before is not None and after is not None:
        if after >= before + 1:
            logger.info("校验通过：角标由 %s 增至 %s", before, after)
            logger.info(
                "run_shop_home_flow 全部步骤已完成（单次线性流程，无循环），返回 True"
            )
            return True
        logger.error("角标未 +1：before=%s after=%s", before, after)
        return False
    if after is not None and before is None:
        logger.info("加购前无数角标，加购后=%s，视为流程已执行", after)
        logger.info(
            "run_shop_home_flow 全部步骤已完成（单次线性流程，无循环），返回 True"
        )
        return True
    logger.error("无法解析购物车角标，无法校验 +1；请 Inspector 核对角标控件 id")
    return False
