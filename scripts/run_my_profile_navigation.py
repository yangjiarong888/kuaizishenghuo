"""Run fail-closed, read-only navigation checks for the “我的” area."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.my_profile_page import MyProfilePage


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="个人中心只读导航巡检")
    parser.add_argument("--session", default="my_profile_navigation")
    parser.add_argument(
        "--logged-out",
        action="store_true",
        help="仅巡检未登录状态允许访问的只读入口",
    )
    parser.add_argument("--cold", action="store_true", help="冷启动 App")
    parser.add_argument(
        "--start-mode",
        choices=("activate", "cold"),
        help="显式指定 App 启动方式",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cold:
        os.environ["START_MODE"] = "cold"
    elif args.start_mode:
        os.environ["START_MODE"] = args.start_mode
    else:
        os.environ["START_MODE"] = "activate"

    manager = DriverManager()
    driver = None
    try:
        driver = manager.get_driver(session_name=args.session)
        page = MyProfilePage(driver)
        ok = (
            page.run_logged_out_navigation_smoke()
            if args.logged_out
            else page.run_navigation_smoke()
        )
        return 0 if ok else 1
    except Exception as exc:
        logger.error("个人中心只读巡检失败: %s", type(exc).__name__)
        return 1
    finally:
        if driver is not None:
            manager.close_driver(session_name=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
