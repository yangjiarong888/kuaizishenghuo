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
    def __init__(self, label, *, y=100, displayed=True, enabled=True):
        self.label = label
        self.location = {"y": y}
        self.displayed = displayed
        self.enabled = enabled
        self.clicks = 0

    def is_displayed(self):
        return self.displayed

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicks += 1


class FakeDriver:
    def __init__(self, *, package="com.bs.feifubao", elements=None):
        self.current_package = package
        self.elements = list(elements or [])
        self.back_calls = 0

    def get_window_size(self):
        return {"width": 1080, "height": 1920}

    def find_elements(self, _by, value):
        match = re.search(r'@text="([^"]+)"', value)
        label = match.group(1) if match else ""
        return [element for element in self.elements if element.label == label]

    def back(self):
        self.back_calls += 1


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
        return True


def test_navigation_stops_after_first_uncertain_transition():
    page = ScriptedProfilePage([True, False, True])
    targets = (
        ProfileTarget("account", "我的订单", ("我的订单",)),
        ProfileTarget("account", "优惠券", ("优惠券",)),
        ProfileTarget("account", "我的余额", ("我的余额",)),
    )

    assert page.run_navigation_smoke(targets=targets) is False
    assert page.opened == ["我的订单", "优惠券"]
