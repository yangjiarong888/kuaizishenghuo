"""Fail-closed COD rounding calculations and checkout selection helpers."""

from __future__ import annotations

import math
import html
import re
from dataclasses import dataclass
from typing import Any, Iterable

from appium.webdriver.common.appiumby import AppiumBy


@dataclass(frozen=True)
class RoundingOption:
    amount: int
    change: float


def compute_rounding_options(payable: float, limit: int = 3) -> list[RoundingOption]:
    """Return ascending preset COD rounding amounts strictly above ``payable``."""
    try:
        resolved = float(payable)
    except (TypeError, ValueError):
        return []
    if limit <= 0 or not math.isfinite(resolved) or resolved <= 0:
        return []
    if resolved.is_integer() and int(resolved) % 1000 == 0:
        return []

    if resolved >= 1000:
        first_thousand = (math.floor(resolved / 1000) + 1) * 1000
        candidates = [first_thousand + (1000 * index) for index in range(limit)]
    else:
        candidates = [(math.floor(resolved / 100) + 1) * 100]
        next_500 = (math.floor(resolved / 500) + 1) * 500
        if next_500 not in candidates:
            candidates.append(next_500)
        next_thousand = (math.floor(resolved / 1000) + 1) * 1000
        while len(candidates) < limit:
            if next_thousand not in candidates:
                candidates.append(next_thousand)
            next_thousand += 1000
    return [
        RoundingOption(amount=amount, change=round(amount - resolved, 2))
        for amount in candidates[:limit]
    ]


def parse_checkout_money(text: str) -> float | None:
    """Parse one money value only when its text identifies it as monetary."""
    if not text:
        return None
    normalized = html.unescape(str(text)).replace(",", "").strip()
    if not normalized:
        return None

    number = r"(?P<negative>-)?\s*(?P<number>\d+(?:\.\d{1,2})?)(?![\d.])"
    match = re.search(
        r"(?:应付|实付|支付金额|合计|总计|总额|总价|金额|费用)\s*[:：]?\s*"
        r"(?:￥|¥|₱|PHP|RMB|P)?\s*" + number,
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"(?:￥|¥|₱|PHP|RMB|P)\s*" + number,
            normalized,
            flags=re.IGNORECASE,
        )
    if not match:
        match = re.search(
            r"(?P<negative>-)?\s*(?P<number>\d+(?:\.\d{1,2})?)\s*元(?!\S)",
            normalized,
        )
    if not match:
        return None
    value = float(match.group("number"))
    return -value if match.group("negative") else value


class RoundingPaymentMixin:
    """Select and verify a COD rounding amount without coordinate guessing."""

    def _checkout_texts(self) -> list[str]:
        for name in ("page_texts", "_checkout_page_texts"):
            source = getattr(self, name, None)
            if not callable(source):
                continue
            try:
                return [str(text) for text in source() if str(text).strip()]
            except Exception:
                continue
        return []

    def checkout_payable_amount(self) -> float | None:
        texts = self._checkout_texts()
        final_values = self._checkout_values_for_labels(
            texts, ("应付", "实付", "支付金额")
        )
        if final_values:
            return self._unique_checkout_value(final_values, "结算页应付金额")
        total_values = self._checkout_values_for_labels(texts, ("合计", "总计"))
        if total_values:
            return self._unique_checkout_value(total_values, "结算页合计金额")
        return None

    @staticmethod
    def _checkout_values_for_labels(
        texts: Iterable[str], labels: tuple[str, ...]
    ) -> list[float]:
        values = []
        for text in texts:
            if not any(label in text for label in labels):
                continue
            value = parse_checkout_money(text)
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _unique_checkout_value(values: Iterable[float], description: str) -> float:
        unique_values = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)
        if len(unique_values) != 1:
            raise AssertionError(f"{description}冲突，无法安全选择取整金额")
        return unique_values[0]

    def _resolve_rounding_option(
        self, payable: float, custom_amount: float | None
    ) -> RoundingOption:
        if custom_amount is None:
            options = compute_rounding_options(payable)
            if not options:
                raise AssertionError("未找到严格高于应付金额的取整选项")
            return options[0]
        try:
            amount = float(custom_amount)
        except (TypeError, ValueError) as exc:
            raise AssertionError("自定义取整金额必须为整数") from exc
        if not math.isfinite(amount) or not amount.is_integer() or amount <= payable:
            raise AssertionError("自定义取整金额必须为严格大于应付金额的整数")
        rounded = int(amount)
        return RoundingOption(rounded, round(rounded - payable, 2))

    def assert_rounding_module_visible(self) -> None:
        texts = self._checkout_texts()
        if not any("取整" in text for text in texts):
            raise AssertionError("结算页未确认货到付款取整模块可见")

    @staticmethod
    def _visible_enabled(elements: Iterable[Any]) -> list[Any]:
        matches = []
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    matches.append(element)
            except Exception:
                continue
        return matches

    @staticmethod
    def _money_texts(value: float) -> tuple[str, ...]:
        rounded = round(value, 2)
        compact = f"{rounded:g}"
        fixed = f"{rounded:.2f}"
        grouped_compact = f"{rounded:,g}"
        grouped_fixed = f"{rounded:,.2f}"
        return tuple(dict.fromkeys((compact, fixed, grouped_compact, grouped_fixed)))

    @staticmethod
    def _xpath_contains_any(terms: Iterable[str]) -> str:
        return " or ".join(
            f'contains(@text,"{term}") or contains(@content-desc,"{term}")'
            for term in terms
        )

    def _rounding_option_selector(self, option: RoundingOption) -> str:
        amount_terms = (str(option.amount), f"{option.amount:,}")
        amount_predicate = self._xpath_contains_any(amount_terms)
        change_predicate = self._xpath_contains_any(self._money_texts(option.change))
        return (
            f"//*[ ({amount_predicate}) and ({change_predicate}) ]"
        )

    @staticmethod
    def _element_text(element: Any) -> str:
        values = []
        try:
            values.append(str(element.text))
        except Exception:
            pass
        for attribute in ("content-desc", "text"):
            try:
                values.append(str(element.get_attribute(attribute)))
            except Exception:
                continue
        return " ".join(value for value in values if value and value != "None")

    @classmethod
    def _element_represents_option(cls, element: Any, option: RoundingOption) -> bool:
        text = cls._element_text(element)
        if not text:
            return False
        amount_terms = (str(option.amount), f"{option.amount:,}")
        amount_matches = any(
            re.search(rf"(?<![\d.]){re.escape(term)}(?![\d.])", text)
            for term in amount_terms
        )
        change_matches = any(
            re.search(rf"(?<![\d.]){re.escape(term)}(?![\d.])", text)
            for term in cls._money_texts(option.change)
        )
        return amount_matches and change_matches

    @classmethod
    def _element_has_rounding_semantics(cls, element: Any) -> bool:
        text = cls._element_text(element).lower()
        if ("取整" in text or "rounding" in text) and any(
            marker in text for marker in ("找零", "找回", "余额", "change")
        ):
            return True
        try:
            resource_id = str(element.get_attribute("resource-id") or "").lower()
        except Exception:
            resource_id = ""
        return "rounding" in resource_id and any(
            marker in resource_id for marker in ("change", "option", "amount")
        )

    def _click_unique_rounding_option(self, option: RoundingOption) -> None:
        driver = getattr(self, "driver", None)
        if driver is None:
            raise AssertionError("取整选项未能唯一定位")
        try:
            elements = driver.find_elements(
                AppiumBy.XPATH, self._rounding_option_selector(option)
            )
        except Exception as exc:
            raise AssertionError("取整选项查询失败") from exc
        matches = [
            element
            for element in self._visible_enabled(elements)
            if self._element_represents_option(element, option)
            and self._element_has_rounding_semantics(element)
        ]
        if len(matches) != 1:
            raise AssertionError("取整选项必须唯一且可用")
        target = matches[0]
        try:
            target.click()
            return
        except Exception:
            pass
        coordinate_click = getattr(self, "_coord_tap_or_click", None)
        if callable(coordinate_click) and coordinate_click(target, "已选择取整金额"):
            return
        raise AssertionError("取整选项点击失败")

    def _rounding_option_selected(self, option: RoundingOption) -> bool:
        driver = getattr(self, "driver", None)
        if driver is None:
            return False
        try:
            elements = driver.find_elements(
                AppiumBy.XPATH, self._rounding_option_selector(option)
            )
        except Exception:
            return False
        matches = [
            element
            for element in self._visible_enabled(elements)
            if self._element_represents_option(element, option)
            and self._element_has_rounding_semantics(element)
        ]
        if len(matches) != 1:
            return False
        target = matches[0]
        try:
            if target.is_selected():
                return True
        except Exception:
            pass
        for attribute in ("selected", "checked", "aria-selected", "aria-checked"):
            try:
                if str(target.get_attribute(attribute)).lower() == "true":
                    return True
            except Exception:
                continue
        return False

    def select_checkout_rounding_payment(
        self,
        *,
        payable: float | None = None,
        custom_amount: float | None = None,
    ) -> RoundingOption:
        resolved = payable if payable is not None else self.checkout_payable_amount()
        if resolved is None:
            raise AssertionError("无法确认取整前应付金额")
        try:
            resolved = float(resolved)
        except (TypeError, ValueError) as exc:
            raise AssertionError("无法确认取整前应付金额") from exc
        if not math.isfinite(resolved) or resolved <= 0:
            raise AssertionError("无法确认取整前应付金额")
        option = self._resolve_rounding_option(resolved, custom_amount)
        self.assert_rounding_module_visible()
        self._click_unique_rounding_option(option)
        if not self._rounding_option_selected(option):
            raise AssertionError("取整金额或找零回读不一致")
        return option
