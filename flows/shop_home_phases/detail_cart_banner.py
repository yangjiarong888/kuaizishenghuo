"""阶段：详情深度流 → 悬浮购物车 → Banner。"""
from __future__ import annotations

from commons.logger import setup_logger
from flows.shop_home_flow_types import ShopHomeFlowPage

logger = setup_logger(__name__)


def run(page: ShopHomeFlowPage) -> bool:
    if not page.run_mall_product_detail_deep_flow():
        logger.error("商城商品详情深度流失败")
        return False
    if not page.tap_floating_or_entry_cart():
        return False
    if not page.tap_top_back():
        logger.warning("购物车页返回可能失败，仍继续")
    if not page.ensure_mall_tab():
        logger.warning("返回后重进商城 Tab")
    if not page.tap_banner_area():
        return False
    if not page.tap_top_back():
        logger.warning("Banner 活动页返回可能失败，仍继续")
    if not page.ensure_mall_tab():
        logger.warning("返回后重进商城 Tab")
    return True
