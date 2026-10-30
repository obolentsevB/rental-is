"""Фікстури модульних тестів сервісного шару бронювань (lab5-scope.md, пп. 6, 10).

Точки, що спираються на реалізацію:
- `src.auth.TOKENS` — сховище токенів (п. 11);
- `src.bookings.now` — годинник сервісного шару, ін'єкція якого передбачена п. 10.
Час — Europe/Kyiv, як у spec/bdd/booking.feature.
"""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from src.main import app

KYIV = ZoneInfo("Europe/Kyiv")
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def kyiv(text):
    """Момент «YYYY-MM-DD HH:MM» за київським часом."""
    return datetime.fromisoformat(text).replace(tzinfo=KYIV)


class Clock:
    def __init__(self, start):
        self.current = kyiv(start)

    def set(self, text):
        self.current = kyiv(text)


@pytest.fixture
def clock(monkeypatch):
    """Керований годинник; за замовчуванням — «2027-06-01 10:00», як у передумовах booking.feature."""
    from src import bookings

    state = Clock("2027-06-01 10:00")
    monkeypatch.setattr(bookings, "now", lambda: state.current)
    return state


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(monkeypatch):
    from src import auth as auth_module

    def make(role):
        token = f"unit-{role.lower()}-{uuid.uuid4()}"
        monkeypatch.setitem(auth_module.TOKENS, token, {"userId": str(uuid.uuid4()), "role": role})
        return {"Authorization": f"Bearer {token}"}

    return make


@pytest.fixture
def host(auth):
    return auth("HOST")


@pytest.fixture
def guest(auth):
    return auth("GUEST")


@pytest.fixture
def other_guest(auth):
    return auth("GUEST")


@pytest.fixture
def make_listing(client, host):
    """Житло «Поділ» із передумови booking.feature: заїзд 14:00, виїзд 11:00, до 4 осіб."""

    def make(turnover=0):
        body = {
            "title": "Поділ",
            "city": "Київ",
            "address": "вул. Сагайдачного, 1",
            "maxGuests": 4,
            "pricePerNight": "1234.56",
            "photos": [{"data": PNG_1X1}],
            "checkInTime": "14:00",
            "checkOutTime": "11:00",
            "turnoverNights": turnover,
        }
        response = client.post("/listings", json=body, headers=host)
        assert response.status_code == 201
        return response.json()

    return make


def request_booking(client, headers, listing_id, check_in, check_out, guests_count=2):
    body = {"listingId": listing_id, "checkIn": check_in, "checkOut": check_out, "guestsCount": guests_count}
    return client.post("/bookings", json=body, headers=headers)


def book(client, headers, listing_id, check_in, check_out):
    response = request_booking(client, headers, listing_id, check_in, check_out)
    assert response.status_code == 201
    return response.json()


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code
