"""商城首页 E2E 各阶段实现（由 ``flows.shop_home_flow`` 编排）。"""

from flows.shop_home_phases.detail_cart_banner import run as run_detail_cart_banner
from flows.shop_home_phases.home_add_cart_badge import run as run_home_add_cart_badge
from flows.shop_home_phases.home_list_filters import run as run_home_list_filters
from flows.shop_home_phases.kingkong_daily_baihuo import run as run_kingkong_daily_baihuo

__all__ = (
    "run_kingkong_daily_baihuo",
    "run_home_list_filters",
    "run_detail_cart_banner",
    "run_home_add_cart_badge",
)
