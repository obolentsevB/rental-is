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
    except (binascii.Error, ValueError) as err:
        raise ProblemError("PHOTO_INVALID", f"Фотографія {number} не є коректним base64.") from err
    if not raw.startswith((PNG_SIGNATURE, JPEG_SIGNATURE)):
        raise ProblemError("PHOTO_INVALID", f"Фотографія {number} не у форматі JPEG чи PNG.")
    if len(raw) > MAX_PHOTO_BYTES:
        raise ProblemError(
            "PHOTO_INVALID",
            f"Фотографія {number} має розмір {len(raw)} байт, більше за {MAX_PHOTO_BYTES}.",
        )


def _resolve_photos(photos: list, base_url: str, current: list[dict] | None = None) -> list[dict]:
    """Перевіряє вимоги FR-02 до фотографій і повертає записи Photo.

    При порушенні — PHOTO_INVALID.
    """
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ProblemError(
            "PHOTO_INVALID", f"Потрібно від 1 до {MAX_PHOTOS} фотографій, отримано {len(photos)}."
        )
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
    return user is not None and (user["role"] == "MODERATOR" or user["userId"] == record["hostId"])


def to_api(record: dict) -> dict:
    """Готує запис до відповіді за схемою Listing.

    Args:
        record: Запис сховища.

    Returns:
        Новий словник без службових полів `hostId` і `unpublishedBy`.
    """
    return {key: value for key, value in record.items() if key not in ("hostId", "unpublishedBy")}


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
    """Шукає житло в стані Published за необов'язковими фільтрами (FR-05).

    Порядок (FR-ADD-02): без `sort` і для рівних значень ключа — за моментом створення.
    Його дають порядок вставки у сховищі та стабільність `list.sort`.

    Args:
        city: Місто, порівнюється без урахування регістру.
        check_in: Дата заїзду, задається разом із `check_out`.
        check_out: Дата виїзду.
        guests_count: Кількість осіб.
        price_min: Нижня межа ціни за ніч.
        price_max: Верхня межа ціни за ніч.
        sort: price_asc, price_desc, rating_desc або None.

    Returns:
        Упорядковані записи житла.

    Raises:
        ProblemError: VALIDATION_FAILED, якщо задано лише одну дату або діапазон порожній.
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
        results.sort(
            key=lambda record: (record["averageRating"] is None, -(record["averageRating"] or 0))
        )
    return results


def paginate(items: list[dict], limit: int, offset: int) -> tuple[list[dict], int]:
    """Вирізає сторінку впорядкованого результату (FR-ADD-02).

    Args:
        items: Увесь упорядкований результат.
        limit: Розмір сторінки.
        offset: Кількість пропущених записів.

    Returns:
        Сторінку й загальну кількість записів до застосування `limit` і `offset`.
    """
    return items[offset : offset + limit], len(items)


def create(host: dict, body: ListingRequest, base_url: str) -> dict:
    """Створює оголошення одразу в стані Published (FR-02).

    Args:
        host: Користувач, що стає власником житла.
        body: Картка житла.
        base_url: Базова адреса для URL фотографій, зі скісною рискою в кінці.

    Returns:
        Збережений запис житла.

    Raises:
        ProblemError: PHOTO_INVALID за порушення вимог до фотографій.
    """
    photos = _resolve_photos(body.photos, base_url)
    return repository.save_listing(
        {
            "id": str(uuid.uuid4()),
            **_card_fields(body, photos),
            "status": "PUBLISHED",
            "averageRating": None,
            "hostId": host["userId"],
            "unpublishedBy": None,
        }
    )


def get(listing_id: str, user: dict | None) -> dict:
    """Повертає житло, якщо воно видиме користувачу (getListing, AC-04.6).

    Опубліковане житло бачать усі, зняте — лише його власник і модератор.

    Args:
        listing_id: Ідентифікатор житла.
        user: Користувач або None для незареєстрованого відвідувача.

    Returns:
        Запис житла.

    Raises:
        ProblemError: NOT_FOUND, якщо житла немає або воно недоступне.
    """
    record = repository.get_listing(listing_id)
    if record is None or not _can_see(record, user):
        raise not_found()
    return record


def replace(listing_id: str, user: dict, body: ListingRequest, base_url: str) -> dict:
    """Повністю замінює картку власником (FR-02).

    Відсутні необов'язкові поля скидаються до значень за замовчуванням.

    Args:
        listing_id: Ідентифікатор житла.
        user: Користувач, що редагує картку.
        body: Нова картка житла.
        base_url: Базова адреса для URL нових фотографій.

    Returns:
        Оновлений запис житла.

    Raises:
        ProblemError: NOT_FOUND для недоступного житла, FORBIDDEN для не власника, PHOTO_INVALID
            за порушення вимог до фотографій.
    """
    record = get(listing_id, user)
    if record["hostId"] != user["userId"]:
        raise ProblemError("FORBIDDEN", "Редагувати можна лише власне оголошення.")
    photos = _resolve_photos(body.photos, base_url, current=record["photos"])
    record.pop("description", None)
    record.update(_card_fields(body, photos))
    return record


def unpublish(listing_id: str, moderator: dict) -> dict:
    """Знімає житло з публікації рішенням модератора (FR-04).

    Запити в PENDING на це житло переходять у REJECTED.

    Args:
        listing_id: Ідентифікатор житла.
        moderator: Модератор.

    Returns:
        Оновлений запис житла.

    Raises:
        ProblemError: NOT_FOUND, якщо житла немає, STATE_CONFLICT, якщо воно вже зняте.
    """
    record = get(listing_id, moderator)
    if record["status"] == "UNPUBLISHED":
        raise ProblemError("STATE_CONFLICT", "Оголошення вже зняте з публікації.")
    record["status"] = "UNPUBLISHED"
    record["unpublishedBy"] = "MODERATOR"
    bookings.reject_pending_for_listing(listing_id)
    return record


def publish(listing_id: str, moderator: dict) -> dict:
    """Повертає в публікацію лише житло, зняте модератором (FR-04).

    Args:
        listing_id: Ідентифікатор житла.
        moderator: Модератор.

    Returns:
        Оновлений запис житла.

    Raises:
        ProblemError: NOT_FOUND, якщо житла немає, STATE_CONFLICT, якщо воно вже опубліковане
            або зняте не модератором.
    """
    record = get(listing_id, moderator)
    if record["status"] == "PUBLISHED":
        raise ProblemError("STATE_CONFLICT", "Оголошення вже опубліковане.")
    if record["unpublishedBy"] != "MODERATOR":
        raise ProblemError(
            "STATE_CONFLICT", "Оголошення, зняте не модератором, повертається лише за оскарженням."
        )
    record["status"] = "PUBLISHED"
    record["unpublishedBy"] = None
    return record
