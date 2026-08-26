#!/usr/bin/env python3
"""Run the shared nine-keyword matrix from the App-home search entrance."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.diagnostics import capture_failure
from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.Home import ChopsticksTester
from pages.business_search_spec import SearchMatrixError


logger = setup_logger(__name__)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="App 首页九关键词商品搜索矩阵")
    parser.add_argument("--session", default="home_search_matrix")
    parser.add_argument("--cold", action="store_true")
    args = parser.parse_args(argv)

    os.environ["START_MODE"] = "cold" if args.cold else "activate"
    manager = DriverManager()
    driver = manager.get_driver(session_name=args.session)
    try:
        tester = ChopsticksTester(driver=driver, session_name=args.session)
        tester.run_home_search_matrix()
        logger.info("App 首页搜索矩阵执行通过")
        return 0
    except SearchMatrixError as exc:
        capture_failure(
            driver,
            f"home_search_{exc.index}_{exc.keyword}",
            "artifacts/home_search",
        )
        logger.error(
            "App 首页搜索矩阵失败 source=%s stage=%s index=%s keyword=%r",
            exc.source,
            exc.stage,
            exc.index,
            exc.keyword,
        )
        return 1
    finally:
        manager.close_driver(session_name=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
