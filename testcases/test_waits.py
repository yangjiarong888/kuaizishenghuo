import pytest


pytestmark = pytest.mark.unit


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeDriver:
    def __init__(self, responses):
        self.responses = list(responses)

    def find_elements(self, by, value):
        if self.responses:
            return self.responses.pop(0)
        return []


def test_wait_until_returns_immediately_without_sleep():
    from commons.waits import wait_until

    clock = FakeClock()

    assert wait_until(
        lambda: True,
        timeout=1,
        clock=clock.monotonic,
        sleeper=clock.sleep,
    )
    assert clock.sleeps == []


def test_wait_until_polls_until_success():
    from commons.waits import wait_until

    clock = FakeClock()
    outcomes = iter((False, False, True))

    assert wait_until(
        lambda: next(outcomes),
        timeout=1,
        interval=0.1,
        clock=clock.monotonic,
        sleeper=clock.sleep,
    )
    assert clock.sleeps == [0.1, 0.1]


def test_wait_until_returns_false_at_deadline():
    from commons.waits import wait_until

    clock = FakeClock()

    assert (
        wait_until(
            lambda: False,
            timeout=0.2,
            interval=0.1,
            clock=clock.monotonic,
            sleeper=clock.sleep,
        )
        is False
    )
    assert clock.now == pytest.approx(0.2)


def test_find_optional_returns_none_after_timeout():
    from commons.waits import find_optional

    assert (
        find_optional(FakeDriver([[]]), ("id", "home"), timeout=0, interval=0.1)
        is None
    )


def test_find_required_raises_actionable_error():
    from commons.waits import RequiredElementNotFound, find_required

    with pytest.raises(RequiredElementNotFound, match="open home"):
        find_required(
            FakeDriver([[]]),
            ("id", "home"),
            timeout=0,
            interval=0.1,
            action="open home",
        )
