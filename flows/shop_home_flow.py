"""
商城首页完整 E2E 编排入口。

阶段实现位于 ``flows.shop_home_phases``；类型约定见 ``flows.shop_home_flow_types``。
"""
from __future__ import annotations

import time
from typing import AbstractSet, Any, Callable, FrozenSet, Literal, Optional

from commons.logger import setup_logger
from flows.shop_home_flow_types import ShopHomeFlowPage
from flows.shop_home_phases import (
    run_detail_cart_banner,
    run_home_add_cart_badge,
    run_home_list_filters,
    run_kingkong_daily_baihuo,
)

logger = setup_logger(__name__)

PhaseOutcome = Literal["ok", "fail", "skip"]

# 阶段 id（用于 ``skip_phases`` 与回调）
PHASE_KINGKONG_DAILY_BAIHUO = "kingkong_daily_baihuo"
PHASE_HOME_LIST_FILTERS = "home_list_filters"
PHASE_DETAIL_CART_BANNER = "detail_cart_banner"
PHASE_HOME_ADD_CART_BADGE = "home_add_cart_badge"

_PHASE_LABELS: dict[str, str] = {
    PHASE_KINGKONG_DAILY_BAIHUO: "金刚区日用百货+分类选规格",
    PHASE_HOME_LIST_FILTERS: "限时特价/新品优选+主列表滑动",
    PHASE_DETAIL_CART_BANNER: "详情深度流+悬浮购物车+Banner",
    PHASE_HOME_ADD_CART_BADGE: "首页加购+角标校验",
}

# 阶段结束回调：(phase_id, outcome, elapsed_sec, page)；outcome 为 ``skip`` 表示被配置跳过
PhaseEndHook = Optional[Callable[[str, PhaseOutcome, float, Any], None]]


def _run_phase(
    phase_id: str,
    page: ShopHomeFlowPage,
    fn: Callable[[ShopHomeFlowPage], bool],
    *,
    skip_phases: AbstractSet[str],
    on_phase_end: PhaseEndHook,
) -> bool:
    label = _PHASE_LABELS.get(phase_id, phase_id)
    if phase_id in skip_phases:
        logger.info("[阶段跳过] %s (%s)", label, phase_id)
        if on_phase_end is not None:
            on_phase_end(phase_id, "skip", 0.0, page)
        return True
    logger.info("[阶段开始] %s (%s)", label, phase_id)
    t0 = time.perf_counter()
    outcome: PhaseOutcome = "fail"
    ok = False
    try:
        ok = bool(fn(page))
        outcome = "ok" if ok else "fail"
    except Exception:
        elapsed = time.perf_counter() - t0
        logger.exception(
            "[阶段异常] %s (%s) 用时 %.2fs", label, phase_id, elapsed
        )
        if on_phase_end is not None:
            on_phase_end(phase_id, "fail", elapsed, page)
        return False
    elapsed = time.perf_counter() - t0
    logger.info(
        "[阶段结束] %s (%s) outcome=%s 用时 %.2fs",
        label,
        phase_id,
        outcome,
        elapsed,
    )
    if on_phase_end is not None:
        on_phase_end(phase_id, outcome, elapsed, page)
    return ok


def run_shop_home_flow(
    page: ShopHomeFlowPage,
    *,
    skip_phases: Optional[AbstractSet[str]] = None,
    on_phase_end: PhaseEndHook = None,
) -> bool:
    """
    完整流程：商城 Tab
    → **日用百货**（金刚区弹层分类、选规格加购）→ 回首页
    → **限时特价 / 新品优选**（``run_mall_list_filters_scroll_and_back_top``：含长滑回顶）
    → **不再**重复「再切新品优选 + 长滑 + 首页 iv_add_cart」（与详情深度流里详情加购重复）
    → 主列表详情深度流 → 悬浮购物车 → Banner → 末次首页加购 → 角标 +1。

    ``page`` 为 ``ShopHomePage`` 实例（本模块不 import 该类，避免循环依赖）。

    ``skip_phases``：传入阶段 id 集合可跳过对应段（冒烟/调试）；跳过段仍会触发
    ``on_phase_end(..., \"skip\", 0.0, page)``。

    ``on_phase_end``：每阶段结束调用一次，便于接截图、Allure、CI 上报；签名
    ``(phase_id, outcome, elapsed_sec, page)``，其中 ``outcome`` 为
    ``\"ok\" | \"fail\" | \"skip\"``。
    """
    skip_f: FrozenSet[str] = frozenset(skip_phases or ())

    if not page.ensure_mall_tab():
        return False
    time.sleep(0.5)

    if not _run_phase(
        PHASE_KINGKONG_DAILY_BAIHUO,
        page,
        run_kingkong_daily_baihuo,
        skip_phases=skip_f,
        on_phase_end=on_phase_end,
    ):
        return False
    if not _run_phase(
        PHASE_HOME_LIST_FILTERS,
        page,
        run_home_list_filters,
        skip_phases=skip_f,
        on_phase_end=on_phase_end,
    ):
        return False
    if not _run_phase(
        PHASE_DETAIL_CART_BANNER,
        page,
        run_detail_cart_banner,
        skip_phases=skip_f,
        on_phase_end=on_phase_end,
    ):
        return False
    return _run_phase(
        PHASE_HOME_ADD_CART_BADGE,
        page,
        run_home_add_cart_badge,
        skip_phases=skip_f,
        on_phase_end=on_phase_end,
    )


# 供脚本/类型检查：与 run_shop_home_flow 的 ``skip_phases`` 取值一致
SHOP_HOME_FLOW_PHASE_IDS: FrozenSet[str] = frozenset(
    {
        PHASE_KINGKONG_DAILY_BAIHUO,
        PHASE_HOME_LIST_FILTERS,
        PHASE_DETAIL_CART_BANNER,
        PHASE_HOME_ADD_CART_BADGE,
    }
)
