"""Модульні тести правил бронювання, що залежать від часу (lab5-scope.md, п. 10).

Годинник сервісного шару підмінено (фікстура `clock`); дії виконуються через API,
очікування — зі spec/srs.md і spec/bdd/booking.feature. Час — Europe/Kyiv.
"""
from tests.unit.conftest import assert_problem, book, request_booking


def test_checkin_too_soon_boundary(client, clock, guest, other_guest, make_listing):
    """FR-07; AC-07.2 (до моменту заїзду рівно 1 год — запит створюється; на 1 хв менше — CHECKIN_TOO_SOON)."""
    listing = make_listing()

    clock.set("2027-06-10 13:00")
    assert request_booking(client, guest, listing["id"], "2027-06-10", "2027-06-12").status_code == 201

    clock.set("2027-06-10 13:01")
    response = request_booking(client, other_guest, listing["id"], "2027-06-10", "2027-06-12")
    assert_problem(response, 422, "CHECKIN_TOO_SOON")


def test_checkin_too_soon_precedes_dates_unavailable(client, clock, host, guest, other_guest, make_listing):
    """FR-07 (порядок: CHECKIN_TOO_SOON №5 перевіряється раніше за DATES_UNAVAILABLE №6)."""
    listing = make_listing()
    b = book(client, guest, listing["id"], "2027-06-10", "2027-06-12")
    assert client.post(f"/bookings/{b['id']}/confirm", headers=host).status_code == 200

    clock.set("2027-06-10 13:30")
    response = request_booking(client, other_guest, listing["id"], "2027-06-10", "2027-06-11")

    assert_problem(response, 422, "CHECKIN_TOO_SOON")


def test_decision_deadline_is_24_hours_after_creation(client, clock, guest, make_listing):
    """FR-10 (строк рішення — момент створення + 24 год, якщо він раніший за момент заїзду)."""
    clock.set("2027-06-05 14:00")

    created = book(client, guest, make_listing()["id"], "2027-06-10", "2027-06-12")

    assert created["decisionDeadline"] == "2027-06-06T14:00:00+03:00"
    assert created["checkInAt"] == "2027-06-10T14:00:00+03:00"
    assert created["checkOutAt"] == "2027-06-12T11:00:00+03:00"


def test_decision_deadline_is_check_in_when_earlier(client, clock, guest, make_listing):
    """FR-10 (строк рішення — момент заїзду, якщо він раніший за створення + 24 год)."""
    clock.set("2027-06-10 11:00")

    created = book(client, guest, make_listing()["id"], "2027-06-10", "2027-06-12")

    assert created["decisionDeadline"] == "2027-06-10T14:00:00+03:00"


def test_pending_request_is_rejected_at_decision_deadline(client, clock, host, guest, make_listing):
    """FR-10; AC-10.1, AC-10.3, AC-09.5 (сценарій «Автоматичне відхилення після спливу строку рішення»).

    Операція повернення не перевіряється (lab5-scope.md, п. 5); повідомлення — поза обсягом.

    О 13:59 наступного дня запит у PENDING, о 14:00 — REJECTED; підтвердити його вже неможливо.
    """
    clock.set("2027-06-05 14:00")
    created = book(client, guest, make_listing()["id"], "2027-06-10", "2027-06-12")

    clock.set("2027-06-06 13:59")
    assert client.get(f"/bookings/{created['id']}", headers=guest).json()["status"] == "PENDING"

    clock.set("2027-06-06 14:00")
    assert client.get(f"/bookings/{created['id']}", headers=guest).json()["status"] == "REJECTED"
    assert_problem(client.post(f"/bookings/{created['id']}/confirm", headers=host), 409, "STATE_CONFLICT")


def test_confirm_one_minute_before_deadline(client, clock, host, guest, make_listing):
    """FR-09, FR-10; AC-09.7, AC-10.3 (сценарій «Підтвердження за хвилину до спливу строку рішення»)."""
    clock.set("2027-06-05 14:00")
    created = book(client, guest, make_listing()["id"], "2027-06-10", "2027-06-12")

    clock.set("2027-06-06 13:59")
    assert client.post(f"/bookings/{created['id']}/confirm", headers=host).json()["status"] == "CONFIRMED"

    clock.set("2027-06-06 14:00")
    assert client.get(f"/bookings/{created['id']}", headers=guest).json()["status"] == "CONFIRMED"


def test_turnover_remains_after_completion(client, clock, host, guest, other_guest, make_listing):
    """FR-08, FR-11; AC-08.5, AC-12.3 (сценарій «Перерва не зникає після переходу бронювання в COMPLETED»).

    B.N = 1, виїзд 12.06 об 11:00: о 10:59 — CONFIRMED, об 11:00 — COMPLETED з доступним
    відгуком до моменту виїзду + 14 днів; запит на [12.06, 13.06) о 12:00 — DATES_UNAVAILABLE з B.
    """
    listing = make_listing(turnover=1)
    b = book(client, guest, listing["id"], "2027-06-10", "2027-06-12")
    assert client.post(f"/bookings/{b['id']}/confirm", headers=host).status_code == 200

    clock.set("2027-06-12 10:59")
    before = client.get(f"/bookings/{b['id']}", headers=guest).json()
    assert (before["status"], before["reviewDeadline"]) == ("CONFIRMED", None)

    clock.set("2027-06-12 11:00")
    after = client.get(f"/bookings/{b['id']}", headers=guest).json()
    assert after["status"] == "COMPLETED"
    assert after["reviewDeadline"] == "2027-06-26T11:00:00+03:00"

    clock.set("2027-06-12 12:00")
    response = request_booking(client, other_guest, listing["id"], "2027-06-12", "2027-06-13")
    assert_problem(response, 409, "DATES_UNAVAILABLE")
    assert response.json()["conflictingBookingIds"] == [b["id"]]


def test_cancel_at_and_after_check_in_moment_is_refused(client, clock, host, guest, make_listing):
    """FR-13; AC-13.4 (момент заїзду 14:00: скасування о 14:00 і о 14:01 — відмова і для гостя, і для власника).

    За хвилину до моменту заїзду скасування ще можливе (межа FR-13).
    """
    listing = make_listing()
    confirmed = book(client, guest, listing["id"], "2027-06-10", "2027-06-12")
    assert client.post(f"/bookings/{confirmed['id']}/confirm", headers=host).status_code == 200
    spare = book(client, guest, listing["id"], "2027-06-20", "2027-06-22")
    # Підтверджене, бо запит у PENDING на 20.06 уже було б автоматично відхилено (FR-10).
    assert client.post(f"/bookings/{spare['id']}/confirm", headers=host).status_code == 200

    for moment in ("2027-06-10 14:00", "2027-06-10 14:01"):
        clock.set(moment)
        for actor in (guest, host):
            assert_problem(client.post(f"/bookings/{confirmed['id']}/cancel", headers=actor), 409, "STATE_CONFLICT")
    assert client.get(f"/bookings/{confirmed['id']}", headers=guest).json()["status"] == "CONFIRMED"

    clock.set("2027-06-20 13:59")
    assert client.post(f"/bookings/{spare['id']}/cancel", headers=guest).status_code == 200


def test_cancel_completed_booking_is_refused(client, clock, host, guest, make_listing):
    """FR-13; AC-13.5 (частина про COMPLETED: завершене бронювання скасувати неможливо)."""
    b = book(client, guest, make_listing()["id"], "2027-06-10", "2027-06-12")
    assert client.post(f"/bookings/{b['id']}/confirm", headers=host).status_code == 200

    clock.set("2027-06-12 11:00")
    assert client.get(f"/bookings/{b['id']}", headers=guest).json()["status"] == "COMPLETED"

    assert_problem(client.post(f"/bookings/{b['id']}/cancel", headers=guest), 409, "STATE_CONFLICT")
