import pytest

from pages.rounding_payment import (
    RoundingOption,
    RoundingPaymentMixin,
    compute_rounding_options,
    parse_checkout_money,
)


class FakeRoundingElement:
    def __init__(
        self,
        page: "FakeRoundingPage",
        amount: int,
        change: float | None = None,
        *,
        rounding_semantics: bool = True,
        grouped: bool = False,
    ) -> None:
        self._page = page
        self._amount = amount
        self._change = change if change is not None else amount - page.total
        self._rounding_semantics = rounding_semantics
        self._grouped = grouped

    @property
    def text(self) -> str:
        amount = f"{self._amount:,}" if self._grouped else str(self._amount)
        change = f"{self._change:,.2f}" if self._grouped else f"{self._change:.2f}"
        if self._rounding_semantics:
            return f"取整金额 {amount} 找零 {change}"
        return f"SKU {amount} discount {change}"

    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_selected(self) -> bool:
        return self._page.selected_amount == self._amount

    def click(self) -> None:
        if not self._page.never_updates:
            self._page.selected_amount = self._amount


class FakeRoundingDriver:
    def __init__(self, page: "FakeRoundingPage") -> None:
        self._page = page

    def find_elements(self, _by: str, selector: str) -> list[FakeRoundingElement]:
        if self._page.incorrect_candidate_match:
            return [FakeRoundingElement(self._page, 12000, 10550)]
        if self._page.semantic_decoy:
            return [
                FakeRoundingElement(
                    self._page,
                    2000,
                    550,
                    rounding_semantics=False,
                )
            ]
        if self._page.grouped_only:
            if '"2,000"' in selector and '"1,550"' in selector:
                return [FakeRoundingElement(self._page, 2000, 1550, grouped=True)]
            return []
        matches = []
        for amount in self._page.option_amounts:
            if str(amount) in selector:
                matches.extend(
                    FakeRoundingElement(self._page, amount)
                    for _ in range(self._page.match_count)
                )
        return matches


class FakeRoundingPage(RoundingPaymentMixin):
    def __init__(
        self,
        *,
        total: float,
        never_updates: bool = False,
        match_count: int = 1,
        show_candidate_readback: bool = False,
        incorrect_candidate_match: bool = False,
        semantic_decoy: bool = False,
        grouped_only: bool = False,
    ) -> None:
        self.total = total
        self.never_updates = never_updates
        self.match_count = match_count
        self.show_candidate_readback = show_candidate_readback
        self.incorrect_candidate_match = incorrect_candidate_match
        self.semantic_decoy = semantic_decoy
        self.grouped_only = grouped_only
        self.selected_amount: int | None = None
        self.option_amounts = [option.amount for option in compute_rounding_options(total)]
        self.driver = FakeRoundingDriver(self)

    def page_texts(self) -> list[str]:
        texts = [f"应付 ₱{self.total:.2f}", "货到付款取整"]
        if self.show_candidate_readback:
            default = compute_rounding_options(self.total)[0]
            texts.append(f"取整金额 {default.amount} 找零 {default.change:.2f}")
        if self.selected_amount is not None:
            change = self.selected_amount - self.total
            texts.append(f"取整金额 {self.selected_amount} 找零 {change:.2f}")
        return texts


class CheckoutTextsPage(RoundingPaymentMixin):
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts

    def page_texts(self) -> list[str]:
        return self._texts


def test_rounding_options_for_370_are_strictly_higher_and_ordered() -> None:
    assert compute_rounding_options(370) == [
        RoundingOption(400, 30),
        RoundingOption(500, 130),
        RoundingOption(1000, 630),
    ]


def test_exact_thousand_has_no_rounding_options() -> None:
    assert compute_rounding_options(2000) == []


def test_non_positive_payable_has_no_rounding_options() -> None:
    assert compute_rounding_options(0) == []


def test_rounding_options_honor_a_non_positive_limit_and_round_change() -> None:
    assert compute_rounding_options(370.125, limit=0) == []
    assert compute_rounding_options(370.125, limit=1) == [
        RoundingOption(400, 29.88),
    ]


def test_rounding_options_above_a_thousand_use_successive_thousands() -> None:
    assert compute_rounding_options(1450) == [
        RoundingOption(2000, 550),
        RoundingOption(3000, 1550),
        RoundingOption(4000, 2550),
    ]


def test_parse_checkout_money_requires_a_money_or_total_hint() -> None:
    assert parse_checkout_money("应付 ₱1,450.25") == 1450.25
    assert parse_checkout_money("商品编号 1450") is None


def test_parse_checkout_money_ignores_an_unrelated_number_before_the_total() -> None:
    assert parse_checkout_money("商品编号 123，应付 ₱1,450.25") == 1450.25


@pytest.mark.parametrize(
    "texts",
    [
        ["合计 ₱100.00", "应付 ₱80.00"],
        ["应付 ₱80.00", "合计 ₱100.00"],
    ],
)
def test_checkout_payable_prioritizes_final_payable_over_total_regardless_of_order(
    texts: list[str],
) -> None:
    assert CheckoutTextsPage(texts).checkout_payable_amount() == 80.0


def test_checkout_payable_rejects_conflicting_final_payable_amounts() -> None:
    page = CheckoutTextsPage(["应付 ₱80.00", "实付 ₱90.00"])

    with pytest.raises(AssertionError, match="应付金额"):
        page.checkout_payable_amount()


def test_checkout_payable_rejects_a_one_cent_final_payable_conflict() -> None:
    page = CheckoutTextsPage(["应付 ₱80.00", "实付 ₱80.01"])

    with pytest.raises(AssertionError, match="应付金额"):
        page.checkout_payable_amount()


def test_checkout_payable_accepts_duplicate_final_amount_and_unique_total_fallback() -> None:
    assert CheckoutTextsPage(["应付 ₱80.00", "实付 ₱80.00"]).checkout_payable_amount() == 80.0
    assert CheckoutTextsPage(["合计 ₱100.00"]).checkout_payable_amount() == 100.0


def test_checkout_payable_rejects_conflicting_total_fallbacks() -> None:
    page = CheckoutTextsPage(["合计 ₱100.00", "总计 ₱110.00"])

    with pytest.raises(AssertionError, match="合计金额"):
        page.checkout_payable_amount()


def test_custom_rounding_rejects_decimal_or_non_increasing_amount() -> None:
    page = FakeRoundingPage(total=1450)

    with pytest.raises(AssertionError):
        page.select_checkout_rounding_payment(payable=1450, custom_amount=1450)
    with pytest.raises(AssertionError):
        page.select_checkout_rounding_payment(payable=1450, custom_amount=2500.5)


def test_selection_fails_when_readback_does_not_match() -> None:
    page = FakeRoundingPage(total=1450, never_updates=True)

    with pytest.raises(AssertionError, match="取整|回读"):
        page.select_checkout_rounding_payment(payable=1450)


def test_selection_rejects_an_unselected_candidate_text_as_readback() -> None:
    page = FakeRoundingPage(
        total=1450,
        never_updates=True,
        show_candidate_readback=True,
    )

    with pytest.raises(AssertionError, match="取整|回读"):
        page.select_checkout_rounding_payment(payable=1450)


def test_selection_clicks_the_unique_default_option_and_reads_it_back() -> None:
    page = FakeRoundingPage(total=1450)

    assert page.select_checkout_rounding_payment() == RoundingOption(2000, 550)
    assert page.selected_amount == 2000


def test_selection_rejects_ambiguous_visible_option_matches() -> None:
    page = FakeRoundingPage(total=1450, match_count=2)

    with pytest.raises(AssertionError, match="唯一"):
        page.select_checkout_rounding_payment()


def test_selection_rejects_a_substring_match_for_another_option() -> None:
    page = FakeRoundingPage(total=1450, incorrect_candidate_match=True)

    with pytest.raises(AssertionError, match="唯一"):
        page.select_checkout_rounding_payment()


def test_selection_rejects_a_unique_non_rounding_numeric_decoy() -> None:
    page = FakeRoundingPage(total=1450, semantic_decoy=True)

    with pytest.raises(AssertionError, match="唯一"):
        page.select_checkout_rounding_payment()


def test_selection_supports_grouped_amount_and_change_controls() -> None:
    page = FakeRoundingPage(total=450, grouped_only=True)

    assert page.select_checkout_rounding_payment(custom_amount=2000) == RoundingOption(2000, 1550)
    assert page.selected_amount == 2000
