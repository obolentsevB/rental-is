"""HTTP-маршрути операцій Bookings (api/openapi.yaml, тег Bookings).

Docstring кожного обробника починається із символу form feed. FastAPI відкидає текст після
цього символу, тому внутрішні секції не потрапляють в OpenAPI: опис операцій задає контракт.
"""

from fastapi import APIRouter

from src.auth import NonModerator, User
from src.schemas import BookingListRole, BookingRequest
from src.services import bookings as service

router = APIRouter()


@router.post("/bookings", status_code=201)
def create_booking(user: NonModerator, body: BookingRequest):
    """\fСтворює запит на бронювання (createBooking, FR-06, FR-07, FR-08, FR-15).

    Args:
        user: Гість; модератору операція заборонена.
        body: Житло, дати й кількість осіб.

    Returns:
        Запис за схемою Booking у статусі PENDING, відповідь має статус 201.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, FORBIDDEN для модератора, NOT_FOUND, якщо
            житла немає, або перший код відмови FR-07: MIN_NIGHTS, OWN_LISTING,
            GUESTS_OUT_OF_RANGE, LISTING_UNPUBLISHED, CHECKIN_TOO_SOON, DATES_UNAVAILABLE.
    """
    booking = service.create(
        user, str(body.listingId), body.checkIn, body.checkOut, body.guestsCount
    )
    return service.to_api(booking)


@router.get("/bookings")
def list_bookings(user: NonModerator, role: BookingListRole):
    """\fПовертає бронювання користувача (listBookings, FR-12).

    Args:
        user: Гість або власник; модератору операція заборонена.
        role: guest — власні поїздки, owner — запити й бронювання власного житла.

    Returns:
        Записи за схемою Booking.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, FORBIDDEN для модератора.
    """
    return [service.to_api(booking) for booking in service.list_for(user, role)]


@router.get("/bookings/{bookingId}")
def get_booking(bookingId: str, user: User):
    """\fПовертає бронювання (getBooking, FR-12).

    Args:
        bookingId: Ідентифікатор бронювання.
        user: Гість цього бронювання або власник житла.

    Returns:
        Запис за схемою Booking.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, NOT_FOUND для відсутнього або чужого бронювання.
    """
    return service.to_api(service.get(bookingId, user))


@router.post("/bookings/{bookingId}/confirm")
def confirm_booking(bookingId: str, user: User):
    """\fПідтверджує запит власником (confirmBooking, FR-09, NFR-01).

    Args:
        bookingId: Ідентифікатор бронювання.
        user: Власник житла.

    Returns:
        Запис за схемою Booking у статусі CONFIRMED.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, NOT_FOUND, якщо бронювання немає, FORBIDDEN для
            не власника, STATE_CONFLICT, якщо бронювання вже не в PENDING.
    """
    return service.to_api(service.confirm(bookingId, user))


@router.post("/bookings/{bookingId}/reject")
def reject_booking(bookingId: str, user: User):
    """\fВідхиляє запит власником (rejectBooking, FR-09).

    Args:
        bookingId: Ідентифікатор бронювання.
        user: Власник житла.

    Returns:
        Запис за схемою Booking у статусі REJECTED.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, NOT_FOUND, якщо бронювання немає, FORBIDDEN для
            не власника, STATE_CONFLICT, якщо бронювання вже не в PENDING.
    """
    return service.to_api(service.reject(bookingId, user))


@router.post("/bookings/{bookingId}/cancel")
def cancel_booking(bookingId: str, user: User):
    """\fСкасовує бронювання гостем або власником (cancelBooking, FR-13).

    Args:
        bookingId: Ідентифікатор бронювання.
        user: Гість цього бронювання або власник житла.

    Returns:
        Запис за схемою Booking у статусі CANCELLED.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, NOT_FOUND для відсутнього або чужого бронювання,
            STATE_CONFLICT, якщо статус не дозволяє скасування або момент заїзду настав.
    """
    return service.to_api(service.cancel(bookingId, user))
