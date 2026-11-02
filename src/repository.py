"""In-memory сховище житла і бронювань."""

_listings: dict[str, dict] = {}
_bookings: dict[str, dict] = {}


def get_listing(listing_id: str) -> dict | None:
    return _listings.get(listing_id)


def all_listings() -> list[dict]:
    return list(_listings.values())


def save_listing(record: dict) -> dict:
    _listings[record["id"]] = record
    return record


def get_booking(booking_id: str) -> dict | None:
    return _bookings.get(booking_id)


def all_bookings() -> list[dict]:
    return list(_bookings.values())


def bookings_of_listing(listing_id: str) -> list[dict]:
    return [booking for booking in _bookings.values() if booking["listingId"] == listing_id]


def save_booking(record: dict) -> dict:
    _bookings[record["id"]] = record
    return record
