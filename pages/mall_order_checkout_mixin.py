"""Guarded mall checkout side effects."""

from __future__ import annotations

from commons.logger import setup_logger
from flows.mall_order_types import AmountSnapshot, ProductSnapshot, SubmitResult


logger = setup_logger(__name__)


class MallOrderCheckoutMixin:
    """Checkout boundary with amount and explicit side-effect guards."""

    def assert_within_payable_limit(
        self,
        amounts: AmountSnapshot,
    ) -> None:
        if self.max_payable is None or self.max_payable <= 0:
            raise AssertionError("真实提交缺少正数 --max-payable")
        if amounts.payable > self.max_payable:
            raise AssertionError(
                "确认页实付 %.2f 超过 --max-payable %.2f"
                % (amounts.payable, self.max_payable)
            )

    def finish_checkout(
        self,
        product: ProductSnapshot,
        *,
        submit_order: bool,
    ) -> None:
        self.dismiss_checkout_upsell_if_visible()
        amounts = self.assert_checkout_matches_detail(product)
        if self.ensure_test_address:
            self.ensure_test_address_from_checkout_flow(
                force_add=self.force_add_test_address
            )
            amounts = self.assert_checkout_matches_detail(product)
        if self.apply_mall_platform_coupon_if_needed():
            amounts = self.assert_checkout_matches_detail(product)
        self.apply_checkout_preferences()
        amounts = self.read_amounts(product)
        selected_slot = self.pick_tomorrow_random_preorder_time_if_needed()
        if selected_slot:
            amounts = self.read_amounts(product)
        if not submit_order:
            logger.info(
                "未传 --submit-order：停在确认订单页，跳过真实提交和支付"
            )
            return
        self.assert_within_payable_limit(amounts)
        submit = self.submit_order(amounts)
        self.pay_and_assert(submit, product)
        if self.send_im_after_order:
            self.send_order_cancel_im_if_needed(submit)
        if self.cancel_after_order:
            self.cancel_created_order(submit)

    def cancel_created_order(self, submit: SubmitResult) -> None:
        if not submit.order_no:
            raise AssertionError(
                "本次创建订单未解析到订单号，禁止自动取消；需要人工检查"
            )
        self.ensure_order_detail_page()
        if not self.click_labels(
            ("取消订单", "申请取消"),
            desc="取消本次测试订单",
            y_min_ratio=0.20,
            y_max_ratio=1.0,
        ):
            raise AssertionError(
                f"订单 {submit.order_no} 未找到取消入口，需要人工处理"
            )
        self.click_labels(
            ("测试订单", "不想要了", "其他"),
            desc="选择取消原因",
            y_min_ratio=0.15,
            y_max_ratio=1.0,
        )
        if not self.click_labels(
            ("确认取消", "确定", "提交"),
            desc="确认取消本次测试订单",
            y_min_ratio=0.40,
            y_max_ratio=1.0,
        ):
            raise AssertionError(
                f"订单 {submit.order_no} 取消确认失败，需要人工处理"
            )
        self.assert_page_contains_any(
            ("已取消", "取消成功", "订单关闭"),
            f"订单 {submit.order_no} 未确认取消成功，需要人工处理",
            timeout=20.0,
        )
