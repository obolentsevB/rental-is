"""In-memory сховище житла і бронювань."""

_listings: dict[str, dict] = {}
_bookings: dict[str, dict] = {}


def get_listing(listing_id: str) -> dict | None:
    """Шукає запис житла.

    Args:
        listing_id: Ідентифікатор житла.

    Returns:
        Сам запис сховища, а не копію, або None. Зміни запису одразу діють у сховищі.
    """
    return _listings.get(listing_id)


def all_listings() -> list[dict]:
    """Повертає все житло в будь-якому стані.

    Returns:
        Новий список записів у порядку створення; на цьому порядку ґрунтується FR-ADD-02.
    """
    return list(_listings.values())


def save_listing(record: dict) -> dict:
    """Додає запис житла або замінює запис із тим самим `id`.

    Args:
        record: Запис житла з ключем `id`.

    Returns:
        Переданий запис.
    """
    _listings[record["id"]] = record
    return record


def get_booking(booking_id: str) -> dict | None:
    """Шукає запис бронювання.

    Args:
        booking_id: Ідентифікатор бронювання.

    Returns:
        Сам запис сховища, а не копію, або None. Зміни запису одразу діють у сховищі.
    """
    return _bookings.get(booking_id)


def all_bookings() -> list[dict]:
    """Повертає всі бронювання в будь-якому статусі.

    Returns:
        Новий список записів у порядку створення.
    """
    return list(_bookings.values())


def bookings_of_listing(listing_id: str) -> list[dict]:
    """Відбирає бронювання одного житла в будь-якому статусі.

    Args:
        listing_id: Ідентифікатор житла.

    Returns:
        Новий список записів.
    """
    return [booking for booking in _bookings.values() if booking["listingId"] == listing_id]


def save_booking(record: dict) -> dict:
    """Додає запис бронювання або замінює запис із тим самим `id`.

    Args:
        record: Запис бронювання з ключем `id`.

    Returns:
        Переданий запис.
    """
    _bookings[record["id"]] = record
    return record
