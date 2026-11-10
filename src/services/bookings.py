"""Сервісний шар бронювань (FR-06–FR-13, FR-15).

Обсяг — logs/lab5-scope.md: закритих ночей немає (пп. 2, 4), платіжні операції
не створюються (п. 5), частка повернення p розраховується тут і в API не
виходить (п. 6). FR-10 і FR-11 застосовуються ліниво перед кожною дією за
годинником `now`, який модульні тести підміняють (п. 10).
"""

import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from zoneinfo import ZoneInfo

from src import repository
from src.errors import ProblemError, not_found

KYIV = ZoneInfo("Europe/Kyiv")
CENT = Decimal("0.01")

# Параметри платформи (SRS §5, NFR-10): змінюються лише в конфігурації.
COMMISSION_RATE = Decimal("10")
MIN_TIME_BEFORE_CHECKIN = timedelta(hours=1)
DECISION_PERIOD = timedelta(hours=24)
REVIEW_PERIOD = timedelta(days=14)

LOCK = threading.RLock()  # NFR-01: дії над бронюваннями виконуються послідовно


def now() -> datetime:
    """Повертає поточний момент у часовому поясі Europe/Kyiv.

    Єдине джерело часу сервісу: модульні тести підміняють цю функцію (lab5-scope.md, п. 10).

    Returns:
        Поточний момент із часовим поясом.
    """
    return datetime.now(KYIV)


# --- Розрахунки -----------------------------------------------------------------


def moment(night: date, clock_time: str) -> datetime:
    """Поєднує дату з часом доби в момент заїзду чи виїзду.

    Args:
        night: Дата заїзду або виїзду.
        clock_time: Час доби у форматі `ГГ:ХХ`.

    Returns:
        Момент у часовому поясі Europe/Kyiv.
    """
    hours, minutes = map(int, clock_time.split(":"))
    return datetime.combine(night, time(hours, minutes), tzinfo=KYIV)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def costs(
    nights: int, price_per_night: Decimal, commission_rate: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Обчислює суми запиту на бронювання (FR-15).

    Args:
        nights: Кількість ночей.
        price_per_night: Ціна за ніч.
        commission_rate: Відсоток комісії.

    Returns:
        Вартість проживання, комісію, округлену вниз до 0,01, і передоплату.
    """
    accommodation_cost = nights * price_per_night
    commission = (accommodation_cost * commission_rate / 100).quantize(CENT, rounding=ROUND_FLOOR)
    return accommodation_cost, commission, accommodation_cost + commission


def refund_share(
    cancelled_by: str, previous_status: str, cancelled_at: datetime, check_in_at: datetime
) -> int:
    """Визначає частку повернення p (FR-13).

    Args:
        cancelled_by: Ініціатор скасування; шкала діє лише для GUEST.
        previous_status: Статус бронювання до скасування.
        cancelled_at: Момент скасування.
        check_in_at: Момент заїзду.

    Returns:
        Частку у відсотках: 100, 50 або 0.
    """
    if cancelled_by != "GUEST" or previous_status == "PENDING":
        return 100
    hours_left = check_in_at - cancelled_at
    if hours_left >= timedelta(hours=168):
        return 100
    if hours_left >= timedelta(hours=72):
        return 50
    return 0


def refund(refund_rate: int, accommodation_cost: Decimal, commission: Decimal) -> Decimal:
    """Обчислює суму повернення (FR-15).

    Поки не викликається: платіжні операції поза обсягом Лаб 5 (lab5-scope.md, п. 5).

    Args:
        refund_rate: Частка повернення p у відсотках.
        accommodation_cost: Вартість проживання.
        commission: Комісія.

    Returns:
        Суму двох доданків, кожен округлено вгору до 0,01.
    """

    def part(amount: Decimal) -> Decimal:
        return (amount * refund_rate / 100).quantize(CENT, rounding=ROUND_CEILING)

    return part(accommodation_cost) + part(commission)


def _stay(booking: dict) -> tuple[date, date]:
    return date.fromisoformat(booking["checkIn"]), date.fromisoformat(booking["checkOut"])


def overlaps(check_in: date, check_out: date, turnover_nights: int, other: dict) -> bool:
    """Перевіряє умову конфлікту (2) FR-08 для двох діапазонів.

    Args:
        check_in: Дата заїзду перевірюваного діапазону.
        check_out: Дата виїзду перевірюваного діапазону.
        turnover_nights: Перерва N перевірюваного діапазону.
        other: Запис бронювання; його перерва береться із самого запису.

    Returns:
        True, якщо діапазони конфліктують.
    """
    other_in, other_out = _stay(other)
    return check_in < other_out + timedelta(
        days=other["turnoverNights"]
    ) and other_in < check_out + timedelta(days=turnover_nights)


# --- Стан у часі (FR-10, FR-11) -------------------------------------------------


def refresh(current: datetime) -> None:
    """Застосовує переходи статусів у часі (FR-10, FR-11).

    Запит після строку рішення переходить у REJECTED, а підтверджене бронювання в момент виїзду —
    у COMPLETED. Викликач має тримати `LOCK`.

    Args:
        current: Момент, на який оновлюється стан.
    """
    for booking in repository.all_bookings():
        if booking["status"] == "PENDING" and current >= booking["_decisionDeadline"]:
            booking["status"] = "REJECTED"
        elif booking["status"] == "CONFIRMED" and current >= booking["_checkOutAt"]:
            booking["status"] = "COMPLETED"
            booking["reviewDeadline"] = _iso(booking["_checkOutAt"] + REVIEW_PERIOD)


@contextmanager
def _fresh_state() -> Iterator[datetime]:
    """Виконує дію під блокуванням і зі станом, актуальним на поточний момент, який і повертає."""
    with LOCK:
        current = now()
        refresh(current)
        yield current


def conflicts(listing_id: str, check_in: date, check_out: date, turnover_nights: int) -> list[str]:
    """Шукає бронювання, через які діапазон недоступний (FR-08, умова 2).

    Враховуються лише бронювання в статусах CONFIRMED і COMPLETED.

    Args:
        listing_id: Ідентифікатор житла.
        check_in: Дата заїзду.
        check_out: Дата виїзду.
        turnover_nights: Перерва N перевірюваного діапазону.

    Returns:
        Ідентифікатори бронювань, що конфліктують із діапазоном.
    """
    return [
        booking["id"]
        for booking in repository.bookings_of_listing(listing_id)
        if booking["status"] in ("CONFIRMED", "COMPLETED")
        and overlaps(check_in, check_out, turnover_nights, booking)
    ]


def is_available(listing: dict, check_in: date, check_out: date) -> bool:
    """Виконує повну перевірку доступності для пошуку (FR-05).

    Перерву беруть чинну на момент пошуку. Закритих ночей немає (lab5-scope.md, п. 2).

    Args:
        listing: Запис житла.
        check_in: Дата заїзду.
        check_out: Дата виїзду.

    Returns:
        True, якщо житло доступне на весь діапазон.
    """
    with _fresh_state():
        return not conflicts(listing["id"], check_in, check_out, listing["turnoverNights"])


# --- Дії ------------------------------------------------------------------------


def _check_can_request(
    user: dict, listing: dict, check_in: date, check_out: date, guests_count: int, current: datetime
) -> None:
    """Перевірки FR-07 у порядку SRS: повертається перший код.

    ACCOUNT_BLOCKED (№0) не моделюється.
    """
    nights = (check_out - check_in).days
    if nights < 1:
        raise ProblemError(
            "MIN_NIGHTS", f"Діапазон [{check_in}, {check_out}) містить {max(nights, 0)} ночей."
        )
    if user["userId"] == listing["hostId"]:
        raise ProblemError("OWN_LISTING", "Не можна бронювати житло, власником якого ви є.")
    if not 1 <= guests_count <= listing["maxGuests"]:
        raise ProblemError(
            "GUESTS_OUT_OF_RANGE",
            f"Кількість осіб {guests_count} поза межами 1–{listing['maxGuests']}.",
        )
    if listing["status"] == "UNPUBLISHED":
        raise ProblemError(
            "LISTING_UNPUBLISHED", "Житло в стані Unpublished не приймає нових запитів."
        )
    check_in_at = moment(check_in, listing["checkInTime"])
    if check_in_at - current < MIN_TIME_BEFORE_CHECKIN:
        raise ProblemError(
            "CHECKIN_TOO_SOON", f"До моменту заїзду {_iso(check_in_at)} лишається менше 1 години."
        )
    conflicting = conflicts(listing["id"], check_in, check_out, listing["turnoverNights"])
    if conflicting:
        raise ProblemError(
            "DATES_UNAVAILABLE",
            f"Діапазон [{check_in}, {check_out}) не проходить повну перевірку доступності.",
            conflictingBookingIds=conflicting,
        )


def create(user: dict, listing_id: str, check_in: date, check_out: date, guests_count: int) -> dict:
    """Створює запит у PENDING із зафіксованими умовами житла (FR-06, FR-15).

    Args:
        user: Гість.
        listing_id: Ідентифікатор житла.
        check_in: Дата заїзду.
        check_out: Дата виїзду.
        guests_count: Кількість осіб.

    Returns:
        Збережений запис бронювання.

    Raises:
        ProblemError: NOT_FOUND, якщо житла немає, або перший код відмови FR-07: MIN_NIGHTS,
            OWN_LISTING, GUESTS_OUT_OF_RANGE, LISTING_UNPUBLISHED, CHECKIN_TOO_SOON,
            DATES_UNAVAILABLE.
    """
    listing = repository.get_listing(listing_id)
    if listing is None:
        raise ProblemError("NOT_FOUND", "Житла не існує.")
    with _fresh_state() as current:
        _check_can_request(user, listing, check_in, check_out, guests_count, current)

        nights = (check_out - check_in).days
        accommodation_cost, commission, prepayment = costs(
            nights, Decimal(listing["pricePerNight"]), COMMISSION_RATE
        )
        check_in_at = moment(check_in, listing["checkInTime"])
        check_out_at = moment(check_out, listing["checkOutTime"])
        decision_deadline = min(current + DECISION_PERIOD, check_in_at)
        return repository.save_booking(
            {
                "id": str(uuid.uuid4()),
                "listingId": listing["id"],
                "checkIn": check_in.isoformat(),
                "checkOut": check_out.isoformat(),
                "guestsCount": guests_count,
                "status": "PENDING",
                "checkInTime": listing["checkInTime"],
                "checkOutTime": listing["checkOutTime"],
                "turnoverNights": listing["turnoverNights"],
                "commissionRate": int(COMMISSION_RATE)
                if COMMISSION_RATE == COMMISSION_RATE.to_integral()
                else float(COMMISSION_RATE),
                "accommodationCost": str(accommodation_cost),
                "commission": str(commission),
                "prepayment": str(prepayment),
                "checkInAt": _iso(check_in_at),
                "checkOutAt": _iso(check_out_at),
                "decisionDeadline": _iso(decision_deadline),
                "cancelledBy": None,
                "cancelledAt": None,
                "reviewDeadline": None,
                # Службові поля (з префіксом _) у відповідь API не потрапляють.
                "_guestId": user["userId"],
                "_hostId": listing["hostId"],
                "_checkInAt": check_in_at,
                "_checkOutAt": check_out_at,
                "_decisionDeadline": decision_deadline,
                "_refundShare": None,
            }
        )


def _visible(booking_id: str, user: dict) -> dict:
    """Бронювання, доступне гостю або власнику житла; для інших — NOT_FOUND (getBooking)."""
    booking = repository.get_booking(booking_id)
    if booking is None or user["userId"] not in (booking["_guestId"], booking["_hostId"]):
        raise not_found()
    return booking


def get(booking_id: str, user: dict) -> dict:
    """Повертає бронювання гостю або власнику житла (getBooking, FR-12).

    Args:
        booking_id: Ідентифікатор бронювання.
        user: Користувач, що запитує бронювання.

    Returns:
        Запис бронювання.

    Raises:
        ProblemError: NOT_FOUND для відсутнього або чужого бронювання.
    """
    with _fresh_state():
        return _visible(booking_id, user)


def list_for(user: dict, role: str) -> list[dict]:
    """Відбирає бронювання користувача за роллю (listBookings, FR-12).

    Args:
        user: Користувач.
        role: guest — власні поїздки, owner — запити й бронювання власного житла.

    Returns:
        Записи бронювань.
    """
    key = "_guestId" if role == "guest" else "_hostId"
    with _fresh_state():
        return [booking for booking in repository.all_bookings() if booking[key] == user["userId"]]


def _pending_of_host(booking_id: str, user: dict) -> dict:
    booking = repository.get_booking(booking_id)
    if booking is None:
        raise not_found()
    if booking["_hostId"] != user["userId"]:
        raise ProblemError("FORBIDDEN", "Дія доступна лише власнику житла.")
    if booking["status"] != "PENDING":
        raise ProblemError("STATE_CONFLICT", "Бронювання вже не в статусі PENDING.")
    return booking


def confirm(booking_id: str, user: dict) -> dict:
    """Підтверджує запит і відхиляє несумісні запити в PENDING (FR-09, NFR-01).

    Args:
        booking_id: Ідентифікатор бронювання.
        user: Власник житла.

    Returns:
        Запис у статусі CONFIRMED.

    Raises:
        ProblemError: NOT_FOUND, якщо бронювання немає, FORBIDDEN для не власника,
            STATE_CONFLICT, якщо бронювання вже не в PENDING.
    """
    with _fresh_state():
        booking = _pending_of_host(booking_id, user)
        booking["status"] = "CONFIRMED"
        check_in, check_out = _stay(booking)
        for other in repository.bookings_of_listing(booking["listingId"]):
            if (
                other is not booking
                and other["status"] == "PENDING"
                and overlaps(check_in, check_out, booking["turnoverNights"], other)
            ):
                other["status"] = "REJECTED"
        return booking


def reject(booking_id: str, user: dict) -> dict:
    """Відхиляє запит власником (FR-09).

    Args:
        booking_id: Ідентифікатор бронювання.
        user: Власник житла.

    Returns:
        Запис у статусі REJECTED.

    Raises:
        ProblemError: NOT_FOUND, якщо бронювання немає, FORBIDDEN для не власника,
            STATE_CONFLICT, якщо бронювання вже не в PENDING.
    """
    with _fresh_state():
        booking = _pending_of_host(booking_id, user)
        booking["status"] = "REJECTED"
        return booking


def cancel(booking_id: str, user: dict) -> dict:
    """Скасовує бронювання до моменту заїзду (FR-13).

    Гість скасовує запит у PENDING або бронювання в CONFIRMED, власник — лише в CONFIRMED.
    Частка повернення зберігається у службовому полі й в API не виходить (lab5-scope.md, п. 6).

    Args:
        booking_id: Ідентифікатор бронювання.
        user: Гість цього бронювання або власник житла.

    Returns:
        Запис у статусі CANCELLED.

    Raises:
        ProblemError: NOT_FOUND для відсутнього або чужого бронювання, STATE_CONFLICT, якщо статус
            не дозволяє скасування або момент заїзду настав.
    """
    with _fresh_state() as current:
        booking = _visible(booking_id, user)
        cancelled_by = "GUEST" if user["userId"] == booking["_guestId"] else "HOST"
        allowed = ("PENDING", "CONFIRMED") if cancelled_by == "GUEST" else ("CONFIRMED",)
        if booking["status"] not in allowed:
            raise ProblemError(
                "STATE_CONFLICT", f"Бронювання в статусі {booking['status']} скасувати неможливо."
            )
        if current >= booking["_checkInAt"]:
            raise ProblemError(
                "STATE_CONFLICT",
                f"Момент заїзду {booking['checkInAt']} настав, скасування неможливе.",
            )
        booking["_refundShare"] = refund_share(
            cancelled_by, booking["status"], current, booking["_checkInAt"]
        )
        booking["status"] = "CANCELLED"
        booking["cancelledBy"] = cancelled_by
        booking["cancelledAt"] = _iso(current)
        return booking


def reject_pending_for_listing(listing_id: str) -> None:
    """Відхиляє запити в PENDING на житло, зняте з публікації (FR-04).

    Args:
        listing_id: Ідентифікатор житла.
    """
    with _fresh_state():
        for booking in repository.bookings_of_listing(listing_id):
            if booking["status"] == "PENDING":
                booking["status"] = "REJECTED"


def to_api(booking: dict) -> dict:
    """Готує запис до відповіді за схемою Booking.

    Args:
        booking: Запис сховища.

    Returns:
        Новий словник без службових полів із префіксом `_`.
    """
    return {key: value for key, value in booking.items() if not key.startswith("_")}
