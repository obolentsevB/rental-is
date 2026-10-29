"""Сервісний шар бронювань (FR-06–FR-13, FR-15) з in-memory сховищем.

Обсяг — logs/lab5-scope.md: закритих ночей немає (пп. 2, 4), платіжні операції
не створюються (п. 5), частка повернення p розраховується тут і в API не
виходить (п. 6). FR-10 і FR-11 застосовуються ліниво перед кожною дією за
годинником `now`, який модульні тести підміняють (п. 10).
"""
import threading
import uuid
from datetime import date, datetime, time, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")
CENT = Decimal("0.01")

# Параметри платформи (SRS §5, NFR-10): змінюються лише в конфігурації.
COMMISSION_RATE = Decimal("10")
MIN_TIME_BEFORE_CHECKIN = timedelta(hours=1)
DECISION_PERIOD = timedelta(hours=24)
REVIEW_PERIOD = timedelta(days=14)

BOOKINGS: dict[str, dict] = {}
LOCK = threading.RLock()  # NFR-01: дії над бронюваннями виконуються послідовно


def now() -> datetime:
    return datetime.now(KYIV)


class BookingError(Exception):
    """Відмова з кодом зі схеми Problem; HTTP-статус визначає шар API."""

    def __init__(self, code: str, detail: str, conflicting_ids: list[str] | None = None):
        super().__init__(detail)
        self.code, self.detail, self.conflicting_ids = code, detail, conflicting_ids


# --- Розрахунки -----------------------------------------------------------------


def moment(night: date, clock_time: str) -> datetime:
    hours, minutes = map(int, clock_time.split(":"))
    return datetime.combine(night, time(hours, minutes), tzinfo=KYIV)


def costs(nights: int, price_per_night: Decimal, rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """FR-15: вартість проживання, комісія (вниз до 0,01), передоплата."""
    accommodation = nights * price_per_night
    commission = (accommodation * rate / 100).quantize(CENT, rounding=ROUND_FLOOR)
    return accommodation, commission, accommodation + commission


def refund_share(initiator: str, previous_status: str, cancelled_at: datetime, check_in_at: datetime) -> int:
    """FR-13: частка повернення p, %, за ініціатором і попереднім статусом."""
    if initiator != "GUEST" or previous_status == "PENDING":
        return 100
    hours_left = check_in_at - cancelled_at
    if hours_left >= timedelta(hours=168):
        return 100
    if hours_left >= timedelta(hours=72):
        return 50
    return 0


def refund_amount(share: int, accommodation: Decimal, commission: Decimal) -> Decimal:
    """FR-15: повернення = p × вартість + p × комісія, кожен доданок угору до 0,01."""
    def part(amount: Decimal) -> Decimal:
        return (amount * share / 100).quantize(CENT, rounding=ROUND_CEILING)

    return part(accommodation) + part(commission)


def overlaps(check_in: date, check_out: date, turnover: int, other: dict) -> bool:
    """Умова (2) FR-08 з перервою запиту `turnover` і перервою, зафіксованою в `other`."""
    other_in, other_out = date.fromisoformat(other["checkIn"]), date.fromisoformat(other["checkOut"])
    return (
        check_in < other_out + timedelta(days=other["turnoverNights"])
        and other_in < check_out + timedelta(days=turnover)
    )


# --- Стан у часі (FR-10, FR-11) -------------------------------------------------


def refresh(current: datetime | None = None) -> None:
    """Автоматичне відхилення після строку рішення і завершення в момент виїзду."""
    current = current or now()
    for booking in BOOKINGS.values():
        if booking["status"] == "PENDING" and current >= booking["_decisionDeadline"]:
            booking["status"] = "REJECTED"
        elif booking["status"] == "CONFIRMED" and current >= booking["_checkOutAt"]:
            booking["status"] = "COMPLETED"
            booking["reviewDeadline"] = (booking["_checkOutAt"] + REVIEW_PERIOD).isoformat(timespec="seconds")


def conflicts(listing_id: str, check_in: date, check_out: date, turnover: int) -> list[str]:
    """Бронювання житла в CONFIRMED або COMPLETED, з якими перетинається діапазон (FR-08, умова 2)."""
    return [
        booking["id"]
        for booking in BOOKINGS.values()
        if booking["listingId"] == listing_id
        and booking["status"] in ("CONFIRMED", "COMPLETED")
        and overlaps(check_in, check_out, turnover, booking)
    ]


def is_available(listing: dict, check_in: date, check_out: date) -> bool:
    """Повна перевірка доступності для пошуку (FR-05) з перервою, чинною на момент пошуку."""
    with LOCK:
        refresh()
        return not conflicts(listing["id"], check_in, check_out, listing["turnoverNights"])


# --- Дії ------------------------------------------------------------------------


def create(user: dict, listing: dict, check_in: date, check_out: date, guests_count: int) -> dict:
    """FR-06 з перевірками FR-07 у порядку SRS; ACCOUNT_BLOCKED (№0) не моделюється."""
    with LOCK:
        current = now()
        refresh(current)
        nights = (check_out - check_in).days
        if nights < 1:
            raise BookingError("MIN_NIGHTS", f"Діапазон [{check_in}, {check_out}) містить {max(nights, 0)} ночей.")
        if user["userId"] == listing["ownerId"]:
            raise BookingError("OWN_LISTING", "Не можна бронювати житло, власником якого ви є.")
        if not 1 <= guests_count <= listing["maxGuests"]:
            raise BookingError(
                "GUESTS_OUT_OF_RANGE", f"Кількість осіб {guests_count} поза межами 1–{listing['maxGuests']}."
            )
        if listing["status"] == "UNPUBLISHED":
            raise BookingError("LISTING_UNPUBLISHED", "Житло в стані Unpublished не приймає нових запитів.")
        check_in_at = moment(check_in, listing["checkInTime"])
        if check_in_at - current < MIN_TIME_BEFORE_CHECKIN:
            raise BookingError(
                "CHECKIN_TOO_SOON",
                f"До моменту заїзду {check_in_at.isoformat(timespec='seconds')} лишається менше 1 години.",
            )
        conflicting = conflicts(listing["id"], check_in, check_out, listing["turnoverNights"])
        if conflicting:
            raise BookingError(
                "DATES_UNAVAILABLE",
                f"Діапазон [{check_in}, {check_out}) не проходить повну перевірку доступності.",
                conflicting,
            )

        accommodation, commission, prepayment = costs(nights, Decimal(listing["pricePerNight"]), COMMISSION_RATE)
        check_out_at = moment(check_out, listing["checkOutTime"])
        decision_deadline = min(current + DECISION_PERIOD, check_in_at)
        booking_id = str(uuid.uuid4())
        BOOKINGS[booking_id] = {
            "id": booking_id,
            "listingId": listing["id"],
            "checkIn": check_in.isoformat(),
            "checkOut": check_out.isoformat(),
            "guestsCount": guests_count,
            "status": "PENDING",
            "checkInTime": listing["checkInTime"],
            "checkOutTime": listing["checkOutTime"],
            "turnoverNights": listing["turnoverNights"],
            "commissionRate": int(COMMISSION_RATE) if COMMISSION_RATE == COMMISSION_RATE.to_integral() else float(COMMISSION_RATE),
            "accommodationCost": str(accommodation),
            "commission": str(commission),
            "prepayment": str(prepayment),
            "checkInAt": check_in_at.isoformat(timespec="seconds"),
            "checkOutAt": check_out_at.isoformat(timespec="seconds"),
            "decisionDeadline": decision_deadline.isoformat(timespec="seconds"),
            "cancelledBy": None,
            "cancelledAt": None,
            "reviewDeadline": None,
            # Службові поля (з префіксом _) у відповідь API не потрапляють.
            "_guestId": user["userId"],
            "_hostId": listing["ownerId"],
            "_checkInAt": check_in_at,
            "_checkOutAt": check_out_at,
            "_decisionDeadline": decision_deadline,
            "_refundShare": None,
        }
        return BOOKINGS[booking_id]


def visible(booking_id: str, user: dict) -> dict:
    """Бронювання, доступне гостю або власнику житла; для інших — NOT_FOUND (getBooking)."""
    booking = BOOKINGS.get(booking_id)
    if booking is None or user["userId"] not in (booking["_guestId"], booking["_hostId"]):
        raise BookingError("NOT_FOUND", "Ресурс не існує або недоступний.")
    return booking


def get(booking_id: str, user: dict) -> dict:
    with LOCK:
        refresh()
        return visible(booking_id, user)


def list_for(user: dict, role: str) -> list[dict]:
    """FR-12: role=guest — власні поїздки; role=owner — запити й бронювання власного житла."""
    key = "_guestId" if role == "guest" else "_hostId"
    with LOCK:
        refresh()
        return [booking for booking in BOOKINGS.values() if booking[key] == user["userId"]]


def _owned_pending(booking_id: str, user: dict) -> dict:
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        raise BookingError("NOT_FOUND", "Ресурс не існує або недоступний.")
    if booking["_hostId"] != user["userId"]:
        raise BookingError("FORBIDDEN", "Дія доступна лише власнику житла.")
    if booking["status"] != "PENDING":
        raise BookingError("STATE_CONFLICT", "Бронювання вже не в статусі PENDING.")
    return booking


def confirm(booking_id: str, user: dict) -> dict:
    """FR-09: підтвердження з автоматичним відхиленням несумісних запитів у PENDING."""
    with LOCK:
        refresh()
        booking = _owned_pending(booking_id, user)
        booking["status"] = "CONFIRMED"
        check_in, check_out = date.fromisoformat(booking["checkIn"]), date.fromisoformat(booking["checkOut"])
        for other in BOOKINGS.values():
            if (
                other is not booking
                and other["listingId"] == booking["listingId"]
                and other["status"] == "PENDING"
                and overlaps(check_in, check_out, booking["turnoverNights"], other)
            ):
                other["status"] = "REJECTED"
        return booking


def reject(booking_id: str, user: dict) -> dict:
    """FR-09: відхилення власником."""
    with LOCK:
        refresh()
        booking = _owned_pending(booking_id, user)
        booking["status"] = "REJECTED"
        return booking


def cancel(booking_id: str, user: dict) -> dict:
    """FR-13: скасування гостем (PENDING, CONFIRMED) або власником (CONFIRMED) до моменту заїзду."""
    with LOCK:
        current = now()
        refresh(current)
        booking = visible(booking_id, user)
        initiator = "GUEST" if user["userId"] == booking["_guestId"] else "HOST"
        allowed = ("PENDING", "CONFIRMED") if initiator == "GUEST" else ("CONFIRMED",)
        if booking["status"] not in allowed:
            raise BookingError("STATE_CONFLICT", f"Бронювання в статусі {booking['status']} скасувати неможливо.")
        if current >= booking["_checkInAt"]:
            raise BookingError(
                "STATE_CONFLICT", f"Момент заїзду {booking['checkInAt']} настав, скасування неможливе."
            )
        booking["_refundShare"] = refund_share(initiator, booking["status"], current, booking["_checkInAt"])
        booking["status"] = "CANCELLED"
        booking["cancelledBy"] = initiator
        booking["cancelledAt"] = current.isoformat(timespec="seconds")
        return booking


def reject_pending_for_listing(listing_id: str) -> None:
    """FR-04: при знятті житла з публікації запити в PENDING переходять у REJECTED."""
    with LOCK:
        refresh()
        for booking in BOOKINGS.values():
            if booking["listingId"] == listing_id and booking["status"] == "PENDING":
                booking["status"] = "REJECTED"


def to_api(booking: dict) -> dict:
    """Представлення за схемою Booking."""
    return {key: value for key, value in booking.items() if not key.startswith("_")}
