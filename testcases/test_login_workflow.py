from workflows.login_workflow import LoginState, ensure_logged_in
from workflows.result import WorkflowStatus


class FakeLoginPage:
    def __init__(self, logged_in=False):
        self.logged_in = logged_in
        self.probe_calls = 0

    def check_login_status_smart(self):
        self.probe_calls += 1
        return self.logged_in


def test_already_logged_in_never_calls_login_action():
    page = FakeLoginPage(logged_in=True)
    calls = []

    result = ensure_logged_in(page, login_action=lambda: calls.append(True))

    assert result.ok is True
    assert calls == []


def test_logged_out_without_explicit_action_does_not_attempt_login():
    page = FakeLoginPage(logged_in=False)

    result = ensure_logged_in(page)

    assert result.status is WorkflowStatus.LOGIN_REQUIRED
    assert page.probe_calls == 1


def test_logged_out_runs_only_supplied_login_action_and_rechecks_state():
    page = FakeLoginPage(logged_in=False)

    def login():
        page.logged_in = True
        return True

    result = ensure_logged_in(page, login_action=login)

    assert result.ok is True
    assert page.probe_calls == 2


def test_probe_exception_returns_unknown_without_login_attempt():
    calls = []

    class BrokenPage:
        def check_login_status_smart(self):
            raise RuntimeError("driver unavailable")

    result = ensure_logged_in(BrokenPage(), login_action=lambda: calls.append(True))

    assert result.status is WorkflowStatus.LOGIN_STATE_UNKNOWN
    assert calls == []


def test_detector_can_report_explicit_tri_state():
    result = ensure_logged_in(
        object(),
        state_detector=lambda _: LoginState.UNKNOWN,
        login_action=lambda: True,
    )

    assert result.status is WorkflowStatus.LOGIN_STATE_UNKNOWN
