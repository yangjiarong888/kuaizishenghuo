"""商城首页自动化：金刚区、返回、购物车、Banner、加购与多规格弹窗。"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple, Any

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_BACK_ID_SUFFIXES,
    SHOP_ID_BOTTOM_POPUP,
    SHOP_ID_CHOOSE_RECYCLER,
    SHOP_ID_CV_CART,
    SHOP_ID_DIALOG_CHOOSE_CONTAINER,
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_ID_FLOAT_VIEW,
    SHOP_ID_IV_ADD_CART,
    SHOP_ID_IV_BANNER,
    SHOP_ID_IV_CART,
    SHOP_ID_IV_SHOPPING_CART,
    SHOP_ID_IV_UP_TO_TOP,
    SHOP_ID_RL_CART,
    SHOP_ID_RL_SHOPPING_CART,
    SHOP_ID_ACTIVITY_FILTER,
    SHOP_KINGKONG_HOT_SNACKS,
    SHOP_PACKAGES,
    SHOP_TEXT_KEFU_PAGE_MARKERS,
    SHOP_TEXT_LIMITED_SPECIAL,
    SHOP_TEXT_LIMITED_SPECIAL_ALT,
    SHOP_ID_MALL_ADD_SHOP_CAR,
    SHOP_ID_MALL_DETAIL_VIEWPAGER,
    SHOP_ID_RV_CONTENT,
)

from pages.shop_mall_cart_badge import MallCartBadgeReader
from pages.shop_mall_category_page import MallCategoryPage
from pages.shop_mall_context import ShopMallContext
from pages.shop_mall_home_chrome import MallHomeChrome
from pages.shop_mall_product_detail_page import MallProductDetailPage
from pages.shop_mall_spec_sheet import MallSpecSheet

logger = setup_logger(__name__)


class ShopHomePage:
    """当前 driver 已连上设备；先 ``ensure_mall_tab`` 再跑 ``run_shop_home_flow``。"""

    def __init__(self, driver: WebDriver, wait_sec: float = 18.0):
        self.driver = driver
        self.wait_sec = wait_sec
        self._mall_ctx = ShopMallContext(driver)
        self._badge = MallCartBadgeReader(self._mall_ctx)
        self._spec = MallSpecSheet(
            self._mall_ctx, lambda: self._login_like_screen_visible()
        )
        self._category = MallCategoryPage(self)
        self._detail = MallProductDetailPage(self)
        self._home_chrome = MallHomeChrome(self)

    def _window_size(self) -> Tuple[int, int]:
        return self._mall_ctx.window_size()

    def _nearest_clickable_ancestor(self, el, max_hops: int = 8):
        return self._mall_ctx.nearest_clickable_ancestor(el, max_hops=max_hops)

    def _rid(self, pkg: str, suffix: str) -> str:
        return self._mall_ctx.rid(pkg, suffix)

    def _shop_packages_prioritized(self) -> Tuple[str, ...]:
        """当前前台包名优先，减少返回键查找轮询（隐式等待非 0 时避免数十秒卡顿）。"""
        return self._mall_ctx.shop_packages_prioritized()

    def _first_displayed_by_pkg_id(self, suffix: str):
        return self._mall_ctx.first_displayed_by_pkg_id(suffix)

    def _all_displayed_by_pkg_id(self, suffix: str) -> List:
        return self._mall_ctx.all_displayed_by_pkg_id(suffix)

    def ensure_mall_tab(self, settle: float = 1.2) -> bool:
        """点击底部「商城」Tab（与外卖 Tab 同类 resource-id 结构）。"""
        h = self._window_size()[1]
        y_min = int(h * 0.66)
        for pkg in SHOP_PACKAGES:
            xp = (
                f'//android.widget.TextView[@resource-id="{pkg}:id/tab_text_tv" '
                f'and @text="商城"]'
            )
            try:
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        if int(el.location.get("y", 0)) < y_min:
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击底部「商城」Tab（%s）", pkg)
                        time.sleep(settle)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//android.widget.TextView[@text="商城"]'
            ):
                try:
                    if not el.is_displayed():
                        continue
                    if int(el.location.get("y", 0)) < y_min:
                        continue
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击底部「商城」（XPath 文案）")
                    time.sleep(settle)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        logger.error("未点到底部「商城」Tab")
        return False

    def tap_kingkong_hot_snacks(self) -> bool:
        """金刚区点击「爆款零食」。"""
        return self._home_chrome.tap_kingkong_hot_snacks()

    def tap_mall_kingkong_open_all_categories_popup(self) -> bool:
        """
        在当前屏点击「全部分类」以打开 ``popup_win``。
        典型路径：已点金刚区「爆款零食」进入分类页后，再点标题区「全部分类」出弹层。
        """
        return self._category.tap_mall_kingkong_open_all_categories_popup()

    def tap_mall_category_in_all_categories_popup(self, category_name: str) -> bool:
        """在「全部分类」弹层内点击 ``tv_category`` 指定文案（如日用百货）。"""
        return self._category.tap_mall_category_in_all_categories_popup(category_name)

    def tap_mall_kingkong_daily_baihuo_via_popup(self) -> bool:
        """
        金刚区「爆款零食」→ 分类页出现「全部分类」弹层 → 点「日用百货」。
        不在商城首屏直接找「全部分类」；必须先进入爆款零食分类页（与 Inspector 一致）。
        """
        return self._category.tap_mall_kingkong_daily_baihuo_via_popup()

    def leave_mall_category_to_mall_home(self) -> bool:
        """
        从金刚区/分类子页返回到商城首页，直到主列表 ``rv_content`` 可见，
        再执行限时特价、新品优选等依赖首页结构的步骤。
        """
        return self._category.leave_mall_category_to_mall_home()

    def tap_top_back(self) -> bool:
        """
        子页左上角返回（优先 iv_back*，否则系统 back）。

        查找期间将隐式等待置 0：否则对每个不存在的 ``pkg:id/suffix`` 可能各等待约 1s，
        多包名轮询后再 ``driver.back()`` 会出现数十秒空白（见分类页离开商城首页日志）。
        """
        with self._mall_ctx.zero_implicit_wait():
            for pkg in self._shop_packages_prioritized():
                for suf in SHOP_BACK_ID_SUFFIXES:
                    rid = self._rid(pkg, suf)
                    try:
                        for el in self.driver.find_elements(AppiumBy.ID, rid):
                            try:
                                if el.is_displayed():
                                    el.click()
                                    logger.info("已点返回（%s）", rid)
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
            for pkg in self._shop_packages_prioritized():
                for suf in SHOP_BACK_ID_SUFFIXES:
                    xp = f'//*[@resource-id="{self._rid(pkg, suf)}"]'
                    try:
                        for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                            try:
                                if el.is_displayed():
                                    el.click()
                                    logger.info("已点返回（XPath %s）", xp[:80])
                                    time.sleep(1.0)
                                    return True
                            except Exception:
                                continue
                    except Exception:
                        pass
            try:
                self.driver.back()
                logger.info("已发送系统 KeyEvent BACK")
                time.sleep(1.0)
                return True
            except Exception:
                return False

    def tap_floating_or_entry_cart(self) -> bool:
        """商城首页购物车入口：悬浮球 / rl_cart / 多 id 兜底。"""
        order = (
            SHOP_ID_IV_SHOPPING_CART,
            SHOP_ID_IV_CART,
            SHOP_ID_RL_SHOPPING_CART,
            SHOP_ID_CV_CART,
            SHOP_ID_FLOAT_VIEW,
        )
        for suf in order:
            el = self._first_displayed_by_pkg_id(suf)
            if el:
                try:
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击购物车入口（%s）", suf)
                    time.sleep(1.3)
                    return True
                except Exception:
                    pass
        el = self._first_displayed_by_pkg_id(SHOP_ID_RL_CART)
        if el:
            try:
                el.click()
                logger.info("已点击购物车容器（rl_cart）")
                time.sleep(1.3)
                return True
            except Exception:
                pass
        w, h = self._window_size()
        for xf, yf in ((0.92, 0.88), (0.88, 0.90), (0.10, 0.90)):
            cx, cy = int(w * xf), int(h * yf)
            try:
                self.driver.execute_script(
                    "mobile: clickGesture", {"x": cx, "y": cy}
                )
                logger.info("购物车坐标兜底 (%d,%d)", cx, cy)
                time.sleep(1.2)
                return True
            except Exception:
                continue
        logger.error("未点到购物车入口")
        return False

    def tap_banner_area(self) -> bool:
        """点击 Banner（优先 iv_banner，失败则点 ViewPager 区域中轴）。"""
        el = self._first_displayed_by_pkg_id(SHOP_ID_IV_BANNER)
        if el:
            try:
                parent = el.find_element(AppiumBy.XPATH, "./..")
                if (parent.get_attribute("clickable") or "").lower() == "true":
                    parent.click()
                else:
                    el.click()
                logger.info("已点击 Banner（iv_banner）")
                time.sleep(1.3)
                return True
            except Exception:
                try:
                    el.click()
                    logger.info("已点击 Banner（iv_banner 自身）")
                    time.sleep(1.3)
                    return True
                except Exception:
                    pass
        for pkg in SHOP_PACKAGES:
            for vp_suffix in ("viewPager", "vp_banner", "banner_vp"):
                rid = self._rid(pkg, vp_suffix)
                try:
                    for el in self.driver.find_elements(AppiumBy.ID, rid):
                        if el.is_displayed():
                            loc = el.location
                            sz = el.size
                            cx = int(loc["x"] + sz["width"] * 0.5)
                            cy = int(loc["y"] + sz["height"] * 0.45)
                            self.driver.execute_script(
                                "mobile: clickGesture", {"x": cx, "y": cy}
                            )
                            logger.info(
                                "已点击 Banner 区（%s 中心）",
                                vp_suffix,
                            )
                            time.sleep(1.3)
                            return True
                except Exception:
                    pass
        # 部分版本大横幅为全宽 ``activity_filter``（文案如「限时特价」），与 Inspector 一致
        if self.tap_mall_text_filter(
            SHOP_TEXT_LIMITED_SPECIAL,
            y_min_ratio=0.26,
            y_max_ratio=0.56,
        ):
            logger.info("已点击 Banner 区（activity_filter「限时特价」）")
            time.sleep(1.2)
            return True
        w, h = self._window_size()
        cx, cy = int(w * 0.5), int(h * 0.34)
        try:
            self.driver.execute_script("mobile: clickGesture", {"x": cx, "y": cy})
            logger.info("已点击 Banner 大致区域 (%d,%d)", cx, cy)
            time.sleep(1.2)
            return True
        except Exception:
            pass
        logger.error("未点到 Banner")
        return False

    def _login_like_screen_visible(self) -> bool:
        act = (self.driver.current_activity or "").lower()
        if "login" in act or "sign" in act:
            return True
        needles = ("请输入手机号", "短信登录", "密码登录", "验证码登录", "手机号登录")
        for n in needles:
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{n}")]'
                ):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _spec_bottom_sheet_visible(self) -> bool:
        for suf in (
            SHOP_ID_BOTTOM_POPUP,
            SHOP_ID_CHOOSE_RECYCLER,
            SHOP_ID_DIALOG_COMPLETE,
            SHOP_ID_DIALOG_CHOOSE_CONTAINER,
        ):
            if self._first_displayed_by_pkg_id(suf):
                return True
        return False

    def _tap_spec_confirm_if_any(self) -> bool:
        el = self._first_displayed_by_pkg_id(SHOP_ID_DIALOG_COMPLETE)
        if el:
            try:
                tx = (el.get_attribute("text") or "").strip()
                if tx == "确定" or "确定" in (el.get_attribute("content-desc") or ""):
                    el.click()
                    logger.info("已点多规格弹层「确定」（dialog_complete）")
                    time.sleep(0.9)
                    return True
            except Exception:
                pass
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//*[@text="确定" and @clickable="true"]'
            ):
                if el.is_displayed():
                    y = int(el.location.get("y", 0))
                    h = self._window_size()[1]
                    if y > int(h * 0.55):
                        el.click()
                        logger.info("已点多规格弹层「确定」（XPath）")
                        time.sleep(0.9)
                        return True
        except Exception:
            pass
        return False

    def _pick_first_spec_option(self) -> bool:
        """在 choose_recycler_view 内点第一个可选规格 TextView（跳过明显标题列）。"""
        rv = self._first_displayed_by_pkg_id(SHOP_ID_CHOOSE_RECYCLER)
        if not rv:
            return True
        skip_tokens = ("数量", "规格", "容量", "口味", "尺寸", "选择")
        try:
            for el in rv.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView"):
                try:
                    if not el.is_displayed():
                        continue
                    tx = (el.text or "").strip()
                    if not tx or len(tx) > 48:
                        continue
                    if any(t in tx for t in skip_tokens) and "1" not in tx and "瓶" not in tx:
                        continue
                    if tx in ("确定", "取消", "加入购物车", "加购"):
                        continue
                    el.click()
                    logger.info("已选规格项: %s", tx[:32])
                    time.sleep(0.35)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return True

    def handle_add_cart_followups(self) -> Tuple[bool, str]:
        """
        加购后的分支：多规格弹窗 或 登录页。
        返回 (ok, message)。
        """
        time.sleep(0.6)
        if self._spec_bottom_sheet_visible():
            self._pick_first_spec_option()
            if not self._tap_spec_confirm_if_any():
                logger.warning("多规格弹层未点到「确定」，仍继续校验角标")
            time.sleep(0.8)
            return True, "spec"
        if self._login_like_screen_visible():
            logger.error("检测到登录相关界面：请先在本机登录后再跑加购与角标校验")
            return False, "login_required"
        return True, "direct"

    def tap_first_add_cart_on_home(self) -> bool:
        """首页列表第一个可见「加购」iv_add_cart。"""
        els = self._all_displayed_by_pkg_id(SHOP_ID_IV_ADD_CART)
        h = self._window_size()[1]
        scored = []
        for el in els:
            try:
                y = int(el.location.get("y", 99999))
                if y > int(h * 0.88):
                    continue
                scored.append((y, el))
            except Exception:
                continue
        scored.sort(key=lambda t: t[0])
        for _, el in scored[:6]:
            try:
                el.click()
                logger.info("已点击加购（iv_add_cart）")
                time.sleep(0.5)
                return True
            except Exception:
                try:
                    self._nearest_clickable_ancestor(el).click()
                    logger.info("已点击加购（可点击祖先）")
                    time.sleep(0.5)
                    return True
                except Exception:
                    continue
        logger.error("未找到可见的 iv_add_cart")
        return False

    def read_cart_badge_digit(self) -> Optional[int]:
        """购物车 Tab 角标；实现见 ``pages.shop_mall_cart_badge.MallCartBadgeReader``。"""
        return self._badge.read_digit()

    def read_cart_badge_digit_expect_increase(
        self,
        baseline: Optional[int],
        *,
        min_delta: int = 1,
        wait_sec: float = 24.0,
        step_sec: float = 1.0,
    ) -> Optional[int]:
        """加购后轮询读角标，直到相对 baseline 至少增加 min_delta。"""
        return self._badge.read_expect_increase(
            baseline,
            min_delta=min_delta,
            wait_sec=wait_sec,
            step_sec=step_sec,
        )

    def tap_mall_text_filter(
        self,
        text: str,
        *,
        y_min_ratio: float = 0.16,
        y_max_ratio: float = 0.72,
    ) -> bool:
        """
        点击商城主区带指定文案的筛选项/标题（如「限时特价」「新品优选」）。
        用多段纵向带避免点到底部导航或悬浮购物车。
        Inspector：活动条/横滑筛选项常为 ``activity_filter``（TextView，文案随活动变）。
        """
        h = self._window_size()[1]
        bands = (
            (y_min_ratio, y_max_ratio),
            (0.14, min(0.76, y_max_ratio + 0.18)),
            (0.12, 0.78),
        )
        for ymin_r, ymax_r in bands:
            y_lo, y_hi = int(h * ymin_r), int(h * ymax_r)
            for pkg in SHOP_PACKAGES:
                rid = self._rid(pkg, SHOP_ID_ACTIVITY_FILTER)
                xp = f'//*[@resource-id="{rid}" and @text="{text}"]'
                try:
                    for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                        try:
                            if not el.is_displayed():
                                continue
                            y = int(el.location.get("y", -1))
                            if not (y_lo <= y <= y_hi):
                                continue
                            self._nearest_clickable_ancestor(el).click()
                            logger.info(
                                "已点击「%s」（activity_filter / %s）",
                                text,
                                pkg,
                            )
                            time.sleep(0.5)
                            return True
                        except Exception:
                            continue
                except Exception:
                    pass
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[@text="{text}"]'
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」（y 带 %.2f–%.2f）", text, ymin_r, ymax_r)
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH,
                    f'//*[contains(@content-desc,"{text}")]',
                ):
                    try:
                        if not el.is_displayed():
                            continue
                        y = int(el.location.get("y", -1))
                        if not (y_lo <= y <= y_hi):
                            continue
                        self._nearest_clickable_ancestor(el).click()
                        logger.info("已点击「%s」（content-desc，y 带）", text)
                        time.sleep(0.5)
                        return True
                    except Exception:
                        continue
            except Exception:
                pass
        logger.warning("未命中可点击文案「%s」", text)
        return False

    def run_mall_filter_limited_special_toggle(self) -> bool:
        """
        限时特价/限时秒杀：点开筛选 → 首屏等待 → 下滑浏览（每滑一次等待渲染）
        → 再点一次关闭筛选，回到初始列表。
        """
        opened = False
        for label in (SHOP_TEXT_LIMITED_SPECIAL, SHOP_TEXT_LIMITED_SPECIAL_ALT):
            if self.tap_mall_text_filter(
                label, y_min_ratio=0.18, y_max_ratio=0.72
            ):
                opened = True
                break
        if not opened:
            return False
        logger.info("限时特价/秒杀筛选已打开，首屏等待 5.0s（列表渲染）")
        time.sleep(5.0)
        self.swipe_mall_main_list_down(5, settle_sec=5.0)
        closed = False
        for label in (SHOP_TEXT_LIMITED_SPECIAL, SHOP_TEXT_LIMITED_SPECIAL_ALT):
            if self.tap_mall_text_filter(
                label, y_min_ratio=0.14, y_max_ratio=0.78
            ):
                closed = True
                break
        if not closed:
            logger.warning("活动条第二次点击未命中，可能已还原或文案已变")
            return False
        logger.info("已完成活动条（限时特价/秒杀）：浏览后关筛选")
        time.sleep(0.4)
        self.recover_mall_list_to_show_tab_bar()
        return True

    def mall_list_gesture_scroll_to_top(
        self,
        strokes: int = 8,
        *,
        x_ratio: float = 0.48,
        y_start_ratio: float = 0.25,
        y_end_ratio: float = 0.88,
    ) -> None:
        """
        手指由上向下拖，使列表向**文档顶部**回滚（相对屏幕 y 增大方向）。
        注意：起点 ``y_start_ratio`` 过小且列表已在顶部时，易触发整页「下拉刷新」；
        分类页请用 ``MallCategoryPage.recover_mall_category_goods_list_to_top`` 或
        ``MallCategoryPage.swipe_within_rv_goods_toward_top``。
        """
        w, h = self._window_size()
        x = int(w * x_ratio)
        y0 = int(h * y_start_ratio)
        y1 = int(h * y_end_ratio)
        for _ in range(strokes):
            try:
                self.driver.swipe(x, y0, x, y1, 420)
            except Exception:
                break
            time.sleep(0.24)

    def recover_mall_category_goods_list_to_top(self) -> None:
        """
        分类页右侧 ``rv_goods``：先 **UiScrollable 回顶** / **仅在列表内**安全区手势，
        避免整页从顶部下拉触发「刷新」；再尝试「回到顶部」按钮微调。
        """
        self._category.recover_mall_category_goods_list_to_top()

    def _kingkong_hot_snacks_label_visible(self) -> bool:
        return self._home_chrome.kingkong_hot_snacks_label_visible()

    def recover_mall_list_to_show_tab_bar(self) -> None:
        """
        长列表滑到底后，横滑 Tab（新品优选等）可能不在屏内。
        优先点「回到顶部」；若无按钮或主列表仍不可见，再用手势拉回顶部区域。
        """
        if self.tap_back_to_top_if_visible():
            time.sleep(0.55)
            if self._is_mall_home_main_list_visible():
                return
        logger.info(
            "无「回到顶部」或主列表仍不可见：手势拉回商城首页上方（Tab/金刚区）"
        )
        self.mall_list_gesture_scroll_to_top(8)
        time.sleep(0.4)

    def tap_new_product_prefer_tab(self) -> bool:
        """
        列表上方 Tab「新品优选」。
        与金刚区相同为 ``tv_title``，文案常为 ``✨新品优选``（非 ``activity_filter`` 精确「新品优选」）。
        """
        return self._home_chrome.tap_new_product_prefer_tab()

    def _swipe_mall_vertical_list_down(
        self,
        times: int,
        settle_sec: float,
        log_name: str,
        *,
        x_ratio: float = 0.48,
    ) -> None:
        """商城内纵向商品列表：上滑翻页 + 每次等待渲染。"""
        w, h = self._window_size()
        x = int(w * x_ratio)
        for i in range(times):
            try:
                self.driver.swipe(x, int(h * 0.72), x, int(h * 0.30), 420)
            except Exception:
                try:
                    self.driver.execute_script(
                        "mobile: swipeGesture",
                        {
                            "left": int(w * 0.22),
                            "top": int(h * 0.36),
                            "width": int(w * 0.56),
                            "height": int(h * 0.48),
                            "direction": "up",
                            "percent": 0.52,
                        },
                    )
                except Exception:
                    pass
            logger.info(
                "%s第 %d/%d 次下滑后等待 %.1fs（列表翻页渲染）",
                log_name,
                i + 1,
                times,
                settle_sec,
            )
            time.sleep(settle_sec)
        logger.info(
            "%s已下滑 %d 次，每次渲染等待 %.1fs", log_name, times, settle_sec
        )

    def swipe_mall_main_list_down(
        self,
        times: int = 5,
        settle_sec: float = 5.0,
    ) -> None:
        """
        商城首页主列表向下滑动浏览（手指自下向上拖，内容向下滚）。

        每次滑动后等待 ``settle_sec`` 秒，便于翻页/懒加载列表数据渲染完成。
        """
        self._swipe_mall_vertical_list_down(
            times, settle_sec, "商城主列表", x_ratio=0.48
        )

    def swipe_mall_kingkong_category_list_down(
        self,
        times: int = 5,
        settle_sec: float = 5.0,
        *,
        first_screen_sec: float = 5.0,
    ) -> None:
        """
        金刚区进入的分类页（如爆款零食）：右侧商品列表上滑浏览，节奏与首页一致。

        分类页常为左栏 + 右列表，横坐标略偏右以减少误触侧栏。
        """
        if first_screen_sec > 0:
            logger.info(
                "金刚区分类页首屏等待 %.1fs（商品列表渲染）", first_screen_sec
            )
            time.sleep(first_screen_sec)
        self._swipe_mall_vertical_list_down(
            times, settle_sec, "金刚区分类商品列表", x_ratio=0.58
        )

    def tap_back_to_top_if_visible(self, *, warn_when_missing: bool = True) -> bool:
        """右侧「回到顶部」箭头（iv_up_to_top）。"""
        el = self._first_displayed_by_pkg_id(SHOP_ID_IV_UP_TO_TOP)
        if el:
            try:
                self._nearest_clickable_ancestor(el).click()
                logger.info("已点击回到顶部（%s）", SHOP_ID_IV_UP_TO_TOP)
                time.sleep(0.85)
                return True
            except Exception:
                pass
        if warn_when_missing:
            logger.warning("未找到可见的「回到顶部」%s", SHOP_ID_IV_UP_TO_TOP)
        return False

    def run_mall_list_filters_scroll_and_back_top(self) -> bool:
        """
        限时特价（开筛选→首屏等 5s→下滑×5 每次等 5s→关筛选）→ 新品优选
        → 首屏等 5s → 下滑×5 每次等 5s → 回到顶部。
        任一步失败记 warning，尽量继续后续主流程。
        """
        ok1 = self.run_mall_filter_limited_special_toggle()
        if not ok1:
            logger.warning("限时特价切换未完成，仍继续新品优选等步骤")
            self.recover_mall_list_to_show_tab_bar()
        if not self.tap_new_product_prefer_tab():
            logger.warning("「新品优选」未点到，仍继续滑动")
        logger.info("新品优选首屏列表等待 5.0s（首屏数据渲染）")
        time.sleep(5.0)
        self.swipe_mall_main_list_down(5, settle_sec=5.0)
        self.tap_back_to_top_if_visible()
        if not self._is_mall_home_main_list_visible() or (
            not self._kingkong_hot_snacks_label_visible()
        ):
            logger.info(
                "新品优选长滑后仍不见 rv_content 或金刚区「%s」，追加手势回顶",
                SHOP_KINGKONG_HOT_SNACKS,
            )
            self.mall_list_gesture_scroll_to_top(8)
            time.sleep(0.5)
        return True

    def _tx_looks_like_mall_spec_chip(self, tx: str) -> bool:
        return self._spec.tx_looks_like_mall_spec_chip(tx)

    def _mall_spec_try_pick_one_chip(self, root, tag: str) -> bool:
        return self._spec.try_pick_one_chip(root, tag)

    def _mall_spec_popup_pick_and_confirm(self) -> bool:
        """多规格底部弹层；实现见 ``pages.shop_mall_spec_sheet.MallSpecSheet``。"""
        return self._spec.popup_pick_and_confirm()

    def _tap_mall_spec_sheet_confirm_button(self) -> bool:
        return self._spec.tap_confirm_button()

    def _is_mall_home_main_list_visible(self) -> bool:
        return self._first_displayed_by_pkg_id(SHOP_ID_RV_CONTENT) is not None

    def _is_mall_product_detail_visible(self) -> bool:
        if self._first_displayed_by_pkg_id(SHOP_ID_MALL_ADD_SHOP_CAR):
            return True
        return self._first_displayed_by_pkg_id(SHOP_ID_MALL_DETAIL_VIEWPAGER) is not None

    def _wait_substring_on_screen(self, sub: str, timeout: float = 3.5) -> bool:
        if not sub:
            return False
        safe = sub.replace('"', "").replace("'", "")[:40]
        end = time.time() + timeout
        while time.time() < end:
            try:
                xp = f'//*[contains(@text,"{safe}")]'
                for el in self.driver.find_elements(AppiumBy.XPATH, xp):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(0.28)
        return False

    def _kefu_native_markers_visible(self) -> bool:
        """Native 层可见文案/描述是否像客服页。"""
        for sub in SHOP_TEXT_KEFU_PAGE_MARKERS:
            safe = sub.replace('"', "").replace("'", "")[:36]
            try:
                for el in self.driver.find_elements(
                    AppiumBy.XPATH, f'//*[contains(@text,"{safe}")]'
                ):
                    try:
                        if el.is_displayed():
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        try:
            for el in self.driver.find_elements(
                AppiumBy.XPATH, '//*[contains(@content-desc,"客服")]'
            ):
                if el.is_displayed():
                    return True
        except Exception:
            pass
        return False

    def _kefu_page_via_webview_source(self) -> bool:
        """部分包客服为 H5，切 WEBVIEW 扫 ``page_source``。"""
        try:
            names = [
                c
                for c in self.driver.contexts
                if "WEBVIEW" in str(c).upper()
            ]
        except Exception:
            return False
        if not names:
            return False
        try:
            prev = self.driver.current_context
        except Exception:
            prev = "NATIVE_APP"
        hit = False
        for name in names:
            try:
                self.driver.switch_to.context(name)
                time.sleep(0.5)
                body = (self.driver.page_source or "")[:500_000]
                if any(
                    k in body
                    for k in (
                        "24小时",
                        "客服",
                        "在线咨询",
                        "人工客服",
                        "意见反馈",
                        "专属客服",
                    )
                ):
                    hit = True
                    break
            except Exception:
                continue
        try:
            self.driver.switch_to.context(prev)
        except Exception:
            pass
        return hit

    def _wait_kefu_destination(self, timeout: float = 10.0) -> bool:
        end = time.time() + timeout
        n = 0
        while time.time() < end:
            if self._kefu_native_markers_visible():
                return True
            n += 1
            if n % 2 == 0 and self._kefu_page_via_webview_source():
                return True
            time.sleep(0.4)
        return False

    def tap_first_mall_list_product_into_detail(self) -> bool:
        """
        主列表（``rv_content``）进商品详情：**点商品图/名称/价签/卡片左区**；
        排除 ``iv_add_cart``（加购按钮走加购流程，不进详情）。
        """
        return self._detail.tap_first_mall_list_product_into_detail()

    def mall_detail_tap_add_to_cart_with_spec(self) -> bool:
        """详情页点「加入购物车」；多规格则选规格 → 点数量+ → 完成/确定。"""
        return self._detail.mall_detail_tap_add_to_cart_with_spec()

    def mall_detail_tap_buy_now_price_gate(self) -> bool:
        """立即购买：售价≤400P 时不应进入提交订单类页面。"""
        return self._detail.mall_detail_tap_buy_now_price_gate()

    def run_mall_product_detail_deep_flow(self) -> bool:
        """
        商城主列表 → 商品详情 → 返回首页 → 再进详情
        → 加入购物车（多规格弹层：选规格 + 数量 + 完成）
        → 收藏（期望「收藏成功」）→ 客服（多文案 / WebView）→ 返回详情
        → 购物车 → 返回详情 → 立即购买（≤400P 不得进下单页）→ 返回商城首页。
        """
        return self._detail.run_mall_product_detail_deep_flow()

    def run_category_spec_add_verify_line_qty(
        self, *, random_pick: bool = False, log_prefix: str = "分类"
    ) -> bool:
        """
        分类商品列表：仅对信息栏含「选规格」的商品加购（``tv_add_cart_more`` / 文案）；
        ``random_pick=True`` 时在可见候选中随机选一行，否则取第一个。
        """
        return self._category.run_category_spec_add_verify_line_qty(
            random_pick=random_pick, log_prefix=log_prefix
        )

    def run_hot_snacks_category_spec_add_verify_line_qty(self) -> bool:
        """兼容：爆款零食分类页，取首个「选规格」。"""
        return self._category.run_category_spec_add_verify_line_qty(
            random_pick=False, log_prefix="爆款零食分类"
        )

    def run_shop_home_flow(self, **kwargs: Any) -> bool:
        """
        完整流程：商城 Tab
        → **日用百货**（金刚区弹层分类、选规格加购）→ 回首页
        → **限时特价 / 新品优选**（``run_mall_list_filters_scroll_and_back_top``：含长滑回顶）
        → **不再**重复「再切新品优选 + 长滑 + 首页 iv_add_cart」（与详情深度流里详情加购重复）
        → 主列表详情深度流 → 悬浮购物车 → Banner → 末次首页加购 → 角标 +1。

        实现见 ``flows.shop_home_flow``（阶段函数拆分，与 Page Object 解耦）。

        额外关键字参数透传给 ``flows.shop_home_flow.run_shop_home_flow``，例如
        ``skip_phases``、``on_phase_end``（阶段结束钩子，便于截图/上报）。
        """
        from flows.shop_home_flow import run_shop_home_flow as _run_flow

        return _run_flow(self, **kwargs)


def run_shop_home_from_driver(driver: WebDriver, **kwargs: Any) -> bool:
    """供脚本直接调用。"""
    return ShopHomePage(driver).run_shop_home_flow(**kwargs)
