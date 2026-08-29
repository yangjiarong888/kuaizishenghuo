#!/usr/bin/env python3
"""
外卖搜索矩阵：支持外卖首页搜索和旺旺商家主页搜索两个入口。

须在项目根目录执行，且 Appium 已启动、设备已连接。

用法：
  python scripts/run_takeout_search_matrix.py --scope home
  python scripts/run_takeout_search_matrix.py --scope wangwang
  python scripts/run_takeout_search_matrix.py --scope wangwang --shop "旺旺超市 WWCS"
  python scripts/run_takeout_search_matrix.py --scope home --session takeout_search_demo

home 会先验证热搜词、榜单商家、榜单左滑和可选历史搜索，再执行固定九关键词；
wangwang 只执行商家主页内的固定九关键词搜索。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commons.diagnostics import capture_failure
from commons.driver import DriverManager
from commons.logger import setup_logger
from pages.business_search_spec import SearchMatrixError, run_search_matrix
from pages.takeout_home_search_adapter import TakeoutHomeSearchAdapter
from pages.takeout_merchant_search_adapter import TakeoutMerchantSearchAdapter
from pages.takeout_page import TakeoutPageBase


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="外卖共享九关键词搜索矩阵")
    parser.add_argument("--scope", choices=("home", "wangwang"), default="home")
    parser.add_argument("--shop", default="旺旺超市 WWCS")
    parser.add_argument("--session", default="takeout_search_matrix")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    manager = DriverManager()
    driver = None
    try:
        driver = manager.get_driver(session_name=args.session)
        page = TakeoutPageBase(driver)
        if not page.ensure_takeout_tab():
            return 1
        if args.scope == "wangwang" and not page.scroll_to_and_open_shop(args.shop):
            return 1
        adapter = (
            TakeoutMerchantSearchAdapter(page)
            if args.scope == "wangwang"
            else TakeoutHomeSearchAdapter(page)
        )
        run_search_matrix(adapter)
        logger.info("%s执行通过", adapter.source_name)
        return 0
    except SearchMatrixError as exc:
        if driver is not None:
            capture_failure(
                driver,
                f"takeout_search_{args.scope}_{exc.index}_{exc.keyword}",
                "artifacts/takeout_search",
            )
        logger.error(
            "外卖搜索矩阵失败 source=%s stage=%s index=%s keyword=%r",
            exc.source,
            exc.stage,
            exc.index,
            exc.keyword,
        )
        return 1
    finally:
        if driver is not None:
            manager.close_driver(session_name=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
