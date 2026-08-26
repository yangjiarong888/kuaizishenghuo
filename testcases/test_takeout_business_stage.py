from types import SimpleNamespace

import pytest

import pages.takeout_business_stage as stage_module
from pages.takeout_business_stage import (
    TakeoutStageError,
    TakeoutStageResult,
    run_takeout_stage,
)


pytestmark = pytest.mark.unit


def test_stage_runner_logs_order_and_returns_value():
    page = SimpleNamespace(driver=object())
    result = run_takeout_stage(page, 1, "外卖首页分页", lambda: "three-pages")
    assert result == TakeoutStageResult(1, "外卖首页分页", "three-pages")


def test_stage_runner_captures_and_raises_on_false(monkeypatch):
    captured = []
    monkeypatch.setattr(
        stage_module,
        "capture_failure",
        lambda *args, **kwargs: captured.append((args, kwargs)),
    )
    with pytest.raises(TakeoutStageError) as exc:
        run_takeout_stage(
            SimpleNamespace(driver=object()), 2, "购物车入口", lambda: False
        )
    assert (exc.value.number, exc.value.name) == (2, "购物车入口")
    assert len(captured) == 1


def test_stage_runner_preserves_original_exception(monkeypatch):
    monkeypatch.setattr(stage_module, "capture_failure", lambda *_a, **_k: None)
    with pytest.raises(TakeoutStageError) as exc:
        run_takeout_stage(
            SimpleNamespace(driver=object()), 3, "回顶", lambda: 1 / 0
        )
    assert isinstance(exc.value.__cause__, ZeroDivisionError)
