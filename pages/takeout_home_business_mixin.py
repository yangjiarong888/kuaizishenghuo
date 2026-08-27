"""Read-only and reversible business coverage for the takeout home page."""

from __future__ import annotations

import time
from typing import Optional, Sequence

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger
from pages.business_search_spec import SearchProductSummary
from pages.takeout_locators import (
    TAKEOUT_CONGEE_CATEGORY_LABEL,
    TAKEOUT_DISCOUNT_LABEL,
    TAKEOUT_HOME_CART_LABELS,
    TAKEOUT_HOME_TOP_LABELS,
    TAKEOUT_SERVICE_LABELS,
    _PACKAGES,
)


logger = setup_logger(__name__)


class TakeoutHomeBusinessMixin:
    """Host supplies ``driver``, takeout navigation, and merchant-list waits."""

    _HOME_EXCLUDED_LABELS = {
        "外卖",
        "首页",
        "商城",
        "我的",
        TAKEOUT_DISCOUNT_LABEL,
        TAKEOUT_CONGEE_CATEGORY_LABEL,
    }

    def _takeout_source(self) -> str:
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _takeout_click_label(
        self,
        labels: Sequence[str],
        *,
        exact: bool = False,
        y_min_ratio: float = 0.0,
        y_max_ratio: float = 1.0,
    ) -> bool:
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
        except Exception:
            height = 1920
        for raw in labels:
            safe = raw.replace('"', "").replace("'", "")[:48]
            xpath = (
                f'//*[@text="{safe}" or @content-desc="{safe}"]'
                if exact
                else f'//*[contains(@text,"{safe}") or contains(@content-desc,"{safe}")]'
            )
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    y = int(element.location.get("y", 0))
                    if not int(height * y_min_ratio) <= y <= int(
                        height * y_max_ratio
                    ):
                        continue
                    target = self._nearest_clickable_ancestor(element)
                    target.click()
                    time.sleep(0.6)
                    return True
                except Exception:
                    continue
        return False

    def _takeout_merchant_snapshot(self) -> tuple[str, ...]:
        values: set[str] = set()
        for pkg in _PACKAGES:
            for suffix in ("tv_merchant_name", "tv_shop_name"):
                try:
                    elements = self.driver.find_elements(
                        AppiumBy.ID, f"{pkg}:id/{suffix}"
                    )
                except Exception:
                    elements = []
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        value = (element.text or "").strip()
                        if value and value not in self._HOME_EXCLUDED_LABELS:
                            values.add(value)
                    except Exception:
                        continue
        return tuple(sorted(values))

    def _takeout_swipe_next_page(self) -> bool:
        try:
            self._swipe_merchant_list_once()
            return True
        except Exception:
            return False

    def browse_takeout_merchant_pages(self, min_pages: int = 3):
        if min_pages < 1 or not self.ensure_takeout_tab():
            return False
        snapshots: list[tuple[str, ...]] = []
        attempts = max(min_pages * 3, min_pages)
        for _ in range(attempts):
            snapshot = self._takeout_merchant_snapshot()
            if snapshot and snapshot not in snapshots:
                snapshots.append(snapshot)
                logger.info("外卖首页分页 %s merchants=%s", len(snapshots), snapshot)
                if len(snapshots) >= min_pages:
                    return snapshots
            if not self._takeout_swipe_next_page():
                break
        return False

    def _takeout_cart_page_visible(self) -> bool:
        source = self._takeout_source()
        return "购物车" in source and any(
            marker in source for marker in ("去结算", "清空购物车", "购物车为空", "结算")
        )

    def open_home_floating_cart_and_return(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_HOME_CART_LABELS, y_min_ratio=0.12, y_max_ratio=0.88
        ):
            return False
        if not self._takeout_cart_page_visible():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))

    def _takeout_category_grid_visible(self) -> bool:
        return TAKEOUT_CONGEE_CATEGORY_LABEL in self._takeout_source()

    def return_takeout_list_to_top(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_HOME_TOP_LABELS, y_min_ratio=0.18, y_max_ratio=0.90
        ):
            return False
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            if self._takeout_category_grid_visible():
                return True
            time.sleep(0.25)
        return False

    def _takeout_filter_count(self) -> Optional[int]:
        source = self._takeout_source()
        for value in range(1, 10):
            if f'content-desc="{value}"' in source or f'text="{value}"' in source:
                return value
        return 0 if TAKEOUT_DISCOUNT_LABEL in source else None

    def _takeout_discount_results_visible(self) -> bool:
        source = self._takeout_source()
        return any(marker in source for marker in ("满减", "满₱", "减₱"))

    def verify_discount_filter_cycle(self) -> bool:
        if not self._takeout_click_label((TAKEOUT_DISCOUNT_LABEL,), exact=True):
            return False
        if self._takeout_filter_count() != 1:
            return False
        if not self._takeout_discount_results_visible():
            return False
        if not self._takeout_click_label((TAKEOUT_DISCOUNT_LABEL,), exact=True):
            return False
        return self._takeout_filter_count() in (0, None)

    def _takeout_category_results_visible(self) -> bool:
        source = self._takeout_source()
        return TAKEOUT_CONGEE_CATEGORY_LABEL in source and any(
            marker in source for marker in ("rv_merchant", "tv_merchant_name", "商家")
        )

    def open_congee_category_and_return(self) -> bool:
        if not self._takeout_click_label(
            (TAKEOUT_CONGEE_CATEGORY_LABEL,), exact=True, y_max_ratio=0.58
        ):
            return False
        if not self._takeout_category_results_visible():
            return False
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))

    def _takeout_im_conversation_visible(self) -> bool:
        source = self._takeout_source()
        return "24小时客服" in source and any(
            marker in source for marker in ("输入消息", "表情", "相册", "图片")
        )

    def open_takeout_home_service_im(self) -> bool:
        if not self._takeout_click_label(
            TAKEOUT_SERVICE_LABELS, y_max_ratio=0.28
        ):
            return False
        return self._takeout_im_conversation_visible()

    # External takeout-home search support. Merchant search has its own entry
    # and intentionally does not use the suggestion fallback.
    def open_takeout_home_search(self) -> bool:
        if not self.ensure_takeout_tab():
            return False
        return self._takeout_click_label(
            ("搜索商家或商品", "搜索商品", "搜索"), y_max_ratio=0.28
        ) and self._takeout_search_input() is not None

    def _takeout_visible_text_nodes(self):
        """Return visible text/description nodes with stable screen geometry."""
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH,
                '//android.widget.TextView | //*[@content-desc!=""]',
            )
        except Exception:
            elements = []
        nodes = []
        seen = set()
        for element in elements:
            try:
                if not element.is_displayed() or not element.is_enabled():
                    continue
                text = (
                    (element.text or "").strip()
                    or (element.get_attribute("content-desc") or "").strip()
                )
                rect = element.rect
                key = (
                    text,
                    int(rect.get("x", 0)),
                    int(rect.get("y", 0)),
                    int(rect.get("width", 0)),
                    int(rect.get("height", 0)),
                )
                if not text or key in seen:
                    continue
                seen.add(key)
                nodes.append((*key, element))
            except Exception:
                continue
        return sorted(nodes, key=lambda node: (node[2], node[1]))

    def _takeout_search_landing_visible(self) -> bool:
        source = self._takeout_source()
        if self._takeout_search_input() is None:
            return False
        return any(
            marker in source
            for marker in (
                ">Hot<",
                'text="Hot"',
                "热搜",
                "热门搜索",
                "历史搜索",
                ">History<",
                'text="History"',
                "榜单",
                "推荐",
            )
        )

    @staticmethod
    def _takeout_node_text_is_section_title(text: str) -> bool:
        normalized = text.strip().lower()
        return (
            normalized in ("hot", "history")
            or "历史搜索" in text
            or "热门搜索" in text
            or "热搜榜" in text
            or "推荐" in text
            or text.endswith("榜单")
        )

    def _takeout_click_text_node(self, node, desc: str) -> bool:
        text, _x, _y, _width, _height, element = node
        try:
            self._nearest_clickable_ancestor(element).click()
            logger.info("%s：%s", desc, text)
            time.sleep(0.7)
            return True
        except Exception as exc:
            logger.warning("%s点击失败 text=%s error=%s", desc, text, exc)
            return False

    def _takeout_configured_destination_kind(self) -> Optional[str]:
        if self._takeout_search_landing_visible():
            return None
        source = self._takeout_source()
        try:
            inside_shop = bool(self._looks_inside_takeout_shop())
        except (AttributeError, TypeError):
            inside_shop = False
        if inside_shop or any(
            marker in source
            for marker in (
                "店内招牌",
                "商家主页",
                "联系商家",
                "收藏",
                "起送",
                "配送费",
                "选规格",
                "加入购物车",
                "shop_detail",
                "tv_shop_name",
            )
        ):
            return "merchant"
        if any(
            marker in source
            for marker in (
                "活动详情",
                "活动规则",
                "活动商品",
                "优惠活动",
                "activity_detail",
                "activity_goods",
            )
        ):
            return "activity"
        if any(
            marker in source
            for marker in (
                "vp_search_result",
                "rv_goods",
                "rv_merchant",
                "商品结果",
                "商家结果",
                "搜索结果",
                "综合排序",
            )
        ):
            return "search_results"
        return None

    def _wait_takeout_configured_destination(
        self, *, merchant_only: bool = False, timeout: float = 7.0
    ) -> Optional[str]:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            kind = self._takeout_configured_destination_kind()
            if kind and (not merchant_only or kind == "merchant"):
                return kind
            time.sleep(0.25)
        return None

    def _return_to_takeout_search_landing(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        end = time.monotonic() + 6.0
        while time.monotonic() < end:
            if self._takeout_search_landing_visible():
                return True
            time.sleep(0.25)
        return False

    def _takeout_hot_search_candidates(self):
        nodes = self._takeout_visible_text_nodes()
        hot_nodes = [
            node
            for node in nodes
            if node[0].strip().lower() == "hot" or node[0] in ("热搜", "热门搜索")
        ]
        if not hot_nodes:
            return []
        hot_bottom = min(node[2] + node[4] for node in hot_nodes)
        section_y = [
            node[2]
            for node in nodes
            if node[2] > hot_bottom
            and self._takeout_node_text_is_section_title(node[0])
        ]
        lower_bound = min(section_y) if section_y else None
        excluded = {"搜索", "Search", "取消", "Hot", "热搜", "热门搜索"}
        return [
            node
            for node in nodes
            if node[2] > hot_bottom
            and (lower_bound is None or node[2] < lower_bound)
            and node[0] not in excluded
            and not self._takeout_node_text_is_section_title(node[0])
            and "销量" not in node[0]
        ]

    def _open_takeout_hot_search_destination_and_return(self) -> bool:
        candidates = self._takeout_hot_search_candidates()
        if not candidates:
            logger.error("外卖搜索首页未找到可点击热搜词")
            return False
        target = candidates[0]
        if not self._takeout_click_text_node(target, "外卖热搜词"):
            return False
        kind = self._wait_takeout_configured_destination()
        if not kind:
            logger.error("外卖热搜词未进入商家主页、活动页或搜索结果页")
            return False
        logger.info("外卖热搜词落地类型=%s", kind)
        return self._return_to_takeout_search_landing()

    def _takeout_ranking_titles(self):
        try:
            height = int(self.driver.get_window_size().get("height", 1920))
        except Exception:
            height = 1920
        return [
            node
            for node in self._takeout_visible_text_nodes()
            if node[2] >= int(height * 0.30)
            and ("榜" in node[0] or "推荐" in node[0])
            and "人气大榜" not in node[0]
        ]

    def _takeout_ranking_snapshot(self) -> tuple[str, ...]:
        titles = self._takeout_ranking_titles()
        if not titles:
            return ()
        top = min(node[2] for node in titles)
        return tuple(
            dict.fromkeys(
                node[0]
                for node in self._takeout_visible_text_nodes()
                if node[2] >= top and node[0] not in ("销量",)
            )
        )

    def _takeout_first_ranking_merchant_node(self):
        titles = sorted(self._takeout_ranking_titles(), key=lambda node: node[1])
        if not titles:
            return None
        title = titles[0]
        left = max(0, title[1] - 16)
        right = titles[1][1] if len(titles) > 1 else left + max(title[3] * 3, 260)
        title_bottom = title[2] + title[4]
        excluded_fragments = ("销量", "榜单", "推荐", "搜索", "Hot", "History")
        candidates = [
            node
            for node in self._takeout_visible_text_nodes()
            if title_bottom < node[2]
            and left <= node[1] + max(node[3] // 2, 1) < right
            and not any(fragment in node[0] for fragment in excluded_fragments)
            and not node[0].strip().isdigit()
        ]
        return candidates[0] if candidates else None

    def _open_takeout_ranking_merchant_and_return(self) -> bool:
        target = self._takeout_first_ranking_merchant_node()
        if target is None:
            logger.error("外卖搜索首页未找到榜单商家")
            return False
        if not self._takeout_click_text_node(target, "外卖榜单商家"):
            return False
        if self._wait_takeout_configured_destination(merchant_only=True) != "merchant":
            logger.error("外卖榜单条目未进入商家主页")
            return False
        return self._return_to_takeout_search_landing()

    def _swipe_takeout_rankings_left_and_open_merchant(self) -> bool:
        before = self._takeout_ranking_snapshot()
        if not before:
            logger.error("外卖搜索首页没有可横滑榜单")
            return False
        try:
            size = self.driver.get_window_size()
            width = int(size.get("width", 1080))
            height = int(size.get("height", 1920))
            self.driver.execute_script(
                "mobile: swipeGesture",
                {
                    "left": int(width * 0.08),
                    "top": int(height * 0.34),
                    "width": int(width * 0.84),
                    "height": int(height * 0.52),
                    "direction": "left",
                    "percent": 0.78,
                },
            )
        except Exception as exc:
            logger.error("外卖榜单左滑失败：%s", exc)
            return False
        end = time.monotonic() + 5.0
        after = before
        while time.monotonic() < end:
            after = self._takeout_ranking_snapshot()
            if after and after != before:
                break
            time.sleep(0.25)
        if not after or after == before:
            logger.error("外卖榜单左滑后内容未变化")
            return False
        logger.info("外卖榜单左滑成功 before=%s after=%s", before, after)
        return self._open_takeout_ranking_merchant_and_return()

    def _takeout_search_history_present(self) -> bool:
        source = self._takeout_source()
        return any(
            marker in source
            for marker in (
                "历史搜索",
                'text="History"',
                ">History<",
            )
        )

    def _takeout_history_candidates(self):
        nodes = self._takeout_visible_text_nodes()
        titles = [
            node
            for node in nodes
            if node[0].strip().lower() == "history" or "历史搜索" in node[0]
        ]
        if not titles:
            return []
        title_bottom = min(node[2] + node[4] for node in titles)
        next_sections = [
            node[2]
            for node in nodes
            if node[2] > title_bottom
            and self._takeout_node_text_is_section_title(node[0])
        ]
        lower_bound = min(next_sections) if next_sections else None
        return [
            node
            for node in nodes
            if node[2] > title_bottom
            and (lower_bound is None or node[2] < lower_bound)
            and not self._takeout_node_text_is_section_title(node[0])
            and node[0] not in ("清空", "删除", "搜索", "Search")
        ]

    def _open_takeout_history_result_and_return(self) -> bool:
        candidates = self._takeout_history_candidates()
        if not candidates:
            logger.error("检测到历史搜索区域，但未找到历史搜索词")
            return False
        target = candidates[0]
        keyword = target[0]
        if not self._takeout_click_text_node(target, "外卖历史搜索词"):
            return False
        if not self.takeout_search_results_visible(keyword, timeout=7.0):
            logger.error("历史搜索词未进入对应搜索结果 keyword=%s", keyword)
            return False
        return self._return_to_takeout_search_landing()

    def browse_takeout_search_landing_business(self) -> bool:
        """Validate dynamic hot words, ranking cards, and optional history."""
        if not self._takeout_search_landing_visible():
            logger.error("外卖搜索首页未加载 Hot/榜单区域")
            return False
        for action in (
            self._open_takeout_hot_search_destination_and_return,
            self._open_takeout_ranking_merchant_and_return,
            self._swipe_takeout_rankings_left_and_open_merchant,
        ):
            if not action():
                return False
        if not self._takeout_search_history_present():
            logger.info("外卖搜索首页暂无历史搜索数据，按业务规则跳过")
            return True
        return self._open_takeout_history_result_and_return()

    def _takeout_search_input(self):
        for suffix in ("et_search", "edit_search", "search_edit", "input_search"):
            for pkg in _PACKAGES:
                try:
                    elements = self.driver.find_elements(
                        AppiumBy.ID, f"{pkg}:id/{suffix}"
                    )
                except Exception:
                    elements = []
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            return element
                    except Exception:
                        continue
        try:
            return next(
                (
                    el
                    for el in self.driver.find_elements(
                        AppiumBy.CLASS_NAME, "android.widget.EditText"
                    )
                    if el.is_displayed() and el.is_enabled()
                ),
                None,
            )
        except Exception:
            return None

    def type_takeout_search_keyword(self, keyword: str) -> bool:
        edit = self._takeout_search_input()
        if not edit:
            return False
        try:
            edit.click()
            edit.clear()
            edit.send_keys(keyword)
        except Exception:
            return False
        end = time.monotonic() + 3.0
        while time.monotonic() < end:
            try:
                if (edit.text or "").strip() == keyword:
                    return True
            except Exception:
                pass
            if keyword in self._takeout_source():
                return True
            time.sleep(0.2)
        return False

    def submit_takeout_search(self) -> bool:
        for label in ("搜索", "确定"):
            if self._takeout_click_label((label,), exact=True, y_max_ratio=0.28):
                return True
        try:
            self.driver.press_keycode(66)
            return True
        except Exception:
            return False

    def takeout_search_results_visible(
        self, keyword: str, timeout: float = 8.0
    ) -> bool:
        markers = (
            "vp_search_result",
            "rv_goods",
            "tv_good_name",
            "goods_name",
            "product_name",
            "商品结果",
        )
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            source = self._takeout_source()
            suggestions_only = "rv_search" in source and not any(
                marker in source for marker in markers
            )
            if keyword in source and not suggestions_only and any(
                marker in source for marker in markers
            ):
                return True
            time.sleep(0.25)
        return False

    def click_takeout_search_suggestion(self, keyword: str) -> bool:
        return self._takeout_click_label(
            (keyword,), y_min_ratio=0.08, y_max_ratio=0.88
        )

    def prefer_takeout_goods_results(self) -> bool:
        self._takeout_click_label(
            ("商品",), exact=True, y_min_ratio=0.08, y_max_ratio=0.45
        )
        return True

    def open_first_takeout_search_goods(self) -> bool:
        xpaths = (
            '//*[contains(@resource-id,"tv_good_name")]',
            '//*[contains(@resource-id,"goods_name") or contains(@resource-id,"product_name")]',
            '//*[@clickable="true" and contains(@content-desc,"₱")]',
        )
        for xpath in xpaths:
            try:
                elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
            except Exception:
                elements = []
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    blob = " ".join(
                        str(element.get_attribute(name) or "")
                        for name in ("text", "content-desc", "resource-id")
                    )
                    if any(word in blob for word in ("加购", "加入购物车", "iv_add")):
                        continue
                    self._nearest_clickable_ancestor(element).click()
                    time.sleep(0.8)
                    return True
                except Exception:
                    continue
        return False

    def read_takeout_goods_summary(
        self, keyword: str
    ) -> Optional[SearchProductSummary]:
        values: list[str] = []
        try:
            elements = self.driver.find_elements(
                AppiumBy.XPATH,
                '//android.widget.TextView | //*[@content-desc!=""]',
            )
        except Exception:
            elements = []
        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                value = (
                    (element.text or "").strip()
                    or (element.get_attribute("content-desc") or "").strip()
                )
                if value and value not in values:
                    values.append(value)
            except Exception:
                continue
        excluded = {"加入购物车", "立即购买", "客服", "分享", "购物车"}
        name = next(
            (value for value in values if value not in excluded and "₱" not in value),
            "",
        )
        price = next((value for value in values if "₱" in value), "")
        specification = next(
            (
                value
                for value in values
                if value not in excluded
                and value not in (name, price)
                and any(ch.isdigit() for ch in value)
                and "₱" not in value
            ),
            "",
        )
        return (
            SearchProductSummary(keyword, name, price, specification)
            if name
            else None
        )

    def return_from_takeout_search_goods(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return self._takeout_search_input() is not None

    def finish_takeout_home_search(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return bool(self.wait_merchant_list_present(timeout=6.0))
