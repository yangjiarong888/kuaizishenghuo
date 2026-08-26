import logging
import sys

import pytest

import commons.logger as logger_module


pytestmark = pytest.mark.unit


def reset_logger_state():
    logger_module._log_file_path_cache = None
    for name in ("unit.logger", "unit.logger.second"):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


def test_setup_logger_is_idempotent(tmp_path, monkeypatch):
    reset_logger_state()
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))

    first = logger_module.setup_logger("unit.logger")
    second = logger_module.setup_logger("unit.logger")

    assert first is second
    assert (
        len(
            [
                handler
                for handler in first.handlers
                if getattr(handler, "_chopsticks_managed", False)
            ]
        )
        == 2
    )


def test_logger_redacts_keyed_secrets(tmp_path, monkeypatch):
    reset_logger_state()
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    logger = logger_module.setup_logger("unit.logger.second")

    logger.error("password=secret-value verification_code: 123456 token=abc")
    for handler in logger.handlers:
        handler.flush()

    content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
    assert "secret-value" not in content
    assert "123456" not in content
    assert "token=abc" not in content
    assert "<redacted>" in content


def test_takeout_log_name_describes_cod_command(tmp_path, monkeypatch):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_takeout_wangwang.py",
            "--checkout",
            "--checkout-payment",
            "cod",
        ],
    )

    name = logger_module._build_log_path().name

    assert "takeout_wangwang_checkout_cod" in name


def test_takeout_log_name_describes_delivery_slot_ordinal(tmp_path, monkeypatch):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_takeout_wangwang.py",
            "--checkout",
            "--delivery-time-slot-ordinal",
            "5",
        ],
    )

    name = logger_module._build_log_path().name

    assert "takeout_wangwang_checkout_slot_ordinal_5" in name


def test_takeout_log_name_describes_address_creation_policy(tmp_path, monkeypatch):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_takeout_wangwang.py",
            "--checkout",
            "--address-policy",
            "auto",
        ],
    )

    name = logger_module._build_log_path().name

    assert "takeout_wangwang_checkout_address_auto" in name


def test_log_tag_keeps_safe_chinese_business_name():
    assert logger_module._sanitize_log_file_tag("商城首页搜索矩阵") == "商城首页搜索矩阵"


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["scripts/run_home_search_matrix.py"], "App首页搜索矩阵"),
        (
            ["scripts/run_shop_business.py", "--action", "search_matrix"],
            "商城首页搜索矩阵",
        ),
    ],
)
def test_search_matrix_command_uses_business_log_tag(monkeypatch, argv, expected):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setattr(sys, "argv", argv)

    assert logger_module._log_file_tag_from_env_or_argv() == expected


def test_business_tag_replaces_generic_filename_stem(tmp_path, monkeypatch):
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("CHOPSTICKLIFE_LOG_FILE_TAG", "商城首页搜索矩阵")

    name = logger_module._build_log_path().name

    assert name.startswith("商城首页搜索矩阵_")
    assert not name.startswith("chopsticklife_")


@pytest.mark.parametrize(
    ("scope", "expected"),
    [("home", "外卖首页搜索矩阵"), ("wangwang", "旺旺店内搜索矩阵")],
)
def test_takeout_search_matrix_uses_scope_business_tag(
    monkeypatch, scope, expected
):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_takeout_search_matrix.py", "--scope", scope],
    )
    assert logger_module._log_file_tag_from_env_or_argv() == expected


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("--full-business", "外卖完整业务_旺旺超市_真实COD下单"),
        ("--full-business-preview", "外卖完整业务_安全预览"),
    ],
)
def test_full_takeout_business_uses_ordered_business_log_tag(
    monkeypatch, flag, expected
):
    monkeypatch.delenv("CHOPSTICKLIFE_LOG_FILE_TAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["scripts/run_takeout_wangwang.py", flag])
    assert logger_module._log_file_tag_from_env_or_argv() == expected
