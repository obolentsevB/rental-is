"""HTTP-маршрути операцій Bookings (api/openapi.yaml, тег Bookings)."""

from fastapi import APIRouter

from src.auth import NonModerator, User
from src.schemas import BookingListRole, BookingRequest
from src.services import bookings as service

router = APIRouter()


@router.post("/bookings", status_code=201)
def create_booking(user: NonModerator, body: BookingRequest):
    booking = service.create(
        user, str(body.listingId), body.checkIn, body.checkOut, body.guestsCount
    )
    return service.to_api(booking)


@router.get("/bookings")
def list_bookings(user: NonModerator, role: BookingListRole):
    return [service.to_api(booking) for booking in service.list_for(user, role)]


@router.get("/bookings/{bookingId}")
def get_booking(bookingId: str, user: User):
    return service.to_api(service.get(bookingId, user))


@router.post("/bookings/{bookingId}/confirm")
def confirm_booking(bookingId: str, user: User):
    return service.to_api(service.confirm(bookingId, user))


@router.post("/bookings/{bookingId}/reject")
def reject_booking(bookingId: str, user: User):
    return service.to_api(service.reject(bookingId, user))


@router.post("/bookings/{bookingId}/cancel")
def cancel_booking(bookingId: str, user: User):
    return service.to_api(service.cancel(bookingId, user))
