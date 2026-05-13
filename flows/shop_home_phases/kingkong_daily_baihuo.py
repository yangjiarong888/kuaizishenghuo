"""阶段：金刚区日用百货分类 → 选规格校验 → 回首页。"""
from __future__ import annotations

import time

from commons.logger import setup_logger
from flows.shop_home_flow_types import ShopHomeFlowPage

logger = setup_logger(__name__)


def run(page: ShopHomeFlowPage) -> bool:
    if not page.tap_mall_kingkong_daily_baihuo_via_popup():
        logger.error("金刚区：未能打开全部分类或未进入「日用百货」")
        return False
    page.swipe_mall_kingkong_category_list_down(5, settle_sec=5.0)
    time.sleep(0.45)
    if not page.run_category_spec_add_verify_line_qty(
        random_pick=True, log_prefix="日用百货分类"
    ):
        logger.error("日用百货分类：选规格加购或行数量校验失败")
        return False
    if not page.leave_mall_category_to_mall_home():
        logger.warning(
            "日用百货：离开分类页后仍未确认商城首页，仍尝试限时特价/新品优选"
        )
    for _mall_try in range(3):
        if page.ensure_mall_tab(1.0):
            break
        time.sleep(0.75)
    else:
        logger.warning("返回后多次点击「商城」Tab 未成功，仍继续后续步骤")
    time.sleep(0.55)
    return True
