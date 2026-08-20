import re

from pages.my_profile_page import MyProfilePage, ProfileTarget


def test_default_targets_are_read_only_allow_list():
    labels = {target.label for target in MyProfilePage.default_targets()}

    assert labels == {
        "我的订单",
        "优惠券",
        "我的余额",
        "积分",
        "收藏清单",
        "我的地址",
    }


def test_sensitive_profile_mutation_apis_do_not_exist():
    forbidden = (
        "run_phone_change_flow",
        "run_payment_password_change_flow",
        "run_fingerprint_payment_flow",
        "run_account_cancellation_flow",
        "run_login_password_change_flow",
        "run_settings_state_actions",
    )

    assert all(not hasattr(MyProfilePage, name) for name in forbidden)


class FakeElement:
    def __init__(self, label, *, y=100, displayed=True, enabled=True, on_click=None):
        self.label = label
        self.location = {"y": y}
        self.displayed = displayed
        self.enabled = enabled
        self.on_click = on_click
        self.clicks = 0

    def is_displayed(self):
        return self.displayed

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicks += 1
        if self.on_click is not None:
            self.on_click()


class FakeDriver:
    def __init__(self, *, package="com.bs.feifubao", elements=None, on_back=None):
        self.current_package = package
        self.elements = list(elements or [])
        self.on_back = on_back
        self.back_calls = 0

    def get_window_size(self):
        return {"width": 1080, "height": 1920}

    def find_elements(self, _by, value):
        match = re.search(r'@text="([^"]+)"', value)
        label = match.group(1) if match else ""
        return [element for element in self.elements if element.label == label]

    def back(self):
        self.back_calls += 1
        if self.on_back is not None:
            self.on_back()


def test_open_my_tab_rejects_wrong_package_without_clicking():
    tab = FakeElement("我的", y=1700)
    page = MyProfilePage(FakeDriver(package="other.app", elements=[tab]))

    assert page.open_my_tab() is False
    assert tab.clicks == 0


def test_open_my_tab_rejects_duplicate_visible_targets():
    first = FakeElement("我的", y=1700)
    second = FakeElement("我的", y=1750)
    page = MyProfilePage(FakeDriver(elements=[first, second]))

    assert page.open_my_tab() is False
    assert first.clicks == second.clicks == 0


def test_open_my_tab_requires_a_read_only_page_marker_after_click():
    tab = FakeElement("我的", y=1700)
    marker = FakeElement("我的订单")
    page = MyProfilePage(FakeDriver(elements=[tab, marker]), wait_sec=0.01)

    assert page.open_my_tab() is True
    assert tab.clicks == 1


def test_open_my_tab_supports_known_alternate_app_package():
    tab = FakeElement("我的", y=1700)
    marker = FakeElement("我的订单")
    page = MyProfilePage(
        FakeDriver(package="com.ba.feifubao", elements=[tab, marker]),
        wait_sec=0.01,
    )

    assert page.open_my_tab() is True


def test_arbitrary_non_allowlisted_target_is_rejected_without_clicking():
    dangerous = FakeElement("申请注销账户")
    driver = FakeDriver(elements=[dangerous])
    page = MyProfilePage(driver, wait_sec=0)

    result = page.open_target(
        ProfileTarget("account", "申请注销账户", ("确认注销",))
    )

    assert result is False
    assert dangerous.clicks == 0


def test_target_marker_wait_fails_if_click_leaves_expected_package():
    driver = FakeDriver()
    target = MyProfilePage.default_targets()[0]
    entry = FakeElement(target.label, on_click=lambda: setattr(driver, "current_package", "other.app"))
    marker = FakeElement(target.marker_labels[0])
    driver.elements = [entry, marker]
    page = MyProfilePage(driver, wait_sec=0.01)

    assert page.open_target(target) is False
    assert entry.clicks == 1


def test_missing_or_duplicate_target_is_fail_closed():
    target = MyProfilePage.default_targets()[0]
    missing_page = MyProfilePage(FakeDriver(), wait_sec=0)
    first = FakeElement(target.label)
    second = FakeElement(target.label)
    duplicate_page = MyProfilePage(FakeDriver(elements=[first, second]), wait_sec=0)

    assert missing_page.open_target(target) is False
    assert duplicate_page.open_target(target) is False
    assert first.clicks == second.clicks == 0


def test_target_marker_timeout_is_fail_closed():
    target = MyProfilePage.default_targets()[0]
    entry = FakeElement(target.label)
    page = MyProfilePage(FakeDriver(elements=[entry]), wait_sec=0)

    assert page.open_target(target) is False
    assert entry.clicks == 1


class ScriptedProfilePage(MyProfilePage):
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.opened = []

    def open_my_tab(self):
        return True

    def open_target(self, target):
        self.opened.append(target.label)
        return next(self.outcomes)

    def return_to_my_page(self):
        return next(self.outcomes)


def test_navigation_stops_after_first_uncertain_transition():
    page = ScriptedProfilePage([True, True, False, True])
    targets = MyProfilePage.default_targets()[:3]

    assert page.run_navigation_smoke(targets=targets) is False
    assert page.opened == ["我的订单", "优惠券"]


def test_navigation_stops_when_real_back_leaves_expected_package():
    driver = FakeDriver()
    driver.on_back = lambda: setattr(driver, "current_package", "other.app")

    class BackLeavingPage(MyProfilePage):
        def __init__(self):
            super().__init__(driver, wait_sec=0)
            self.opened = []

        def open_my_tab(self):
            return True

        def open_target(self, target):
            self.opened.append(target.label)
            return True

    page = BackLeavingPage()

    assert page.run_navigation_smoke(targets=page.default_targets()[:2]) is False
    assert driver.back_calls == 1
    assert page.opened == ["我的订单"]
