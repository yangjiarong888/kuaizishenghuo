"""商城自动化共享能力：窗口、包名顺序、按 id 查找、点击与隐式等待。"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable, List, Optional, Tuple, TypeVar

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver

from commons.logger import setup_logger
from pages.shop_locators import SHOP_PACKAGES

logger = setup_logger(__name__)

T = TypeVar("T")


class ShopMallContext:
    """抽离 ``ShopHomePage`` 中与「页面无关」的 driver 工具，便于拆模块与单测。"""

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def window_size(self) -> Tuple[int, int]:
        try:
            s = self.driver.get_window_size()
            return int(s["width"]), int(s["height"])
        except Exception:
            return 1080, 2400

    def nearest_clickable_ancestor(self, el, max_hops: int = 8):
        cur = el
        for _ in range(max_hops):
            try:
                if (cur.get_attribute("clickable") or "").lower() == "true":
                    return cur
                cur = cur.find_element(AppiumBy.XPATH, "..")
            except Exception:
                break
        return el

    def rid(self, pkg: str, suffix: str) -> str:
        return f"{pkg}:id/{suffix}"

    def shop_packages_prioritized(self) -> Tuple[str, ...]:
        cur = (getattr(self.driver, "current_package", None) or "").strip()
        if cur and cur in SHOP_PACKAGES:
            return (cur,) + tuple(p for p in SHOP_PACKAGES if p != cur)
        try:
            caps = getattr(self.driver, "capabilities", None) or {}
            app = (
                str(caps.get("appium:appPackage") or caps.get("appPackage") or "")
            ).strip()
            if app and app in SHOP_PACKAGES:
                return (app,) + tuple(p for p in SHOP_PACKAGES if p != app)
        except Exception:
            pass
        return SHOP_PACKAGES

    def first_displayed_by_pkg_id(self, suffix: str):
        for pkg in self.shop_packages_prioritized():
            rid = self.rid(pkg, suffix)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if el.is_displayed():
                            return el
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def all_displayed_by_pkg_id(self, suffix: str) -> List:
        out: List = []
        for pkg in self.shop_packages_prioritized():
            rid = self.rid(pkg, suffix)
            try:
                for el in self.driver.find_elements(AppiumBy.ID, rid):
                    try:
                        if el.is_displayed():
                            out.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return out

    @contextmanager
    def zero_implicit_wait(self):
        restore = 1.0
        try:
            iw = self.driver.timeouts.implicit_wait
            if hasattr(iw, "total_seconds"):
                restore = float(iw.total_seconds())
            else:
                v = float(iw)
                restore = v / 1000.0 if v >= 500 else v
        except Exception:
            restore = 1.0
        try:
            self.driver.implicitly_wait(0)
        except Exception:
            pass
        try:
            yield
        finally:
            try:
                self.driver.implicitly_wait(restore if restore >= 0 else 1.0)
            except Exception:
                try:
                    self.driver.implicitly_wait(1)
                except Exception:
                    pass

    def try_click(self, el, desc: str = "element") -> bool:
        try:
            el.click()
            return True
        except Exception as ex:
            logger.debug("try_click 失败 %s: %s", desc, ex)
            return False

    def poll_value(
        self,
        read_fn: Callable[[], Optional[T]],
        *,
        until: Callable[[Optional[T]], bool],
        timeout_sec: float = 12.0,
        step_sec: float = 0.35,
    ) -> Optional[T]:
        """轮询 ``read_fn`` 直到 ``until(value)`` 为真或超时。"""
        end = time.time() + timeout_sec
        last: Optional[T] = None
        while time.time() < end:
            last = read_fn()
            if until(last):
                return last
            time.sleep(step_sec)
        return last
