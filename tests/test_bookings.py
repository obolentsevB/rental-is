"""API-тести операцій Bookings (api/openapi.yaml, тег Bookings).

Обсяг і обмеження — logs/lab5-scope.md. Шляхи, коди відповідей і поля
взято лише з api/openapi.yaml; вимоги й AC — зі spec/srs.md (v1.1).
Дати — у далекому майбутньому, щоб не спрацьовувала CHECKIN_TOO_SOON (FR-07 №5).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from src.main import app

# Мінімальний PNG 1×1: формат PNG дозволений FR-02, розмір значно менший за 5 242 880 байтів.
PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(monkeypatch):
    """Засіває in-memory сховище токенів {token → userId, role} (lab5-scope.md, п. 11).

    Єдине місце, що спирається на реалізацію: розташування сховища `src.auth.TOKENS`.
    Ролі — значення `User.roles` з api/openapi.yaml.
    """
    from src import auth as auth_module

    def make(role):
        token = f"test-{role.lower()}-{uuid.uuid4()}"
        monkeypatch.setitem(auth_module.TOKENS, token, {"userId": str(uuid.uuid4()), "role": role})
        return {"Authorization": f"Bearer {token}"}

    return make


@pytest.fixture
def owner(auth):
    return auth("HOST")


@pytest.fixture
def guest(auth):
    return auth("GUEST")


@pytest.fixture
def other_guest(auth):
    return auth("GUEST")


@pytest.fixture
def listing(client, owner):
    """Житло з передумови spec/bdd/booking.feature: 1 234,56 грн за ніч, до 4 осіб, перерва 0."""
    body = {
        "title": "Поділ",
        "city": "Київ",
        "address": "вул. Сагайдачного, 1",
        "maxGuests": 4,
        "pricePerNight": "1234.56",
        "photos": [{"data": PNG_1X1}],
        "checkInTime": "14:00",
        "checkOutTime": "11:00",
        "turnoverNights": 0,
    }
    response = client.post("/listings", json=body, headers=owner)
    assert response.status_code == 201
    return response.json()


def booking_request(listing_id, check_in, check_out, guests_count=2):
    return {"listingId": listing_id, "checkIn": check_in, "checkOut": check_out, "guestsCount": guests_count}


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


def test_create_booking_returns_201(client, guest, listing):
    """FR-06, FR-15; AC-06.1 (PENDING із вказаними датами й кількістю осіб), AC-15.1 (суми).

    3 ночі × 1 234,56 при комісії 10% (параметр платформи, SRS §5): вартість 3 703,68,
    комісія 370,36, передоплата 4 074,04. Операція оплати не перевіряється (lab5-scope.md, п. 5).
    """
    body = booking_request(listing["id"], "2030-06-09", "2030-06-12")

    response = client.post("/bookings", json=body, headers=guest)

    assert response.status_code == 201
    data = response.json()
    uuid.UUID(data["id"])
    assert data["listingId"] == listing["id"]
    assert data["checkIn"] == "2030-06-09"
    assert data["checkOut"] == "2030-06-12"
    assert data["guestsCount"] == 2
    assert data["status"] == "PENDING"
    assert data["checkInTime"] == "14:00"
    assert data["checkOutTime"] == "11:00"
    assert data["turnoverNights"] == 0
    assert data["commissionRate"] == 10
    assert data["accommodationCost"] == "3703.68"
    assert data["commission"] == "370.36"
    assert data["prepayment"] == "4074.04"
    assert data["cancelledBy"] is None
    assert data["cancelledAt"] is None
    assert data["reviewDeadline"] is None


@pytest.mark.parametrize(
    "check_in, check_out",
    [("2030-06-10", "2030-06-10"), ("2030-06-12", "2030-06-10")],
    ids=["checkout-equals-checkin", "checkout-before-checkin"],
)
def test_create_booking_checkout_not_after_checkin_returns_422(client, guest, listing, check_in, check_out):
    """FR-07; AC-07.1 (підстава №1: кількість ночей менша за 1 — MIN_NIGHTS).

    Схема не обмежує порядок дат, тому код — MIN_NIGHTS, а не VALIDATION_FAILED (createBooking).
    """
    response = client.post("/bookings", json=booking_request(listing["id"], check_in, check_out), headers=guest)

    assert_problem(response, 422, "MIN_NIGHTS")


def test_create_booking_with_max_guests_returns_201(client, guest, listing):
    """FR-07; AC-07.3 (кількість осіб, що дорівнює максимальній, приймається)."""
    body = booking_request(listing["id"], "2030-06-10", "2030-06-12", guests_count=listing["maxGuests"])

    response = client.post("/bookings", json=body, headers=guest)

    assert response.status_code == 201
    assert response.json()["guestsCount"] == listing["maxGuests"]


def test_create_booking_above_max_guests_returns_422(client, guest, listing):
    """FR-07; AC-07.3 (на 1 більше за максимальну — GUESTS_OUT_OF_RANGE)."""
    body = booking_request(listing["id"], "2030-06-10", "2030-06-12", guests_count=listing["maxGuests"] + 1)

    response = client.post("/bookings", json=body, headers=guest)

    assert_problem(response, 422, "GUESTS_OUT_OF_RANGE")


def test_create_booking_unknown_listing_returns_404(client, guest):
    """FR-06; AC — немає: відповідь 404 NOT_FOUND визначена контрактом createBooking."""
    body = booking_request(str(uuid.uuid4()), "2030-06-10", "2030-06-12")

    response = client.post("/bookings", json=body, headers=guest)

    assert_problem(response, 404, "NOT_FOUND")


def test_create_booking_overlapping_confirmed_returns_409(client, owner, guest, other_guest, listing):
    """FR-08, FR-07; AC-08.2 (спільна ніч із бронюванням B у CONFIRMED — відмова з ідентифікатором B).

    Сценарій «Відмова через спільну ніч із кодом DATES_UNAVAILABLE» (booking.feature).
    Запис журналу й причина не перевіряються (lab5-scope.md, п. 9).
    """
    b = client.post("/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=guest)
    assert b.status_code == 201
    confirmed = client.post(f"/bookings/{b.json()['id']}/confirm", headers=owner)
    assert confirmed.status_code == 200

    response = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-11", "2030-06-13"), headers=other_guest
    )

    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert response.json()["conflictingBookingIds"] == [b.json()["id"]]


def test_get_booking_returns_200(client, guest, listing):
    """FR-12; AC-12.5 (позитивна частина: гість бачить власне бронювання)."""
    created = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=guest
    ).json()

    response = client.get(f"/bookings/{created['id']}", headers=guest)

    assert response.status_code == 200
    assert response.json() == created


def test_cancel_booking_returns_200(client, guest, listing):
    """FR-13 (гість скасовує свій запит у PENDING); AC-13.6 (ініціатор GUEST).

    AC-13.2 (p = 100% для PENDING) тут не перевіряється: p у відповіді відсутня,
    її перевіряє модульний тест (lab5-scope.md, п. 6).
    """
    created = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=guest
    ).json()

    response = client.post(f"/bookings/{created['id']}/cancel", headers=guest)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["status"] == "CANCELLED"
    assert data["cancelledBy"] == "GUEST"
    assert data["cancelledAt"] is not None
