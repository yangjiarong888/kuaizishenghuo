"""
登录业务入口：微信、QQ、Google、手机验证码、密码、客服及忘记密码。

须在项目根目录执行，且 Appium 已启动、设备已连接。

用法：
  python scripts/run_login.py --method wechat
  python scripts/run_login.py --method phone --phone "手机号" --code "验证码"
  python scripts/run_login.py --method password --phone "手机号" --password "密码"
  python scripts/run_login.py --method customer_service
  python scripts/run_login.py --method forget_password
  python scripts/run_login.py --method qq --no-from-home

phone/password/forget_password 也可读取 LOGIN_DEFAULT_PHONE、
LOGIN_DEFAULT_PASSWORD、LOGIN_DEFAULT_NEW_PASSWORD 环境变量。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.login_page import LoginData, LoginPage


logger = setup_logger(__name__)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="筷子生活登录自动化")
    parser.add_argument(
        "--method",
        type=lambda value: value.strip().lower(),
        choices=sorted(SUPPORTED_LOGIN_METHODS),
        required=True,
        help="登录方式",
    )
    parser.add_argument(
        "--no-from-home",
        action="store_true",
        help="当前已在登录页面，不从首页进入",
    )
    parser.add_argument("--phone", help="手机号；默认读取 LOGIN_DEFAULT_PHONE")
    parser.add_argument("--password", help="密码；默认读取 LOGIN_DEFAULT_PASSWORD")
    parser.add_argument("--code", help="短信验证码")
    return parser


def _missing_required_login_fields(method: str, data: LoginData) -> list[str]:
    missing: list[str] = []
    if method in ("phone", "password", "forget_password") and not data.resolved_phone():
        missing.append("LOGIN_DEFAULT_PHONE/--phone")
    if method == "password" and not data.resolved_password():
        missing.append("LOGIN_DEFAULT_PASSWORD/--password")
    if method == "forget_password" and not data.resolved_new_password():
        missing.append("LOGIN_DEFAULT_NEW_PASSWORD")
    return missing


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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_kwargs = {}
    if args.phone:
        data_kwargs["phone"] = args.phone.strip()
    if args.password:
        data_kwargs["password"] = args.password
    data = LoginData(**data_kwargs)
    if args.code:
        data.verification_code = args.code.strip()

    missing = _missing_required_login_fields(args.method, data)
    if missing:
        logger.error("缺少登录参数：%s", ", ".join(missing))
        return 2

    session_name = f"login_{args.method}"
    page = LoginPage(session_name=session_name, data=data)
    try:
        ok = run_login_method(
            args.method,
            page=page,
            from_home=not args.no_from_home,
            session_name=session_name,
        )
        logger.info("登录方法 %s 执行结果: %s", args.method, "成功" if ok else "失败")
        return 0 if ok else 1
    finally:
        DriverManager().close_driver(session_name)


if __name__ == "__main__":
    raise SystemExit(main())
