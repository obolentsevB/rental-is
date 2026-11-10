"""API-тести операцій Bookings (api/openapi.yaml, тег Bookings).

Обсяг і обмеження — logs/lab5-scope.md. Шляхи, коди відповідей і поля
взято лише з api/openapi.yaml; вимоги й AC — зі spec/srs.md (v1.1).
Дати — у далекому майбутньому, щоб не спрацьовувала CHECKIN_TOO_SOON (FR-07 №5).
Перевірки, що залежать від годинника, — у tests/unit/.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

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
def host(auth):
    return auth("HOST")


@pytest.fixture
def other_host(auth):
    return auth("HOST")


@pytest.fixture
def guest(auth):
    return auth("GUEST")


@pytest.fixture
def other_guest(auth):
    return auth("GUEST")


@pytest.fixture
def moderator(auth):
    return auth("MODERATOR")


LISTING_BODY = {
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


def create_listing(client, headers, **overrides):
    response = client.post("/listings", json={**LISTING_BODY, **overrides}, headers=headers)
    assert response.status_code == 201
    return response.json()


def change_listing(client, headers, listing, **overrides):
    """Повна заміна картки (replaceListing) зі збереженням наявної фотографії."""
    body = {**LISTING_BODY, "photos": [{"id": listing["photos"][0]["id"]}], **overrides}
    response = client.put(f"/listings/{listing['id']}", json=body, headers=headers)
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def listing(client, host):
    """Житло з передумови spec/bdd/booking.feature: 1 234,56 грн за ніч, до 4 осіб, перерва 0."""
    return create_listing(client, host)


def booking_request(listing_id, check_in, check_out, guests_count=2):
    return {"listingId": listing_id, "checkIn": check_in, "checkOut": check_out, "guestsCount": guests_count}


def book(client, headers, listing_id, check_in, check_out, guests_count=2):
    response = client.post(
        "/bookings", json=booking_request(listing_id, check_in, check_out, guests_count), headers=headers
    )
    assert response.status_code == 201
    return response.json()


def confirm(client, headers, booking_id):
    response = client.post(f"/bookings/{booking_id}/confirm", headers=headers)
    assert response.status_code == 200
    return response.json()


def status_of(client, headers, booking_id):
    response = client.get(f"/bookings/{booking_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["status"]


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


# --- createBooking: створення і фіксація умов -----------------------------------


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


def test_two_guests_pending_on_same_nights(client, guest, other_guest, listing):
    """FR-06; AC-06.2 (два гості послідовно створюють запити на ті самі ночі — обидва PENDING)."""
    first = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    second = book(client, other_guest, listing["id"], "2030-06-10", "2030-06-12")

    assert first["status"] == second["status"] == "PENDING"


def test_booking_keeps_terms_after_listing_change(client, host, guest, listing):
    """FR-06; AC-06.4 (API-частина: після зміни житла бронювання зберігає 0, 14:00 і 11:00).

    Момент заїзду й виїзду та строк рішення рахуються від зафіксованих значень;
    шкала повернення — у модульних тестах (lab5-scope.md, п. 6).
    """
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    change_listing(client, host, listing, turnoverNights=1, checkInTime="16:00", checkOutTime="10:00")

    response = client.get(f"/bookings/{created['id']}", headers=guest)
    assert response.status_code == 200
    data = response.json()
    assert (data["turnoverNights"], data["checkInTime"], data["checkOutTime"]) == (0, "14:00", "11:00")
    assert data["checkInAt"] == "2030-06-10T14:00:00+03:00"
    assert data["checkOutAt"] == "2030-06-12T11:00:00+03:00"
    assert data["decisionDeadline"] == created["decisionDeadline"]


def test_new_request_after_turnover_change_on_previous_checkout(client, host, guest, other_guest, listing):
    """FR-06, FR-08; AC-06.5 (після зміни перерви житла на 1 запит із заїздом у день виїзду B з N=0 створюється)."""
    b = confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])
    assert b["turnoverNights"] == 0

    change_listing(client, host, listing, turnoverNights=1)

    created = book(client, other_guest, listing["id"], "2030-06-12", "2030-06-14")
    assert created["turnoverNights"] == 1


def test_confirmed_booking_keeps_terms_from_creation(client, host, guest, listing):
    """FR-06; AC-06.7 (створене до зміни налаштувань і підтверджене після неї зберігає значення на момент створення)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    change_listing(client, host, listing, turnoverNights=1, checkInTime="16:00", checkOutTime="10:00")

    confirmed = confirm(client, host, created["id"])

    assert confirmed["status"] == "CONFIRMED"
    for field in ("turnoverNights", "checkInTime", "checkOutTime", "checkInAt", "checkOutAt", "commissionRate"):
        assert confirmed[field] == created[field]


# --- createBooking: підстави FR-07 і їхній порядок ------------------------------


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


def test_create_booking_own_listing_returns_403(client, host, listing):
    """FR-07; AC-07.1 (підстава №2: гість є власником цього житла — OWN_LISTING)."""
    response = client.post("/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=host)

    assert_problem(response, 403, "OWN_LISTING")


def test_create_booking_with_zero_guests_returns_422(client, guest, listing):
    """FR-07; AC-07.1 (підстава №3: кількість осіб менша за 1 — GUESTS_OUT_OF_RANGE)."""
    body = booking_request(listing["id"], "2030-06-10", "2030-06-12", guests_count=0)

    assert_problem(client.post("/bookings", json=body, headers=guest), 422, "GUESTS_OUT_OF_RANGE")


def test_create_booking_with_past_check_in_returns_422(client, guest, listing):
    """FR-07; AC-07.1 (підстава №5: дата заїзду минула — CHECKIN_TOO_SOON).

    Межа «рівно 1 год» залежить від годинника й перевіряється в tests/unit/ (AC-07.2).
    """
    body = booking_request(listing["id"], "2020-06-10", "2020-06-12")

    assert_problem(client.post("/bookings", json=body, headers=guest), 422, "CHECKIN_TOO_SOON")


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


@pytest.mark.parametrize(
    "who, unpublished, check_in, check_out, guests_count, status, code",
    [
        ("host", False, "2030-06-10", "2030-06-10", 0, 422, "MIN_NIGHTS"),
        ("host", False, "2030-06-10", "2030-06-12", 0, 403, "OWN_LISTING"),
        ("guest", True, "2030-06-10", "2030-06-12", 5, 422, "GUESTS_OUT_OF_RANGE"),
        ("guest", True, "2020-06-10", "2020-06-12", 2, 409, "LISTING_UNPUBLISHED"),
        ("host", True, "2030-06-10", "2030-06-12", 2, 403, "OWN_LISTING"),
    ],
    ids=[
        "min-nights-before-own-listing",
        "own-listing-before-guests",
        "guests-before-unpublished",
        "unpublished-before-checkin-too-soon",
        "AC-07.4-own-unpublished-listing",
    ],
)
def test_fr07_checks_order(
    client, host, guest, moderator, listing, who, unpublished, check_in, check_out, guests_count, status, code
):
    """FR-07 (порядок перевірок: повертається перший код, що спрацював); AC-07.1, AC-07.4.

    Кожен рядок порушує дві сусідні підстави; очікується код раніший за порядком.
    CHECKIN_TOO_SOON перед DATES_UNAVAILABLE — у tests/unit/ (потрібен годинник).
    """
    if unpublished:
        response = client.post(
            f"/listings/{listing['id']}/unpublish", json={"reason": "Перевірка порядку."}, headers=moderator
        )
        assert response.status_code == 200
    headers = host if who == "host" else guest

    response = client.post(
        "/bookings", json=booking_request(listing["id"], check_in, check_out, guests_count), headers=headers
    )

    assert_problem(response, status, code)


@pytest.mark.parametrize(
    "actor, check_in, check_out, guests_count, status, code",
    [
        ("guest", "2030-06-10", "2030-06-10", 2, 422, "MIN_NIGHTS"),
        ("host", "2030-06-10", "2030-06-12", 2, 403, "OWN_LISTING"),
        ("guest", "2030-06-10", "2030-06-12", 5, 422, "GUESTS_OUT_OF_RANGE"),
        ("guest", "2030-06-10", "2030-06-12", 2, 409, "LISTING_UNPUBLISHED"),
        ("guest", "2020-06-10", "2020-06-12", 2, 422, "CHECKIN_TOO_SOON"),
        ("guest", "2030-06-11", "2030-06-13", 2, 409, "DATES_UNAVAILABLE"),
    ],
    ids=["MIN_NIGHTS", "OWN_LISTING", "GUESTS_OUT_OF_RANGE", "LISTING_UNPUBLISHED", "CHECKIN_TOO_SOON", "DATES_UNAVAILABLE"],
)
def test_refused_request_creates_no_booking(
    client, host, guest, other_guest, moderator, listing, actor, check_in, check_out, guests_count, status, code
):
    """FR-07; AC-07.1 (після відмови за підставами 1–6 бронювання не з'являється).

    Підстава 0 (ACCOUNT_BLOCKED) не моделюється, платіжні операції не створюються (lab5-scope.md, пп. 5, 11).
    """
    if code == "LISTING_UNPUBLISHED":
        response = client.post(f"/listings/{listing['id']}/unpublish", json={"reason": "Перевірка."}, headers=moderator)
        assert response.status_code == 200
    if code == "DATES_UNAVAILABLE":
        confirm(client, host, book(client, other_guest, listing["id"], "2030-06-10", "2030-06-12")["id"])

    def bookings_of_listing():
        return sorted(item["id"] for item in client.get("/bookings", params={"role": "owner"}, headers=host).json())

    before = bookings_of_listing()
    headers = host if actor == "host" else guest

    response = client.post(
        "/bookings", json=booking_request(listing["id"], check_in, check_out, guests_count), headers=headers
    )

    assert_problem(response, status, code)
    assert bookings_of_listing() == before


# --- createBooking: доступність (FR-08) ------------------------------------------


def test_create_booking_overlapping_confirmed_returns_409(client, host, guest, other_guest, listing):
    """FR-08, FR-07; AC-08.2 (спільна ніч із бронюванням B у CONFIRMED — відмова з ідентифікатором B).

    Сценарій «Відмова через спільну ніч із кодом DATES_UNAVAILABLE» (booking.feature).
    Запис журналу й причина не перевіряються (lab5-scope.md, п. 9).
    """
    b = client.post("/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=guest)
    assert b.status_code == 201
    confirmed = client.post(f"/bookings/{b.json()['id']}/confirm", headers=host)
    assert confirmed.status_code == 200

    response = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-11", "2030-06-13"), headers=other_guest
    )

    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert response.json()["conflictingBookingIds"] == [b.json()["id"]]


def test_check_in_on_previous_checkout_is_created(client, host, guest, other_guest, listing):
    """FR-08; AC-08.1 (B у CONFIRMED на [10.06, 12.06), N=0: запит на [12.06, 14.06) створюється)."""
    confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])

    created = book(client, other_guest, listing["id"], "2030-06-12", "2030-06-14")

    assert created["status"] == "PENDING"


def test_night_in_booking_turnover_returns_409(client, host, guest, other_guest):
    """FR-08; AC-08.3 (B.N = 1: запит на [12.06, 13.06) — відмова з ідентифікатором B).

    Причина «потрапляння в перерву» є лише в журналі (lab5-scope.md, п. 9).
    """
    listing = create_listing(client, host, turnoverNights=1)
    b = confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])

    response = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-12", "2030-06-13"), headers=other_guest
    )

    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert response.json()["conflictingBookingIds"] == [b["id"]]


def test_new_request_turnover_covering_check_in_returns_409(client, host, guest, other_guest, listing):
    """FR-08; AC-08.4 (N житла = 1, B.N = 0: запит на [08.06, 10.06) — відмова, перерва нового запиту накриває заїзд B)."""
    b = confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])
    change_listing(client, host, listing, turnoverNights=1)

    response = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-08", "2030-06-10"), headers=other_guest
    )

    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert response.json()["conflictingBookingIds"] == [b["id"]]


def test_pending_request_does_not_block_same_nights(client, guest, other_guest, listing):
    """FR-08; AC-08.7 (на житло є лише запит у PENDING на [10.06, 12.06) — новий запит на ті самі ночі створюється)."""
    book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    created = book(client, other_guest, listing["id"], "2030-06-10", "2030-06-12")

    assert created["status"] == "PENDING"


def test_night_after_turnover_is_available(client, host, guest, other_guest):
    """FR-08; AC-08.9 (B.N = 1: запит на [13.06, 15.06) створюється)."""
    listing = create_listing(client, host, turnoverNights=1)
    confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])

    created = book(client, other_guest, listing["id"], "2030-06-13", "2030-06-15")

    assert created["status"] == "PENDING"


def test_conflict_with_two_bookings_lists_both_ids(client, host, auth, listing):
    """FR-08; AC — немає: Problem.conflictingBookingIds містить усі бронювання конфлікту (K-110).

    Відповідна частина AC-08.8 стосується журналу і до обсягу не входить (lab5-scope.md, п. 9).
    """
    b1 = confirm(client, host, book(client, auth("GUEST"), listing["id"], "2030-06-10", "2030-06-12")["id"])
    b2 = confirm(client, host, book(client, auth("GUEST"), listing["id"], "2030-06-13", "2030-06-15")["id"])

    response = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-11", "2030-06-14"), headers=auth("GUEST")
    )

    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert sorted(response.json()["conflictingBookingIds"]) == sorted([b1["id"], b2["id"]])


# --- createBooking: коди контракту ----------------------------------------------


def test_create_booking_unknown_listing_returns_404(client, guest):
    """FR-06; AC — немає: відповідь 404 NOT_FOUND визначена контрактом createBooking."""
    body = booking_request(str(uuid.uuid4()), "2030-06-10", "2030-06-12")

    response = client.post("/bookings", json=body, headers=guest)

    assert_problem(response, 404, "NOT_FOUND")


def test_create_booking_without_token_returns_401(client, listing):
    """FR-06; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом createBooking."""
    response = client.post("/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"))

    assert_problem(response, 401, "UNAUTHENTICATED")


def test_create_booking_by_moderator_returns_403(client, moderator, listing):
    """FR-06; AC — немає: модератор не створює запитів — 403 FORBIDDEN (createBooking)."""
    body = booking_request(listing["id"], "2030-06-10", "2030-06-12")

    assert_problem(client.post("/bookings", json=body, headers=moderator), 403, "FORBIDDEN")


# --- listBookings / getBooking (FR-12) ------------------------------------------


def test_list_bookings_as_guest_returns_own_trips(client, host, guest, other_guest, listing):
    """FR-12; AC-12.1, AC-12.2 (API-частина), AC-12.5.

    Сервер повертає всі поїздки гостя, зокрема скасовані, з `checkOutAt`; групування на
    майбутні й минулі виконує клієнт (опис listBookings). Чужих бронювань немає.
    """
    active = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    cancelled = book(client, guest, listing["id"], "2030-07-10", "2030-07-12")
    assert client.post(f"/bookings/{cancelled['id']}/cancel", headers=guest).status_code == 200
    foreign = book(client, other_guest, listing["id"], "2030-08-10", "2030-08-12")

    response = client.get("/bookings", params={"role": "guest"}, headers=guest)

    assert response.status_code == 200
    trips = {item["id"]: item for item in response.json()}
    assert set(trips) == {active["id"], cancelled["id"]}
    assert trips[cancelled["id"]]["status"] == "CANCELLED"
    assert all(item["checkOutAt"] for item in trips.values())
    assert foreign["id"] not in trips


def test_list_bookings_as_owner_returns_own_listing_requests(client, host, other_host, guest, listing):
    """FR-12; AC-12.4 (власник бачить запити свого житла зі статусом; дії — у клієнті), AC-12.5."""
    own = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    other_listing = create_listing(client, other_host)
    foreign = book(client, guest, other_listing["id"], "2030-06-10", "2030-06-12")

    response = client.get("/bookings", params={"role": "owner"}, headers=host)

    assert response.status_code == 200
    ids = {item["id"]: item["status"] for item in response.json()}
    assert ids == {own["id"]: "PENDING"}
    assert foreign["id"] not in ids


def test_list_bookings_without_role_returns_422(client, guest):
    """FR-12; AC — немає: без параметра role — 422 VALIDATION_FAILED (listBookings)."""
    assert_problem(client.get("/bookings", headers=guest), 422, "VALIDATION_FAILED")


def test_list_bookings_without_token_returns_401(client):
    """FR-12; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом listBookings."""
    assert_problem(client.get("/bookings", params={"role": "guest"}), 401, "UNAUTHENTICATED")


def test_list_bookings_by_moderator_returns_403(client, moderator):
    """FR-12; AC — немає: запит модератора — 403 FORBIDDEN (listBookings)."""
    assert_problem(client.get("/bookings", params={"role": "guest"}, headers=moderator), 403, "FORBIDDEN")


def test_get_booking_returns_200(client, guest, listing):
    """FR-12; AC-12.5 (позитивна частина: гість бачить власне бронювання)."""
    created = client.post(
        "/bookings", json=booking_request(listing["id"], "2030-06-10", "2030-06-12"), headers=guest
    ).json()

    response = client.get(f"/bookings/{created['id']}", headers=guest)

    assert response.status_code == 200
    assert response.json() == created


def test_get_booking_visible_to_listing_host(client, host, guest, listing):
    """FR-12; AC — немає: бронювання доступне власнику житла (опис getBooking)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    response = client.get(f"/bookings/{created['id']}", headers=host)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_foreign_booking_returns_404(client, guest, other_guest, other_host, listing):
    """FR-12; AC-12.5 (негативна частина: бронювання іншого гостя або іншого житла не показуються).

    Для інших користувачів бронювання не існує — NOT_FOUND (getBooking).
    """
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    for headers in (other_guest, other_host):
        assert_problem(client.get(f"/bookings/{created['id']}", headers=headers), 404, "NOT_FOUND")


def test_get_unknown_booking_returns_404(client, guest):
    """FR-12; AC — немає: відповідь 404 NOT_FOUND визначена контрактом getBooking."""
    assert_problem(client.get(f"/bookings/{uuid.uuid4()}", headers=guest), 404, "NOT_FOUND")


def test_get_booking_without_token_returns_401(client, guest, listing):
    """FR-12; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом getBooking."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    assert_problem(client.get(f"/bookings/{created['id']}"), 401, "UNAUTHENTICATED")


# --- confirmBooking / rejectBooking (FR-09) -------------------------------------


def test_confirm_single_pending_returns_200(client, host, guest, listing):
    """FR-09; AC-09.7 (підтвердження єдиного запиту в PENDING переводить його в CONFIRMED)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    response = client.post(f"/bookings/{created['id']}/confirm", headers=host)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["status"] == "CONFIRMED"


@pytest.mark.parametrize("turnover_a, status_d", [(0, "PENDING"), (1, "REJECTED")], ids=["AC-09.1", "AC-09.2"])
def test_confirm_rejects_incompatible_pending(client, host, auth, listing, turnover_a, status_d):
    """FR-09; AC-09.1 (частково), AC-09.2.

    A [10, 12), C [11, 13), D [12, 14) у PENDING; C і D — з N = 0, A — з N = turnover_a.
    Після підтвердження A: C — REJECTED, D — PENDING при N(A)=0 і REJECTED при N(A)=1.
    Операції повернення не перевіряються (lab5-scope.md, п. 5).
    """
    guest_a, guest_c, guest_d = auth("GUEST"), auth("GUEST"), auth("GUEST")
    change_listing(client, host, listing, turnoverNights=turnover_a)
    a = book(client, guest_a, listing["id"], "2030-06-10", "2030-06-12")
    change_listing(client, host, listing, turnoverNights=0)
    c = book(client, guest_c, listing["id"], "2030-06-11", "2030-06-13")
    d = book(client, guest_d, listing["id"], "2030-06-12", "2030-06-14")
    assert a["turnoverNights"] == turnover_a

    assert confirm(client, host, a["id"])["status"] == "CONFIRMED"

    assert status_of(client, guest_c, c["id"]) == "REJECTED"
    assert status_of(client, guest_d, d["id"]) == status_d


def test_reject_pending_returns_200(client, host, guest, listing):
    """FR-09; AC-09.3 (частково: після відхилення запит має статус REJECTED; операція повернення — ні)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    response = client.post(f"/bookings/{created['id']}/reject", headers=host)

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


@pytest.mark.parametrize("action", ["confirm", "reject"])
@pytest.mark.parametrize("actor", ["guest", "other_host"])
def test_decision_by_non_owner_returns_403(client, guest, other_host, listing, action, actor):
    """FR-09; AC-09.4 (користувач, який не є власником житла, не може підтвердити чи відхилити запит)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    headers = guest if actor == "guest" else other_host

    response = client.post(f"/bookings/{created['id']}/{action}", headers=headers)

    assert_problem(response, 403, "FORBIDDEN")
    assert status_of(client, guest, created["id"]) == "PENDING"


@pytest.mark.parametrize("action", ["confirm", "reject"])
@pytest.mark.parametrize("previous", ["confirm", "reject"])
def test_decision_on_non_pending_returns_409(client, host, guest, listing, action, previous):
    """FR-09; AC-09.5 (бронювання, яке вже не в PENDING, підтвердити неможливо); те саме для reject (rejectBooking)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    assert client.post(f"/bookings/{created['id']}/{previous}", headers=host).status_code == 200

    response = client.post(f"/bookings/{created['id']}/{action}", headers=host)

    assert_problem(response, 409, "STATE_CONFLICT")


@pytest.mark.parametrize("action", ["confirm", "reject"])
def test_decision_on_unknown_booking_returns_404(client, host, action):
    """FR-09; AC — немає: відповідь 404 NOT_FOUND визначена контрактом confirmBooking і rejectBooking."""
    assert_problem(client.post(f"/bookings/{uuid.uuid4()}/{action}", headers=host), 404, "NOT_FOUND")


@pytest.mark.parametrize("action", ["confirm", "reject"])
def test_decision_without_token_returns_401(client, guest, listing, action):
    """FR-09; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом confirmBooking і rejectBooking."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    assert_problem(client.post(f"/bookings/{created['id']}/{action}"), 401, "UNAUTHENTICATED")


@pytest.mark.parametrize("k", [2, 5, 10])
def test_parallel_confirmations_leave_one_confirmed(host, auth, k):
    """NFR-01, FR-09; AC-N01.1 (частково), AC-N01.3.

    Паралельне підтвердження k несумісних запитів, 100 повторів: щоразу рівно один
    CONFIRMED (200), решта REJECTED (409 STATE_CONFLICT за описом confirmBooking).
    Після прогону жодна пара бронювань у CONFIRMED чи COMPLETED не конфліктує.
    Повернення 100% не перевіряється (lab5-scope.md, п. 5).
    """
    client = TestClient(app)
    guests = [auth("GUEST") for _ in range(k)]
    for _ in range(100):
        listing = create_listing(client, host)
        requests = [book(client, headers, listing["id"], "2030-06-10", "2030-06-12") for headers in guests]

        def confirm_one(booking):
            return TestClient(app).post(f"/bookings/{booking['id']}/confirm", headers=host).status_code

        with ThreadPoolExecutor(max_workers=k) as pool:
            codes = list(pool.map(confirm_one, requests))

        assert sorted(codes) == [200] + [409] * (k - 1)
        statuses = [status_of(client, headers, r["id"]) for headers, r in zip(guests, requests)]
        assert sorted(statuses) == ["CONFIRMED"] + ["REJECTED"] * (k - 1)

    occupied = [
        item
        for item in client.get("/bookings", params={"role": "owner"}, headers=host).json()
        if item["status"] in ("CONFIRMED", "COMPLETED")
    ]
    for i, first in enumerate(occupied):
        for second in occupied[i + 1:]:
            if first["listingId"] != second["listingId"]:
                continue
            assert not _overlap(first, second), (first["id"], second["id"])


def _overlap(a, b):
    """Умова (2) FR-08 між двома бронюваннями з перервами, зафіксованими в кожному."""
    a_in, a_out = date.fromisoformat(a["checkIn"]), date.fromisoformat(a["checkOut"])
    b_in, b_out = date.fromisoformat(b["checkIn"]), date.fromisoformat(b["checkOut"])
    return (
        a_in < b_out + timedelta(days=b["turnoverNights"])
        and b_in < a_out + timedelta(days=a["turnoverNights"])
    )


# --- cancelBooking (FR-13) ------------------------------------------------------


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


def test_host_cancels_confirmed_booking(client, host, guest, listing):
    """FR-13 (власник скасовує бронювання свого житла в CONFIRMED; ініціатор фіксується)."""
    created = confirm(client, host, book(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"])

    response = client.post(f"/bookings/{created['id']}/cancel", headers=host)

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancelledBy"] == "HOST"


@pytest.mark.parametrize("final", ["reject", "cancel"])
def test_cancel_finished_booking_returns_409(client, host, guest, listing, final):
    """FR-13; AC-13.5 (API-частина: REJECTED і CANCELLED скасувати неможливо; COMPLETED — у tests/unit/)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    actor = host if final == "reject" else guest
    assert client.post(f"/bookings/{created['id']}/{final}", headers=actor).status_code == 200

    assert_problem(client.post(f"/bookings/{created['id']}/cancel", headers=guest), 409, "STATE_CONFLICT")


def test_cancel_foreign_booking_returns_404(client, guest, other_guest, listing):
    """FR-13; AC — немає: для стороннього користувача бронювання не існує — 404 NOT_FOUND (cancelBooking)."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    assert_problem(client.post(f"/bookings/{created['id']}/cancel", headers=other_guest), 404, "NOT_FOUND")
    assert status_of(client, guest, created["id"]) == "PENDING"


def test_cancel_unknown_booking_returns_404(client, guest):
    """FR-13; AC — немає: відповідь 404 NOT_FOUND визначена контрактом cancelBooking."""
    assert_problem(client.post(f"/bookings/{uuid.uuid4()}/cancel", headers=guest), 404, "NOT_FOUND")


def test_cancel_without_token_returns_401(client, guest, listing):
    """FR-13; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом cancelBooking."""
    created = book(client, guest, listing["id"], "2030-06-10", "2030-06-12")

    assert_problem(client.post(f"/bookings/{created['id']}/cancel"), 401, "UNAUTHENTICATED")
