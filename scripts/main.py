"""Top-level safe automation command dispatcher."""

from __future__ import annotations

import argparse

from commons.logger import setup_logger
from scripts.run_login import SUPPORTED_LOGIN_METHODS, run_login_method
from scripts.smoke_test import smoke_test


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="筷子生活 App 自动化测试")
    parser.add_argument(
        "--mode",
        choices=("smoke", "login", "quick", "all", "method"),
        default="smoke",
    )
    parser.add_argument("--method", choices=tuple(sorted(SUPPORTED_LOGIN_METHODS)))
    parser.add_argument("--device", help="兼容参数；设备优先由 ANDROID_DEVICE_NAME 配置")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode in {"login", "method", "all"} and not args.method:
        logger.error("mode=%s 必须显式提供 --method", args.mode)
        return 2

    if args.mode in {"smoke", "quick"}:
        return 0 if smoke_test() is not False else 1
    if args.mode in {"login", "method"}:
        return 0 if run_login_method(args.method) else 1

    smoke_ok = smoke_test() is not False
    login_ok = run_login_method(args.method)
    return 0 if smoke_ok and login_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
