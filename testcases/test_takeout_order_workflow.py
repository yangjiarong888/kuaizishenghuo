from workflows.login_workflow import LoginState
from workflows.result import WorkflowStage, WorkflowStatus
from workflows.takeout_order_workflow import run_takeout_order_flow


class FakeTakeoutPage:
    def __init__(self, checkout_ok=True, order_submitted=False):
        self.checkout_ok = checkout_ok
        self._takeout_order_submitted = order_submitted
        self.checkout_kwargs = None

    def run_shop_checkout_pay_and_cancel_flow(self, **kwargs):
        self.checkout_kwargs = kwargs
        return self.checkout_ok


def logged_in(_):
    return LoginState.LOGGED_IN


def test_takeout_workflow_defaults_to_preview_without_submission():
    page = FakeTakeoutPage()

    result = run_takeout_order_flow(
        login_page=object(),
        takeout_page=page,
        state_detector=logged_in,
        open_shop=lambda: True,
    )

    assert result.ok is True
    assert result.stage is WorkflowStage.CHECKOUT
    assert page.checkout_kwargs["submit_order"] is False


def test_caller_cannot_smuggle_submission_through_checkout_kwargs():
    page = FakeTakeoutPage()

    run_takeout_order_flow(
        login_page=object(),
        takeout_page=page,
        submit_order=False,
        checkout_kwargs={"submit_order": True, "checkout_payment": "cod"},
        state_detector=logged_in,
        open_shop=lambda: True,
    )

    assert page.checkout_kwargs["submit_order"] is False


def test_open_shop_failure_stops_before_checkout():
    page = FakeTakeoutPage()

    result = run_takeout_order_flow(
        login_page=object(),
        takeout_page=page,
        state_detector=logged_in,
        open_shop=lambda: False,
    )

    assert result.status is WorkflowStatus.OPEN_SHOP_FAILED
    assert page.checkout_kwargs is None


def test_submitted_order_cleanup_failure_has_distinct_status():
    page = FakeTakeoutPage(checkout_ok=False, order_submitted=True)

    result = run_takeout_order_flow(
        login_page=object(),
        takeout_page=page,
        submit_order=True,
        state_detector=logged_in,
        open_shop=lambda: True,
    )

    assert result.status is WorkflowStatus.ORDER_PLACED_CLEANUP_FAILED
    assert result.stage is WorkflowStage.CLEANUP


def test_preview_failure_is_checkout_failure():
    page = FakeTakeoutPage(checkout_ok=False, order_submitted=False)

    result = run_takeout_order_flow(
        login_page=object(),
        takeout_page=page,
        state_detector=logged_in,
        open_shop=lambda: True,
    )

    assert result.status is WorkflowStatus.CHECKOUT_FAILED
    assert result.stage is WorkflowStage.CHECKOUT
