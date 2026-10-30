"""Модульні тести частки повернення p за FR-13 (lab5-scope.md, п. 6).

p у відповідь API не виходить, тому перевіряється функція сервісного шару
`refund_share(initiator, previous_status, cancelled_at, check_in_at) -> p, %`.
Момент заїзду — «2027-06-10 14:00», як у сценарії «Повернення за шкалою» (booking.feature).
"""
from datetime import timedelta

import pytest

from src.bookings import refund_share
from tests.unit.conftest import kyiv

CHECK_IN_AT = kyiv("2027-06-10 14:00")


@pytest.mark.parametrize(
    "before_check_in, expected",
    [
        (timedelta(hours=168), 100),
        (timedelta(hours=167, minutes=59), 50),
        (timedelta(hours=100), 50),
        (timedelta(hours=72), 50),
        (timedelta(hours=71, minutes=59), 0),
    ],
    ids=["168:00", "167:59", "100:00", "72:00", "71:59"],
)
def test_guest_cancels_confirmed_by_scale(before_check_in, expected):
    """FR-13; AC-13.1 (гість, CONFIRMED: t ≥ 168 → 100%; 72 ≤ t < 168 → 50%; t < 72 → 0%)."""
    assert refund_share("GUEST", "CONFIRMED", CHECK_IN_AT - before_check_in, CHECK_IN_AT) == expected


@pytest.mark.parametrize("before_check_in", [timedelta(hours=200), timedelta(hours=24), timedelta(hours=1)])
def test_guest_cancels_pending_gets_full_refund(before_check_in):
    """FR-13; AC-13.2 (скасування гостем запиту в PENDING — p = 100% незалежно від t)."""
    assert refund_share("GUEST", "PENDING", CHECK_IN_AT - before_check_in, CHECK_IN_AT) == 100


@pytest.mark.parametrize("before_check_in", [timedelta(hours=200), timedelta(hours=100), timedelta(hours=1)])
def test_host_cancels_gets_full_refund(before_check_in):
    """FR-13; AC-13.3 (скасування власником — p = 100% незалежно від t)."""
    assert refund_share("HOST", "CONFIRMED", CHECK_IN_AT - before_check_in, CHECK_IN_AT) == 100
