"""Side-effect-bounded login state detection and orchestration."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from workflows.result import WorkflowResult, WorkflowStage, WorkflowStatus


class LoginState(str, Enum):
    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    UNKNOWN = "unknown"


StateDetector = Callable[[object], LoginState]
LoginAction = Callable[[], bool]


def _normalize_state(value: object) -> LoginState:
    if isinstance(value, LoginState):
        return value
    if value is True:
        return LoginState.LOGGED_IN
    if value is False:
        return LoginState.LOGGED_OUT
    return LoginState.UNKNOWN


def detect_login_state(page: object) -> LoginState:
    """Probe login state without starting a login flow."""
    for name in ("check_login_status_smart", "_home_logged_in_quick_check"):
        probe = getattr(page, name, None)
        if not callable(probe):
            continue
        try:
            return _normalize_state(probe())
        except Exception:
            return LoginState.UNKNOWN
    return LoginState.UNKNOWN


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
