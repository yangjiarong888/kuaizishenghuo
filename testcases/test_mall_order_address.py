import pytest

from pages.mall_order_address_mixin import MallOrderAddressMixin


pytestmark = pytest.mark.unit


def test_target_address_labels_ignore_empty_values():
    page = object.__new__(MallOrderAddressMixin)
    page.address_name = "Tester"
    page.address_phone = ""
    page.address_query = "Manila"
    page.address_detail = ""

    assert page.target_address_labels() == ("Tester", "Manila")


def test_address_search_result_labels_derive_only_from_query():
    page = object.__new__(MallOrderAddressMixin)
    page.address_query = "Manila, Metro Manila"

    assert page.address_search_result_labels() == (
        "Manila, Metro Manila",
        "Manila",
    )


@pytest.mark.parametrize(
    ("blob", "expected"),
    [
        ("地址簿\nTester\nManila", True),
        ("地址簿\nTester", False),
        ("地址簿\nManila", False),
    ],
)
def test_target_address_requires_every_configured_label(blob, expected):
    page = object.__new__(MallOrderAddressMixin)
    page.address_name = "Tester"
    page.address_phone = ""
    page.address_query = "Manila"
    page.address_detail = ""
    page.page_blob = lambda: blob

    assert page.page_has_target_address() is expected


def test_checkout_address_reuses_existing_target_without_writing():
    page = object.__new__(MallOrderAddressMixin)
    events = []
    page.open_address_sheet_from_checkout = (
        lambda: events.append(("open",)) or True
    )
    page.copy_test_address = False
    page.edit_test_address = False
    page.select_existing_target_address = (
        lambda *, expect_checkout: (
            events.append(("select", expect_checkout)) or True
        )
    )
    page.add_test_address = lambda: events.append(("add",))

    assert page.ensure_test_address_from_checkout_flow() is None
    assert events == [("open",), ("select", True)]
