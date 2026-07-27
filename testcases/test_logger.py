import logging

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
