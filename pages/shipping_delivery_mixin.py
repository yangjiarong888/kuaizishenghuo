"""Delivery-slot selection safeguards for the shipping checkout."""

from datetime import date

from appium.webdriver.common.appiumby import AppiumBy

from .app_common import logger
from .shipping_types import earliest_future_label, parse_delivery_date


class ShippingDeliveryMixin:
    """Select and verify a delivery date that is strictly in the future."""

    _DELIVERY_OPENERS = ("预约配送", "配送时间", "选择上门时间", "选择配送时间")
    _DELIVERY_DISABLED_MARKERS = ("disabled", "不可用", "禁用", "已满", "灰色")

    def device_today(self) -> date:
        """Read the device clock without ever falling back to the host clock."""
        try:
            raw = str(self.driver.get_device_time())
            return date.fromisoformat(raw[:10])
        except Exception as exc:
            raise AssertionError("无法读取设备日期，禁止选择配送时间") from exc

    def select_earliest_future_delivery(self, today: date | None = None) -> date:
        """Choose the earliest enabled delivery slot after ``today`` and read it back."""
        base = today if today is not None else self.device_today()
        if not self._click_text(self._DELIVERY_OPENERS):
            raise AssertionError("提交订单页未打开配送时间选择器")

        elements = self._delivery_candidate_elements()
        labels = [self._element_blob(element) for element in elements]
        try:
            chosen_label, chosen_date = earliest_future_label(labels, base)
        except ValueError as exc:
            raise AssertionError("未找到严格晚于今天的可选配送日期") from exc

        chosen = next(
            (
                element
                for element in elements
                if self._element_blob(element) == chosen_label
                and self._element_enabled(element)
            ),
            None,
        )
        if chosen is None:
            raise AssertionError("未来配送日期选项不可点击")
        try:
            chosen.click()
        except Exception as exc:
            raise AssertionError("未来配送日期点击失败") from exc
        self._click_text(("确定", "确认"))
        self.verify_selected_delivery_date(chosen_date, base)
        logger.info("配送日期已选择 selected=%s today=%s", chosen_date, base)
        return chosen_date

    def verify_selected_delivery_date(self, selected: date, today: date) -> bool:
        """Fail closed unless checkout displays exactly the future date selected."""
        parsed = parse_delivery_date(self._checkout_delivery_text(), today)
        if parsed is None:
            raise AssertionError("提交订单页配送时间无法解析")
        if parsed <= today:
            raise AssertionError("配送日期必须严格晚于今天")
        if parsed != selected:
            raise AssertionError(
                f"配送日期回读不一致 selected={selected} actual={parsed}"
            )
        return True

    def _delivery_candidate_elements(self) -> list:
        """Return only displayed, enabled, clickable, non-disabled UI elements."""
        try:
            elements = self.driver.find_elements(AppiumBy.XPATH, "//*[@text or @content-desc]")
        except Exception as exc:
            logger.debug(
                "Shipping delivery candidate lookup failed error_type=%s",
                type(exc).__name__,
            )
            return []
        return [element for element in elements if self._element_enabled(element)]

    def _element_enabled(self, element) -> bool:
        try:
            if not element.is_displayed() or not element.is_enabled():
                return False
        except Exception:
            return False
        attributes = []
        for name in ("enabled", "clickable", "class", "style", "resource-id", "content-desc"):
            try:
                value = element.get_attribute(name)
                attributes.append("" if value is None else str(value).lower())
            except Exception:
                continue
        if any(value in {"false", "0", "no"} for value in attributes[:2]):
            return False
        return not any(
            marker in value
            for value in attributes
            for marker in self._DELIVERY_DISABLED_MARKERS
        )

    @staticmethod
    def _element_blob(element) -> str:
        values = []
        try:
            values.append(str(element.text or ""))
        except Exception:
            pass
        for name in ("text", "content-desc"):
            try:
                values.append(str(element.get_attribute(name) or ""))
            except Exception:
                pass
        return " ".join(dict.fromkeys(value.strip() for value in values if value.strip()))

    def _checkout_delivery_text(self) -> str:
        return self.page_blob()
