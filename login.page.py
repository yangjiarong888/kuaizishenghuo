"""
login.page.py - Appium 登录自动化脚本入口

用法示例（在项目根目录 `kuaizishenghuo` 执行）：
  python login.page.py --method wechat
  python login.page.py --method qq
  python login.page.py --method google
  python login.page.py --method phone
  python login.page.py --method customer_service
  python login.page.py --method password
  python login.page.py --method forget_password
  python login.page.py --method password --no-from-home   # 已在登录页，跳过首页「立即登录」
  python login.page.py --method password --phone 13800138000 --password 你的密码
  python login.page.py --method phone --phone 13800138000
  python login.page.py --method phone --code 123456   # 非交互：直接传入短信验证码

账号密码来自命令行参数或环境变量 LOGIN_DEFAULT_PHONE / LOGIN_DEFAULT_PASSWORD，不在代码内保存真实凭据。
验证码登录：未传 --code 时默认在终端 input() 手动输入短信码（page_source 易含误匹配数字，已不再默认从页面自动猜码）。
若需恢复从页面正则猜码（不推荐），可设环境变量 LOGIN_SMS_PARSE_CODE_FROM_PAGE=1。

注意：
- 由于第三方授权页（微信/QQ/谷歌）UI 可能因登录状态不同而变化，本脚本使用“尽力点击授权/允许”策略。
- 验证码如果不能自动抓取，会在终端提示手动输入。
- 日志文件：`logs/chopsticklife_<登录方式>_YYYYMMDD_HHMMSS.log`（由 `--method` 决定，如 `chopsticklife_qq_20260403_164610.log`）。
  其它入口未带 `--method` 时可设环境变量 `CHOPSTICKLIFE_LOG_FILE_TAG=qq`。
"""

from __future__ import annotations

import argparse

from pages.login_page import LoginData, LoginPage
from commons.driver import DriverManager
from commons.logger import setup_logger


logger = setup_logger(__name__)


def _missing_required_login_fields(method: str, data: LoginData) -> list[str]:
    missing: list[str] = []
    if method in ("phone", "password", "forget_password") and not data.resolved_phone():
        missing.append("LOGIN_DEFAULT_PHONE/--phone")
    if method == "password" and not data.resolved_password():
        missing.append("LOGIN_DEFAULT_PASSWORD/--password")
    if method == "forget_password" and not data.resolved_new_password():
        missing.append("LOGIN_DEFAULT_NEW_PASSWORD")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method",
        type=lambda s: s.strip().lower(),
        choices=[
            "wechat",
            "qq",
            "google",
            "phone",
            "customer_service",
            "password",
            "forget_password",
        ],
        required=True,
        help="登录方式（不区分大小写，如 WeChat / wechat 均可）",
    )
    parser.add_argument(
        "--no-from-home",
        action="store_true",
        help="不从首页点击「立即登录」（已在登录/验证码等页面时使用）",
    )
    parser.add_argument(
        "--phone",
        default=None,
        help="登录手机号/账号（不设则用环境变量 LOGIN_DEFAULT_PHONE）",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="登录密码（不设则用环境变量 LOGIN_DEFAULT_PASSWORD）",
    )
    parser.add_argument(
        "--code",
        default=None,
        help="短信验证码（仅 --method phone 等需要时有效；不传则终端手动输入或自动从页面猜）",
    )
    args = parser.parse_args()

    session_name = f"login_{args.method}"
    data_kw = {}
    if args.phone:
        data_kw["phone"] = args.phone.strip()
    if args.password:
        data_kw["password"] = args.password
    data = LoginData(**data_kw)
    if args.code:
        data.verification_code = args.code.strip()
    missing = _missing_required_login_fields(args.method, data)
    if missing:
        logger.error("缺少登录参数：%s", ", ".join(missing))
        return 2

    page = LoginPage(session_name=session_name, data=data)
    try:
        # 除「客服语音验证码」流外，默认从首页进入登录页
        entered = False
        if not args.no_from_home and args.method != "customer_service":
            entered = page.open_login_from_home()
            if not entered:
                logger.warning("从首页进入登录页失败，将假设当前已在登录相关页面")

        # open_login_from_home 已成功时，页面可能尚未刷新完；补一轮短等待避免误报
        if not page.is_login_page_loaded():
            if entered:
                page.wait_for_login_landing_page(timeout=15)
            if not page.is_login_page_loaded():
                logger.warning(
                    "未检测到登录页特征：请手动确保当前为登录聚合页，或关活动页后重跑。"
                )

        if args.method == "wechat":
            ok = page.login_by_wechat()
        elif args.method == "qq":
            ok = page.login_by_qq()
        elif args.method == "google":
            ok = page.login_by_google()
        elif args.method == "phone":
            ok = page.login_by_phone_sms()
        elif args.method == "customer_service":
            ok = page.customer_service_voice_captcha_flow()
        elif args.method == "password":
            ok = page.login_by_account_password()
        elif args.method == "forget_password":
            ok = page.forget_password()
        else:
            ok = False

        logger.info(f"登录方法 {args.method} 执行结果: {'成功' if ok else '失败'}")
        return 0 if ok else 1
    finally:
        DriverManager().close_driver(session_name)


if __name__ == "__main__":
    raise SystemExit(main())
