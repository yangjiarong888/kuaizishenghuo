"""阶段：限时特价 / 新品优选 Tab 与主列表长滑回顶。"""
from __future__ import annotations

import time

from commons.logger import setup_logger
from flows.shop_home_flow_types import ShopHomeFlowPage

logger = setup_logger(__name__)


def run(page: ShopHomeFlowPage) -> bool:
    page.run_mall_list_filters_scroll_and_back_top()
    time.sleep(0.45)
    logger.info(
        "限时特价/新品优选已在上一段完成 Tab 与列表浏览；跳过首页 iv_add_cart（避免与详情加购重复）"
    )
    return True
