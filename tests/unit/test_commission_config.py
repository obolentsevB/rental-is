"""Модульний тест зміни відсотка комісії в конфігурації (FR-06, NFR-10; lab5-scope.md, зведення AC).

Відсоток комісії — параметр платформи, операції для його зміни в API немає, тому підміняється
значення сервісного шару `src.bookings.COMMISSION_RATE`.
"""
from decimal import Decimal

from src import bookings
from tests.unit.conftest import book


def test_commission_change_applies_only_to_new_requests(client, monkeypatch, guest, other_guest, make_listing):
    """FR-06; AC-06.6 (створені бронювання зберігають старий відсоток, нові запити отримують новий)."""
    listing = make_listing()
    old = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    assert (old["commissionRate"], old["commission"]) == (10, "246.91")

    monkeypatch.setattr(bookings, "COMMISSION_RATE", Decimal("15"))
    new = book(client, other_guest, listing["id"], "2030-06-10", "2030-06-12")

    assert (new["commissionRate"], new["commission"], new["prepayment"]) == (15, "370.36", "2839.48")
    stored = client.get(f"/bookings/{old['id']}", headers=guest).json()
    assert (stored["commissionRate"], stored["commission"], stored["prepayment"]) == (10, "246.91", "2716.03")
