from appium.webdriver.common.appiumby import AppiumBy

from workflows.login_workflow import LoginState, detect_login_state, ensure_logged_in
from workflows.result import WorkflowStatus


class VisibleElement:
    def is_displayed(self):
        return True


class FakeLoginDriver:
    def __init__(self, state):
        self.current_package = "com.bs.feifubao"
        self.state = state

    def find_elements(self, by, value):
        if self.state == "logged_in" and by == AppiumBy.ID and "ll_exchange_rate" in value:
            return [VisibleElement()]
        if self.state == "logged_out" and by == AppiumBy.XPATH and "立即登录" in value:
            return [VisibleElement()]
        return []


class FakeLoginPage:
    def __init__(self, state):
        self.driver = FakeLoginDriver(state)


def test_already_logged_in_never_calls_login_action():
    page = FakeLoginPage("logged_in")
    calls = []

    result = ensure_logged_in(page, login_action=lambda: calls.append(True))

    assert result.ok is True
    assert calls == []


def test_logged_out_without_explicit_action_does_not_attempt_login():
    page = FakeLoginPage("logged_out")

    result = ensure_logged_in(page)

    assert result.status is WorkflowStatus.LOGIN_REQUIRED


def test_logged_out_runs_only_supplied_login_action_and_rechecks_state():
    page = FakeLoginPage("logged_out")

    def login():
        page.driver.state = "logged_in"
        return True

    result = ensure_logged_in(page, login_action=login)

    assert result.ok is True


def test_probe_exception_returns_unknown_without_login_attempt():
    calls = []

    class BrokenPage:
        class Driver:
            current_package = "com.bs.feifubao"

            def find_elements(self, *_args):
                raise RuntimeError("driver unavailable")

        driver = Driver()

    result = ensure_logged_in(BrokenPage(), login_action=lambda: calls.append(True))

    assert result.status is WorkflowStatus.LOGIN_STATE_UNKNOWN
    assert calls == []


def test_ambiguous_screen_is_unknown_and_never_uses_legacy_boolean_probe():
    calls = []

    class AmbiguousPage(FakeLoginPage):
        def __init__(self):
            super().__init__("ambiguous")

        def check_login_status_smart(self):
            calls.append("legacy-probe")
            return False

    page = AmbiguousPage()
    result = ensure_logged_in(page, login_action=lambda: calls.append("login") or True)

    assert detect_login_state(page) is LoginState.UNKNOWN
    assert result.status is WorkflowStatus.LOGIN_STATE_UNKNOWN
    assert calls == []


def test_detector_can_report_explicit_tri_state():
    result = ensure_logged_in(
        object(),
        state_detector=lambda _: LoginState.UNKNOWN,
        login_action=lambda: True,
    )

    assert result.status is WorkflowStatus.LOGIN_STATE_UNKNOWN
