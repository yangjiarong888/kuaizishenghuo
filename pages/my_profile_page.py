"""Fail-closed, read-only navigation for the app's “我的” area."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Sequence

from appium.webdriver.common.appiumby import AppiumBy

from commons.logger import setup_logger


logger = setup_logger(__name__)

APP_PACKAGES = frozenset(
    {
        "com.bs.feifubao",
        "com.ba.feifubao",
        "com.bx.feifubao",
        "com.hu.feifubao",
    }
)
_PROFILE_PAGE_MARKERS = (
    "我的订单",
    "优惠券",
    "我的余额",
    "积分",
    "收藏清单",
    "我的地址",
    "登录筷子生活",
)


@dataclass(frozen=True)
class ProfileTarget:
    section: str
    label: str
    marker_labels: tuple[str, ...]


class MyProfilePage:
    """Navigate only to allow-listed pages and never mutate account state."""

    def __init__(self, driver: object, wait_sec: float = 10.0):
        self.driver = driver
        self.wait_sec = max(0.0, float(wait_sec))

    @staticmethod
    def default_targets() -> tuple[ProfileTarget, ...]:
        return (
            ProfileTarget("account", "我的订单", ("全部", "待付款", "待收货")),
            ProfileTarget("account", "优惠券", ("可使用", "已使用", "已过期")),
            ProfileTarget("account", "我的余额", ("账户余额", "余额明细", "充值")),
            ProfileTarget("account", "积分", ("积分明细", "积分规则")),
            ProfileTarget("general", "收藏清单", ("收藏商品", "收藏店铺")),
            ProfileTarget("general", "我的地址", ("收货地址", "新增地址")),
        )

    @staticmethod
    def logged_out_targets() -> tuple[ProfileTarget, ...]:
        return (
            ProfileTarget("general", "设置", ("语言设置", "当前版本")),
            ProfileTarget("general", "我要反馈", ("意见反馈", "反馈内容", "问题描述")),
            ProfileTarget("general", "在线客服", ("客服中心", "联系客服", "请输入您的问题")),
            ProfileTarget("general", "商家入驻", ("入驻申请", "立即入驻", "商家信息")),
        )

    @classmethod
    def _approved_targets(cls) -> frozenset[ProfileTarget]:
        return frozenset((*cls.default_targets(), *cls.logged_out_targets()))

    def _app_package_is_expected(self) -> bool:
        try:
            return str(self.driver.current_package) in APP_PACKAGES
        except Exception:
            return False

    @staticmethod
    def _label_xpath(label: str) -> str:
        safe = label.replace('"', "")
        return f'//*[@text="{safe}" or @content-desc="{safe}"]'

    def _visible_enabled(self, element: object) -> bool:
        try:
            return bool(element.is_displayed()) and bool(element.is_enabled())
        except Exception:
            return False

    def _unique_label(self, label: str, *, bottom_only: bool = False):
        try:
            candidates = self.driver.find_elements(
                AppiumBy.XPATH,
                self._label_xpath(label),
            )
        except Exception:
            return None

        bottom_y = 0
        if bottom_only:
            try:
                bottom_y = int(self.driver.get_window_size()["height"] * 0.65)
            except Exception:
                return None

        visible = []
        for element in candidates:
            if not self._visible_enabled(element):
                continue
            if bottom_only:
                try:
                    if int(element.location.get("y", 0)) < bottom_y:
                        continue
                except Exception:
                    continue
            visible.append(element)
        return visible[0] if len(visible) == 1 else None

    def _wait_for_any_label(self, labels: Iterable[str]) -> bool:
        labels = tuple(labels)
        deadline = time.monotonic() + self.wait_sec
        while True:
            if not self._app_package_is_expected():
                return False
            if any(self._unique_label(label) is not None for label in labels):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

    def open_my_tab(self) -> bool:
        if not self._app_package_is_expected():
            return False
        tab = self._unique_label("我的", bottom_only=True)
        if tab is None:
            return False
        try:
            tab.click()
        except Exception:
            return False
        return self._wait_for_any_label(_PROFILE_PAGE_MARKERS)

    def open_target(self, target: ProfileTarget) -> bool:
        if target not in self._approved_targets():
            return False
        if not self._app_package_is_expected():
            return False
        element = self._unique_label(target.label)
        if element is None:
            return False
        try:
            element.click()
        except Exception:
            return False
        return self._wait_for_any_label(target.marker_labels)

    def return_to_my_page(self) -> bool:
        try:
            self.driver.back()
        except Exception:
            return False
        return self._wait_for_any_label(_PROFILE_PAGE_MARKERS)

    def run_navigation_smoke(
        self,
        *,
        targets: Sequence[ProfileTarget] | None = None,
    ) -> bool:
        selected = tuple(targets) if targets is not None else self.default_targets()
        if any(target not in self._approved_targets() for target in selected):
            return False
        if not self.open_my_tab():
            return False
        for target in selected:
            if not self.open_target(target):
                logger.error("个人中心只读入口未可靠打开: %s", target.label)
                return False
            if not self.return_to_my_page():
                logger.error("个人中心返回校验失败: %s", target.label)
                return False
        return True

    def run_logged_out_navigation_smoke(self) -> bool:
        return self.run_navigation_smoke(targets=self.logged_out_targets())
