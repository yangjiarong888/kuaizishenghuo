"""Reusable login-method dispatch for production entry points."""

from __future__ import annotations

from commons.driver import DriverManager
from pages.login_page import LoginPage


SUPPORTED_LOGIN_METHODS = frozenset(
    {
        "wechat",
        "qq",
        "google",
        "phone",
        "customer_service",
        "password",
        "forget_password",
    }
)


def run_login_method(
    method: str,
    *,
    page=None,
    from_home: bool = True,
    session_name: str | None = None,
) -> bool:
    """Run one explicit login path; close only sessions created here."""
    normalized = (method or "").strip().lower()
    if normalized not in SUPPORTED_LOGIN_METHODS:
        raise ValueError(f"unsupported login method: {normalized!r}")

    owned = page is None
    resolved_session = session_name or f"login_{normalized}"
    login_page = page or LoginPage(session_name=resolved_session)
    try:
        if from_home and normalized != "customer_service":
            login_page.open_login_from_home()
        action_names = {
            "wechat": "login_by_wechat",
            "qq": "login_by_qq",
            "google": "login_by_google",
            "phone": "login_by_phone_sms",
            "customer_service": "customer_service_voice_captcha_flow",
            "password": "login_by_account_password",
            "forget_password": "forget_password",
        }
        return bool(getattr(login_page, action_names[normalized])())
    finally:
        if owned:
            DriverManager().close_driver(resolved_session)
