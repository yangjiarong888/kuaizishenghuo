"""商城多规格底部弹层：选 SKU、数量、确定/完成。"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.shop_locators import (
    SHOP_ID_BOTTOM_POPUP,
    SHOP_ID_CHOOSE_RECYCLER,
    SHOP_ID_CHOOSE_SCROLL,
    SHOP_ID_CHOOSE_SKU_CONTAINER,
    SHOP_ID_COUNT_ADD,
    SHOP_ID_DIALOG_CHOOSE_CONTAINER,
    SHOP_ID_DIALOG_COMPLETE,
    SHOP_TEXT_FINISH_SPEC,
)
from pages.shop_mall_context import ShopMallContext

logger = setup_logger(__name__)


class MallSpecSheet:
    """规格弹层交互，供 ``ShopHomePage`` 委托。"""

    def __init__(
        self,
        ctx: ShopMallContext,
        login_like_visible: Callable[[], bool],
    ) -> None:
        self._ctx = ctx
        self._login_like_visible = login_like_visible

    SPEC_GROUP_TITLES = (
        "规格",
        "颜色",
        "色号",
        "尺寸",
        "尺码",
        "容量",
        "口味",
        "味道",
        "款式",
        "型号",
        "净含量",
        "包装",
        "套餐",
        "属性",
        "类型",
    )
    NON_SPEC_EXACT = (
        "确定",
        SHOP_TEXT_FINISH_SPEC,
        "取消",
        "加入购物车",
        "立即购买",
        "数量",
        "库存",
        "选择",
        "已选",
        "+",
        "-",
        "＋",
        "－",
    )
    NON_SPEC_CONTAINS = (
        "优惠",
        "活动",
        "服务",
        "正品",
        "退换",
        "维修",
        "客服",
        "收藏",
        "购物车",
        "查看更多",
        "暂无优惠",
        "未选择",
    )

    def tx_looks_like_mall_spec_chip(self, tx: str) -> bool:
        if not tx or len(tx) > 44:
            return False
        t = tx.strip()
        ban_exact = (
            "确定",
            SHOP_TEXT_FINISH_SPEC,
            "取消",
            "加入购物车",
            "立即购买",
            "规格",
            "数量",
            "库存",
            "选择",
            "已选",
            "+",
            "-",
            "＋",
            "－",
        )
        if t in ban_exact:
            return False
        if self._fullmatch(r"\d{1,4}", t):
            return False
        low = t.lower()
        return bool(
            self._search(
                r"(pcs|pic|pc\b|box|箱|盒|袋|包|瓶|罐|条|/"
                r"|ml\b|\bmg\b|\bg\b|cm\b|mm\b|m\b|寸|码|号|色|款|"
                r"\d+\s*(瓶|罐|包|pcs|pic|箱|件|盒|条|cm|mm|m|寸|码|号))",
                low,
            )
        )

    @staticmethod
    def _search(pattern: str, text: str) -> bool:
        import re

        return re.search(pattern, text, re.I) is not None

    @staticmethod
    def _fullmatch(pattern: str, text: str) -> bool:
        import re

        return re.fullmatch(pattern, text) is not None

    def _sheet_root(self):
        for suffix in (
            SHOP_ID_DIALOG_CHOOSE_CONTAINER,
            SHOP_ID_BOTTOM_POPUP,
            SHOP_ID_CHOOSE_SCROLL,
            SHOP_ID_CHOOSE_RECYCLER,
            SHOP_ID_CHOOSE_SKU_CONTAINER,
        ):
            root = self._ctx.first_displayed_by_pkg_id(suffix)
            if root:
                return root
        return None

    @staticmethod
    def _bounds(el) -> Optional[Tuple[int, int, int, int]]:
        try:
            loc = el.location
            size = el.size
            x1 = int(loc["x"])
            y1 = int(loc["y"])
            return x1, y1, x1 + int(size["width"]), y1 + int(size["height"])
        except Exception:
            return None

    def _visible_textviews(self, root) -> List[Tuple[int, int, int, int, str, object]]:
        if not root:
            return []
        out: List[Tuple[int, int, int, int, str, object]] = []
        try:
            elements = root.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
        except Exception:
            return out
        for el in elements:
            try:
                if not el.is_displayed():
                    continue
                text = (el.text or "").strip()
                if not text:
                    continue
                bounds = self._bounds(el)
                if not bounds:
                    continue
                x1, y1, x2, y2 = bounds
                out.append((y1, x1, x2, y2, text, el))
            except Exception:
                continue
        out.sort(key=lambda item: (item[0], item[1]))
        return out

    def _is_spec_group_title(self, text: str) -> bool:
        t = (text or "").strip()
        return t in self.SPEC_GROUP_TITLES

    def _is_structural_spec_candidate(self, text: str, el) -> bool:
        t = (text or "").strip()
        if not t or len(t) > 60:
            return False
        if t in self.NON_SPEC_EXACT or self._is_spec_group_title(t):
            return False
        if any(token in t for token in self.NON_SPEC_CONTAINS):
            return False
        if any(token in t for token in ("₱", "￥", "¥", "PHP", "RMB")):
            return False
        if any(token in t for token in ("售罄", "无货", "库存不足", "不可选")):
            return False
        try:
            if (el.get_attribute("enabled") or "").lower() == "false":
                return False
        except Exception:
            pass
        return True

    def _click_structural_candidate(self, row, tag: str) -> bool:
        _, _, _, _, text, el = row
        try:
            self._ctx.nearest_clickable_ancestor(el).click()
            logger.info("已按元素结构选择规格项(%s): %s", tag, text[:40])
            time.sleep(0.45)
            return True
        except Exception:
            if self._ctx.try_click(el, f"结构规格项 {text[:24]}"):
                logger.info("已按元素结构选择规格项(%s 自身): %s", tag, text[:40])
                time.sleep(0.45)
                return True
        return False

    def pick_specs_by_structure(self) -> bool:
        """
        以弹层元素结构选规格：
        - 找规格组标题（规格/颜色/尺寸/款式等）
        - 在该标题到下一个规格组或「数量」之间，点击第一个可用选项
        - 文案只用于排除标题/按钮/数量，不用于判断业务规格类型
        """
        root = self._sheet_root()
        rows = self._visible_textviews(root)
        if not rows:
            return False

        quantity_y = min((r[0] for r in rows if r[4] == "数量"), default=None)
        confirm_y = min(
            (r[0] for r in rows if r[4] in ("确定", SHOP_TEXT_FINISH_SPEC, "立即购买", "加入购物车")),
            default=None,
        )
        hard_bottom = min(v for v in (quantity_y, confirm_y) if v is not None) if (
            quantity_y is not None or confirm_y is not None
        ) else self._ctx.window_size()[1]

        titles = [row for row in rows if self._is_spec_group_title(row[4]) and row[0] < hard_bottom]
        clicked = 0
        for idx, title in enumerate(titles):
            title_y, title_x, title_x2, _, title_text, _ = title
            next_title_y = titles[idx + 1][0] if idx + 1 < len(titles) else hard_bottom
            candidates = []
            for row in rows:
                y1, x1, _, _, text, el = row
                same_row_right = abs(y1 - title_y) <= 18 and x1 > title_x2
                below_title = title_y + 8 < y1 < next_title_y - 4
                if not (same_row_right or below_title):
                    continue
                if self._is_structural_spec_candidate(text, el):
                    candidates.append(row)
            candidates.sort(key=lambda item: (item[0], item[1]))
            if candidates and self._click_structural_candidate(candidates[0], title_text):
                clicked += 1

        if clicked:
            return True

        # 无明确标题时，选「已选/选择」之后、「数量/完成」之前的首个可点项。
        top = max((r[3] for r in rows if r[4] in ("已选", "选择")), default=0)
        candidates = [
            row
            for row in rows
            if top < row[0] < hard_bottom
            and self._is_structural_spec_candidate(row[4], row[5])
        ]
        candidates.sort(key=lambda item: (item[0], item[1]))
        if candidates:
            return self._click_structural_candidate(candidates[0], "fallback")
        return False

    def try_pick_one_chip(self, root, tag: str) -> bool:
        if not root:
            return False
        try:
            for tel in root.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.TextView"
            ):
                try:
                    if not tel.is_displayed():
                        continue
                    tx = (tel.text or "").strip()
                    if not self.tx_looks_like_mall_spec_chip(tx):
                        continue
                    self._ctx.nearest_clickable_ancestor(tel).click()
                    logger.info("已选规格项(%s): %s", tag, tx[:40])
                    time.sleep(0.45)
                    return True
                except Exception as ex:
                    logger.debug("try_pick_one_chip 跳过: %s", ex)
                    continue
        except Exception as ex:
            logger.debug("try_pick_one_chip 容器失败: %s", ex)
        return False

    def popup_pick_and_confirm(self) -> bool:
        end = time.time() + 14.0
        while time.time() < end:
            if self._login_like_visible():
                logger.error("选规格后进入登录页，请先登录")
                return False
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_DIALOG_COMPLETE):
                break
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_BOTTOM_POPUP):
                break
            if self._ctx.first_displayed_by_pkg_id(SHOP_ID_DIALOG_CHOOSE_CONTAINER):
                break
            time.sleep(0.35)
        picked = self.pick_specs_by_structure()
        sku_root = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SKU_CONTAINER)
        if not picked and self.try_pick_one_chip(sku_root, "choose_sku"):
            picked = True
        if not picked:
            rv = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_RECYCLER)
            if self.try_pick_one_chip(rv, "choose_recycler"):
                picked = True
        if not picked:
            sv = self._ctx.first_displayed_by_pkg_id(SHOP_ID_CHOOSE_SCROLL)
            self.try_pick_one_chip(sv, "choose_scroll")
        add_el = self._ctx.first_displayed_by_pkg_id(SHOP_ID_COUNT_ADD)
        if add_el:
            if self._ctx.try_click(add_el, "count_add"):
                logger.info("已点击规格弹层数量加（count_add）")
                time.sleep(0.45)
        if self.tap_confirm_button():
            return True
        logger.error("多规格弹层未点到「确定/完成」等主按钮")
        return False

    @staticmethod
    def _short_bottom_text(el, y_cut: int, *, max_len: int = 10) -> bool:
        try:
            if not el.is_displayed():
                return False
            if int(el.location.get("y", 0)) < y_cut:
                return False
            return len((el.text or "").strip()) <= max_len
        except Exception:
            return False

    def _click_confirm_candidate(self, el, desc: str, *, sleep_sec: float = 0.85) -> bool:
        try:
            self._ctx.nearest_clickable_ancestor(el).click()
            logger.info("已点击多规格弹层主按钮（%s）", desc)
            time.sleep(sleep_sec)
            return True
        except Exception:
            if self._ctx.try_click(el, desc):
                logger.info("已点击多规格弹层主按钮（%s 自身）", desc)
                time.sleep(sleep_sec)
                return True
        return False

    def _tap_confirm_by_dialog_complete_id(self) -> bool:
        for pkg in self._ctx.shop_packages_prioritized():
            rid = self._ctx.rid(pkg, SHOP_ID_DIALOG_COMPLETE)
            try:
                for el in self._ctx.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if not el.is_displayed():
                            continue
                        if self._click_confirm_candidate(el, f"dialog_complete / {pkg}"):
                            return True
                    except Exception as ex:
                        logger.debug("dialog_complete 候选跳过: %s", ex)
            except Exception as ex:
                logger.debug("dialog_complete id 扫描: %s", ex)
        return False

    def _tap_confirm_by_dialog_complete_xpath(self) -> bool:
        try:
            for el in self._ctx.driver.find_elements(
                AppiumBy.XPATH,
                '//*[contains(@resource-id,"dialog_complete")]',
            ):
                try:
                    if el.is_displayed() and self._click_confirm_candidate(
                        el, "resource-id 含 dialog_complete"
                    ):
                        return True
                except Exception:
                    continue
        except Exception as ex:
            logger.debug("dialog_complete XPath: %s", ex)
        return False

    def _tap_confirm_by_exact_text(self, y_cut: int) -> bool:
        for label in (SHOP_TEXT_FINISH_SPEC, "确定", "加入购物车", "立即购买"):
            try:
                for el in self._ctx.driver.find_elements(
                    AppiumBy.XPATH, f'//*[@text="{label}"]'
                ):
                    if self._short_bottom_text(el, y_cut) and self._click_confirm_candidate(
                        el, f"文案 {label}"
                    ):
                        return True
            except Exception as ex:
                logger.debug("规格弹层文案 %s: %s", label, ex)
        return False

    def _tap_confirm_by_contains_text(self, y_cut: int) -> bool:
        for sub, disp in (
            (SHOP_TEXT_FINISH_SPEC, "完成"),
            ("确定", "确定"),
            ("立即购买", "立即购买"),
        ):
            try:
                xp = f'//*[contains(@text,"{sub}")]'
                for el in self._ctx.driver.find_elements(AppiumBy.XPATH, xp):
                    if self._short_bottom_text(el, y_cut) and self._click_confirm_candidate(
                        el, f"contains 文案 {disp}"
                    ):
                        return True
            except Exception as ex:
                logger.debug("规格弹层 contains %s: %s", sub, ex)
        return False

    def _tap_confirm_by_button_text(self, y_cut: int) -> bool:
        try:
            for el in self._ctx.driver.find_elements(
                AppiumBy.XPATH,
                (
                    '//android.widget.Button['
                    'contains(@text,"完成") or contains(@text,"确定") or contains(@text,"立即购买")]'
                ),
            ):
                if self._short_bottom_text(el, y_cut) and self._ctx.try_click(
                    el, "Button 完成/确定"
                ):
                    logger.info("已点击多规格弹层主按钮（Button 完成/确定）")
                    time.sleep(0.85)
                    return True
        except Exception as ex:
            logger.debug("规格 Button: %s", ex)
        return False

    def _tap_confirm_by_uiautomator(self) -> bool:
        for label in (SHOP_TEXT_FINISH_SPEC, "确定", "立即购买"):
            try:
                self._ctx.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().text("{label}").clickable(true)',
                ).click()
                logger.info("已点击多规格弹层「%s」（UiAutomator）", label)
                time.sleep(0.85)
                return True
            except Exception as ex:
                logger.debug("规格 UiAutomator %s: %s", label, ex)
                continue
        return False

    def tap_confirm_button(self) -> bool:
        y_cut = int(self._ctx.window_size()[1] * 0.32)
        for strategy in (
            self._tap_confirm_by_dialog_complete_id,
            self._tap_confirm_by_dialog_complete_xpath,
            lambda: self._tap_confirm_by_exact_text(y_cut),
            lambda: self._tap_confirm_by_contains_text(y_cut),
            lambda: self._tap_confirm_by_button_text(y_cut),
            self._tap_confirm_by_uiautomator,
        ):
            if strategy():
                return True
        return False
