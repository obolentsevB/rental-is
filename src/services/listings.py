"""Сервісний шар житла (FR-02, FR-04, FR-05)."""
import base64
import binascii
import uuid
from datetime import date
from decimal import Decimal

from src import repository
from src.errors import ProblemError, not_found
from src.schemas import ExistingPhoto, ListingRequest, NewPhoto
from src.services import bookings

MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 5 * 1_048_576  # FR-02, ADD-01
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


# --- Фотографії -----------------------------------------------------------------


def _check_new_photo(number: int, photo: NewPhoto) -> None:
    try:
        raw = base64.b64decode(photo.data, validate=True)
    except (binascii.Error, ValueError):
        raise ProblemError("PHOTO_INVALID", f"Фотографія {number} не є коректним base64.")
    if not raw.startswith((PNG_SIGNATURE, JPEG_SIGNATURE)):
        raise ProblemError("PHOTO_INVALID", f"Фотографія {number} не у форматі JPEG чи PNG.")
    if len(raw) > MAX_PHOTO_BYTES:
        raise ProblemError(
            "PHOTO_INVALID", f"Фотографія {number} має розмір {len(raw)} байт, більше за {MAX_PHOTO_BYTES}."
        )


def _resolve_photos(photos: list, base_url: str, current: list[dict] | None = None) -> list[dict]:
    """Перевіряє вимоги FR-02 до фотографій і повертає записи Photo; при порушенні — PHOTO_INVALID."""
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ProblemError("PHOTO_INVALID", f"Потрібно від 1 до {MAX_PHOTOS} фотографій, отримано {len(photos)}.")
    kept = {photo["id"]: photo for photo in current or []}
    resolved = []
    for number, photo in enumerate(photos, start=1):
        if isinstance(photo, ExistingPhoto):
            if str(photo.id) not in kept:
                raise ProblemError("PHOTO_INVALID", f"Фотографія {number} не належить цій картці.")
            resolved.append(kept[str(photo.id)])
            continue
        _check_new_photo(number, photo)
        photo_id = str(uuid.uuid4())
        resolved.append({"id": photo_id, "url": f"{base_url}photos/{photo_id}"})
    return resolved


# --- Допоміжне ------------------------------------------------------------------


def _card_fields(body: ListingRequest, photos: list[dict]) -> dict:
    fields = body.model_dump(exclude={"photos", "description"})
    if body.description is not None:
        fields["description"] = body.description
    fields["photos"] = photos
    return fields


def _can_see(record: dict, user: dict | None) -> bool:
    if record["status"] == "PUBLISHED":
        return True
    return user is not None and (user["role"] == "MODERATOR" or user["userId"] == record["ownerId"])


def to_api(record: dict) -> dict:
    """Представлення за схемою Listing (без службових полів сховища)."""
    return {key: value for key, value in record.items() if key not in ("ownerId", "unpublishedBy")}


def _price(record: dict) -> Decimal:
    return Decimal(record["pricePerNight"])


def _check_date_range(check_in: date | None, check_out: date | None) -> None:
    if (check_in is None) != (check_out is None):
        raise ProblemError("VALIDATION_FAILED", "checkIn і checkOut задаються разом.")
    if check_in is not None and check_in >= check_out:
        raise ProblemError("VALIDATION_FAILED", "checkOut має бути пізнішим за checkIn.")


# --- Дії ------------------------------------------------------------------------


def search(
    city: str | None,
    check_in: date | None,
    check_out: date | None,
    guests_count: int | None,
    price_min: str | None,
    price_max: str | None,
    sort: str | None,
) -> list[dict]:
    """FR-05: житло в стані Published за необов'язковими фільтрами.

    Порядок (FR-ADD-02): без `sort` і для рівних значень ключа — за моментом створення.
    Його дають порядок вставки у сховищі та стабільність `list.sort`.
    """
    _check_date_range(check_in, check_out)

    def matches(record: dict) -> bool:
        return (
            record["status"] == "PUBLISHED"
            and (city is None or record["city"].casefold() == city.casefold())
            and (guests_count is None or guests_count <= record["maxGuests"])
            and (price_min is None or _price(record) >= Decimal(price_min))
            and (price_max is None or _price(record) <= Decimal(price_max))
            and (check_in is None or bookings.is_available(record, check_in, check_out))
        )

    results = [record for record in repository.all_listings() if matches(record)]
    if sort in ("price_asc", "price_desc"):
        results.sort(key=_price, reverse=sort == "price_desc")
    elif sort == "rating_desc":
        results.sort(key=lambda record: (record["averageRating"] is None, -(record["averageRating"] or 0)))
    return results


def paginate(items: list[dict], limit: int, offset: int) -> tuple[list[dict], int]:
    """FR-ADD-02: сторінка впорядкованого результату та загальна кількість до застосування limit і offset."""
    return items[offset:offset + limit], len(items)


def create(owner: dict, body: ListingRequest, base_url: str) -> dict:
    """FR-02: нове оголошення одразу в стані Published."""
    photos = _resolve_photos(body.photos, base_url)
    return repository.save_listing({
        "id": str(uuid.uuid4()),
        **_card_fields(body, photos),
        "status": "PUBLISHED",
        "averageRating": None,
        "ownerId": owner["userId"],
        "unpublishedBy": None,
    })


def get(listing_id: str, user: dict | None) -> dict:
    record = repository.get_listing(listing_id)
    if record is None or not _can_see(record, user):
        raise not_found()
    return record


def replace(listing_id: str, user: dict, body: ListingRequest, base_url: str) -> dict:
    """FR-02: повна заміна картки власником; відсутні необов'язкові поля скидаються до значень за замовчуванням."""
    record = get(listing_id, user)
    if record["ownerId"] != user["userId"]:
        raise ProblemError("FORBIDDEN", "Редагувати можна лише власне оголошення.")
    photos = _resolve_photos(body.photos, base_url, current=record["photos"])
    record.pop("description", None)
    record.update(_card_fields(body, photos))
    return record


def unpublish(listing_id: str, moderator: dict) -> dict:
    """FR-04: зняття модератором; запити в PENDING переходять у REJECTED."""
    record = get(listing_id, moderator)
    if record["status"] == "UNPUBLISHED":
        raise ProblemError("STATE_CONFLICT", "Оголошення вже зняте з публікації.")
    record["status"] = "UNPUBLISHED"
    record["unpublishedBy"] = "MODERATOR"
    bookings.reject_pending_for_listing(listing_id)
    return record


def publish(listing_id: str, moderator: dict) -> dict:
    """FR-04: повернення в публікацію лише оголошення, знятого модератором."""
    record = get(listing_id, moderator)
    if record["status"] == "PUBLISHED":
        raise ProblemError("STATE_CONFLICT", "Оголошення вже опубліковане.")
    if record["unpublishedBy"] != "MODERATOR":
        raise ProblemError("STATE_CONFLICT", "Оголошення, зняте не модератором, повертається лише за оскарженням.")
    record["status"] = "PUBLISHED"
    record["unpublishedBy"] = None
    return record
