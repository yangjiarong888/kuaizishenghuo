"""Composition entry for takeout shop checkout flows."""
from __future__ import annotations

from pages.takeout_checkout_mixin import TakeoutCheckoutMixin


class TakeoutShopMixin(TakeoutCheckoutMixin):
    """Combine shop detail, checkout, delivery time, payment, and cancellation flows."""

    pass
