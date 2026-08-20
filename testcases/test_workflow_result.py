import pytest

from workflows.result import WorkflowResult, WorkflowStage, WorkflowStatus


def test_success_result_is_ok_and_preserves_order_identity():
    result = WorkflowResult.success(
        stage=WorkflowStage.CLEANUP,
        message="order canceled",
        order_id="ORD-1",
    )

    assert result.ok is True
    assert result.status is WorkflowStatus.SUCCESS
    assert result.order_id == "ORD-1"


def test_failure_rejects_success_status():
    with pytest.raises(ValueError, match="SUCCESS"):
        WorkflowResult.failure(
            status=WorkflowStatus.SUCCESS,
            stage=WorkflowStage.CHECKOUT,
            message="invalid",
        )


def test_cleanup_failure_is_never_reported_as_success():
    result = WorkflowResult.failure(
        status=WorkflowStatus.ORDER_PLACED_CLEANUP_FAILED,
        stage=WorkflowStage.CLEANUP,
        message="cancel failed",
        order_id="ORD-2",
    )

    assert result.ok is False
    assert result.order_id == "ORD-2"
