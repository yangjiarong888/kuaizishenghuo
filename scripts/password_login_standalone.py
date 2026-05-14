#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅「账号密码登录」入口，逻辑与项目根目录执行
  python login.page.py --method password
一致。可复制本文件到其它目录时：保留同级 `pages/`、`commons/` 等包，或把下面 ROOT 改成你的项目根。

用法（在 kuaizishenghuo 项目根目录）:
  python scripts/password_login_standalone.py
  python scripts/password_login_standalone.py --no-from-home

依赖: Appium 已启动、设备已连接；可选环境变量 APP_PACKAGE、APP_ACTIVITY、START_MODE、POST_LOGIN_* 等与主项目相同。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.login_page import LoginData, LoginPage

logger = setup_logger(__name__)
SESSION_NAME = "login_password_standalone"


def main() -> int:
    parser = argparse.ArgumentParser(description="仅执行账号密码登录")
    parser.add_argument(
        "--no-from-home",
        action="store_true",
        help="已在登录相关页时使用，跳过首页「立即登录」",
    )
    parser.add_argument(
        "--phone",
        default=None,
        help="覆盖默认手机号（不设则用环境变量 LOGIN_DEFAULT_PHONE 或 LoginData 内置默认）",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="覆盖默认密码（不设则用环境变量 LOGIN_DEFAULT_PASSWORD 或 LoginData 内置默认）",
    )
    args = parser.parse_args()

    data_kw = {}
    if args.phone:
        data_kw["phone"] = args.phone.strip()
    if args.password:
        data_kw["password"] = args.password
    data = LoginData(**data_kw)

    page = LoginPage(session_name=SESSION_NAME, data=data)
    try:
        entered = False
        if not args.no_from_home:
            entered = page.open_login_from_home()
            if not entered:
                logger.warning("从首页进入登录页失败，将假设当前已在登录相关页面")

        if not page.is_login_page_loaded():
            if entered:
                page.wait_for_login_landing_page(timeout=15)
            if not page.is_login_page_loaded():
                logger.warning(
                    "未检测到登录页特征：请手动确保当前为登录聚合页，或改用 --no-from-home。"
                )

        ok = page.login_by_account_password()
        logger.info("密码登录执行结果: %s", "成功" if ok else "失败")
        return 0 if ok else 1
    finally:
        DriverManager().close_driver(SESSION_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
