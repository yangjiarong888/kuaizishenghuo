"""Side-effect-bounded login state detection and orchestration."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from appium.webdriver.common.appiumby import AppiumBy

from workflows.result import WorkflowResult, WorkflowStage, WorkflowStatus


class LoginState(str, Enum):
    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    UNKNOWN = "unknown"


StateDetector = Callable[[object], LoginState]
LoginAction = Callable[[], bool]
APP_PACKAGES = frozenset(
    {
        "com.bs.feifubao",
        "com.ba.feifubao",
        "com.bx.feifubao",
        "com.hu.feifubao",
    }
)


def _normalize_state(value: object) -> LoginState:
    if isinstance(value, LoginState):
        return value
    return LoginState.UNKNOWN


def _visible_any(driver: object, selectors: tuple[tuple[str, str], ...]) -> bool | None:
    found = False
    for by, value in selectors:
        try:
            elements = driver.find_elements(by, value)
        except Exception:
            return None
        for element in elements:
            try:
                if element.is_displayed():
                    found = True
            except Exception:
                return None
    return found


def detect_login_state(page: object) -> LoginState:
    """Use independent visible signals without clicking or dismissing UI."""
    driver = getattr(page, "driver", None)
    if driver is None:
        return LoginState.UNKNOWN
    try:
        current_package = str(driver.current_package)
        if current_package not in APP_PACKAGES:
            return LoginState.UNKNOWN
    except Exception:
        return LoginState.UNKNOWN

    logged_in = _visible_any(
        driver,
        (
            (AppiumBy.ID, f"{current_package}:id/ll_exchange_rate"),
        ),
    )
    logged_out = _visible_any(
        driver,
        (
            (
                AppiumBy.XPATH,
                '//*[@text="立即登录" or @text="登录筷子生活"]',
            ),
        ),
    )
    if logged_in is None or logged_out is None or logged_in == logged_out:
        return LoginState.UNKNOWN
    return LoginState.LOGGED_IN if logged_in else LoginState.LOGGED_OUT


def ensure_logged_in(
    page: object,
    *,
    state_detector: StateDetector = detect_login_state,
    login_action: LoginAction | None = None,
) -> WorkflowResult:
    """Require an explicit login action and only run it when logged out."""
    try:
        state = _normalize_state(state_detector(page))
    except Exception:
        state = LoginState.UNKNOWN

    if state is LoginState.LOGGED_IN:
        return WorkflowResult.success(
            stage=WorkflowStage.LOGIN,
            message="账号已登录",
        )
    if state is LoginState.UNKNOWN:
        return WorkflowResult.failure(
            status=WorkflowStatus.LOGIN_STATE_UNKNOWN,
            stage=WorkflowStage.LOGIN,
            message="无法可靠确认登录状态",
        )
    if login_action is None:
        return WorkflowResult.failure(
            status=WorkflowStatus.LOGIN_REQUIRED,
            stage=WorkflowStage.LOGIN,
            message="账号未登录，且未提供显式登录动作",
        )

    try:
        action_ok = bool(login_action())
    except Exception:
        action_ok = False
    if not action_ok:
        return WorkflowResult.failure(
            status=WorkflowStatus.LOGIN_FAILED,
            stage=WorkflowStage.LOGIN,
            message="显式登录动作失败",
        )

    try:
        state_after = _normalize_state(state_detector(page))
    except Exception:
        state_after = LoginState.UNKNOWN
    if state_after is not LoginState.LOGGED_IN:
        status = (
            WorkflowStatus.LOGIN_STATE_UNKNOWN
            if state_after is LoginState.UNKNOWN
            else WorkflowStatus.LOGIN_FAILED
        )
        return WorkflowResult.failure(
            status=status,
            stage=WorkflowStage.LOGIN,
            message="登录后状态校验失败",
        )
    return WorkflowResult.success(
        stage=WorkflowStage.LOGIN,
        message="显式登录并校验成功",
    )
