"""E2E 流程编排（与 Page Object 分离）。"""

from flows.shop_home_flow import (
    PHASE_DETAIL_CART_BANNER,
    PHASE_HOME_ADD_CART_BADGE,
    PHASE_HOME_LIST_FILTERS,
    PHASE_KINGKONG_DAILY_BAIHUO,
    SHOP_HOME_FLOW_PHASE_IDS,
    PhaseEndHook,
    PhaseOutcome,
    run_shop_home_flow,
)

__all__ = (
    "PHASE_DETAIL_CART_BANNER",
    "PHASE_HOME_ADD_CART_BADGE",
    "PHASE_HOME_LIST_FILTERS",
    "PHASE_KINGKONG_DAILY_BAIHUO",
    "SHOP_HOME_FLOW_PHASE_IDS",
    "PhaseEndHook",
    "PhaseOutcome",
    "run_shop_home_flow",
)
