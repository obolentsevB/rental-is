"""rental-is: операції Listings за api/openapi.yaml (тег Listings), in-memory сховище.

Обсяг і обмеження — logs/lab5-scope.md. Bookings ще не реалізовано, тому фільтр
пошуку за діапазоном дат лише валідує checkIn/checkOut: бронювань, з якими можна
перетнутися, поки немає, а закритих ночей немає за обсягом (п. 4).
"""
import base64
import binascii
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.auth import TOKENS

app = FastAPI(title="rental-is")

MONEY_PATTERN = r"^\d+\.\d{2}$"
MAX_PHOTO_BYTES = 5 * 1_048_576  # FR-02, ADD-01
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

LISTINGS: dict[str, dict] = {}


# --- Помилки (схема Problem, RFC 9457) -----------------------------------------

PROBLEM_TITLES = {
    "UNAUTHENTICATED": "Потрібен вхід",
    "FORBIDDEN": "Дію не дозволено",
    "NOT_FOUND": "Не знайдено",
    "VALIDATION_FAILED": "Запит порушує схему",
    "STATE_CONFLICT": "Дія неможлива в поточному стані",
    "PHOTO_INVALID": "Фотографії не відповідають вимогам",
    "INTERNAL_ERROR": "Збій системи",
}


class ProblemError(Exception):
    def __init__(self, status: int, code: str, detail: str | None = None):
        self.status, self.code, self.detail = status, code, detail


def problem_response(status: int, code: str, detail: str | None = None) -> JSONResponse:
    body = {
        "type": f"urn:rental-is:problem:{code.lower().replace('_', '-')}",
        "title": PROBLEM_TITLES[code],
        "status": status,
        "code": code,
        "correlationId": str(uuid.uuid4()),
    }
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


@app.exception_handler(ProblemError)
async def handle_problem(request: Request, exc: ProblemError):
    return problem_response(exc.status, exc.code, exc.detail)


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0])
    return problem_response(422, "VALIDATION_FAILED", f"{field}: {error['msg']}")


@app.exception_handler(StarletteHTTPException)
async def handle_http(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return problem_response(404, "NOT_FOUND", "Ресурс не існує або недоступний.")
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def handle_internal(request: Request, exc: Exception):
    return problem_response(500, "INTERNAL_ERROR")


# --- Автентифікація -------------------------------------------------------------


def current_user(authorization: str | None) -> dict | None:
    """Користувач за bearer-токеном або None, якщо токена немає чи він невідомий."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return TOKENS.get(token.strip())


def require_user(authorization: str | None) -> dict:
    user = current_user(authorization)
    if user is None:
        raise ProblemError(401, "UNAUTHENTICATED", "Дія потребує входу в систему.")
    return user


def require_moderator(authorization: str | None) -> dict:
    user = require_user(authorization)
    if user["role"] != "MODERATOR":
        raise ProblemError(403, "FORBIDDEN", "Дія доступна лише модератору.")
    return user


# --- Схеми запитів --------------------------------------------------------------


class NewPhoto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: str


class ExistingPhoto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: uuid.UUID


class ListingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=2000)] | None = None
    city: Annotated[str, Field(min_length=1)]
    address: Annotated[str, Field(min_length=1)]
    maxGuests: Annotated[StrictInt, Field(ge=1, le=20)]
    pricePerNight: Annotated[str, Field(pattern=MONEY_PATTERN)]
    photos: list[NewPhoto | ExistingPhoto]
    checkInTime: Annotated[str, Field(pattern=r"^(1[2-9]:[0-5]\d|20:00)$")] = "14:00"
    checkOutTime: Annotated[str, Field(pattern=r"^(0[89]:[0-5]\d|1[01]:[0-5]\d|12:00)$")] = "11:00"
    turnoverNights: Literal[0, 1] = 0

    @field_validator("pricePerNight")
    @classmethod
    def price_in_range(cls, value: str) -> str:
        if not Decimal("0.01") <= Decimal(value) <= Decimal("1000000.00"):
            raise ValueError("від 0.01 до 1000000.00 включно")
        return value


class ModerationReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Annotated[str, Field(min_length=1)]


# --- Допоміжне ------------------------------------------------------------------


def photo_invalid(detail: str) -> ProblemError:
    return ProblemError(422, "PHOTO_INVALID", detail)


def resolve_photos(photos: list, request: Request, current: list[dict] | None = None) -> list[dict]:
    """Перевіряє вимоги FR-02 до фотографій і повертає записи Photo; при порушенні — PHOTO_INVALID."""
    if not 1 <= len(photos) <= 10:
        raise photo_invalid(f"Потрібно від 1 до 10 фотографій, отримано {len(photos)}.")
    kept = {photo["id"]: photo for photo in current or []}
    resolved = []
    for number, photo in enumerate(photos, start=1):
        if isinstance(photo, ExistingPhoto):
            if str(photo.id) not in kept:
                raise photo_invalid(f"Фотографія {number} не належить цій картці.")
            resolved.append(kept[str(photo.id)])
            continue
        try:
            raw = base64.b64decode(photo.data, validate=True)
        except (binascii.Error, ValueError):
            raise photo_invalid(f"Фотографія {number} не є коректним base64.")
        if not raw.startswith((PNG_SIGNATURE, JPEG_SIGNATURE)):
            raise photo_invalid(f"Фотографія {number} не у форматі JPEG чи PNG.")
        if len(raw) > MAX_PHOTO_BYTES:
            raise photo_invalid(f"Фотографія {number} має розмір {len(raw)} байт, більше за {MAX_PHOTO_BYTES}.")
        photo_id = str(uuid.uuid4())
        resolved.append({"id": photo_id, "url": f"{request.base_url}photos/{photo_id}"})
    return resolved


def listing_fields(body: ListingRequest, photos: list[dict]) -> dict:
    fields = body.model_dump(exclude={"photos", "description"})
    if body.description is not None:
        fields["description"] = body.description
    fields["photos"] = photos
    return fields


def to_listing(record: dict) -> dict:
    """Представлення за схемою Listing (без службових полів сховища)."""
    return {key: value for key, value in record.items() if key not in ("ownerId", "unpublishedBy")}


def can_see(record: dict, user: dict | None) -> bool:
    if record["status"] == "PUBLISHED":
        return True
    return user is not None and (user["role"] == "MODERATOR" or user["userId"] == record["ownerId"])


def find_listing(listing_id: str, user: dict | None) -> dict:
    record = LISTINGS.get(listing_id)
    if record is None or not can_see(record, user):
        raise ProblemError(404, "NOT_FOUND", "Ресурс не існує або недоступний.")
    return record


# --- Listings -------------------------------------------------------------------


@app.get("/listings")
def search_listings(
    city: str | None = None,
    checkIn: date | None = None,
    checkOut: date | None = None,
    guestsCount: Annotated[int | None, Query(ge=1)] = None,
    priceMin: Annotated[str | None, Query(pattern=MONEY_PATTERN)] = None,
    priceMax: Annotated[str | None, Query(pattern=MONEY_PATTERN)] = None,
    sort: Literal["price_asc", "price_desc", "rating_desc"] | None = None,
):
    if (checkIn is None) != (checkOut is None):
        raise ProblemError(422, "VALIDATION_FAILED", "checkIn і checkOut задаються разом.")
    if checkIn is not None and checkIn >= checkOut:
        raise ProblemError(422, "VALIDATION_FAILED", "checkOut має бути пізнішим за checkIn.")

    results = [record for record in LISTINGS.values() if record["status"] == "PUBLISHED"]
    if city is not None:
        results = [record for record in results if record["city"].casefold() == city.casefold()]
    if guestsCount is not None:
        results = [record for record in results if guestsCount <= record["maxGuests"]]
    if priceMin is not None:
        results = [record for record in results if Decimal(record["pricePerNight"]) >= Decimal(priceMin)]
    if priceMax is not None:
        results = [record for record in results if Decimal(record["pricePerNight"]) <= Decimal(priceMax)]

    if sort in ("price_asc", "price_desc"):
        results.sort(key=lambda record: Decimal(record["pricePerNight"]), reverse=sort == "price_desc")
    elif sort == "rating_desc":
        results.sort(key=lambda record: (record["averageRating"] is None, -(record["averageRating"] or 0)))
    return [to_listing(record) for record in results]


@app.post("/listings", status_code=201)
def create_listing(body: ListingRequest, request: Request, authorization: str | None = Header(None)):
    user = require_user(authorization)
    if user["role"] == "MODERATOR":
        raise ProblemError(403, "FORBIDDEN", "Модератор не створює оголошень.")
    photos = resolve_photos(body.photos, request)
    listing_id = str(uuid.uuid4())
    LISTINGS[listing_id] = {
        "id": listing_id,
        **listing_fields(body, photos),
        "status": "PUBLISHED",
        "averageRating": None,
        "ownerId": user["userId"],
        "unpublishedBy": None,
    }
    return to_listing(LISTINGS[listing_id])


@app.get("/listings/{listingId}")
def get_listing(listingId: str, authorization: str | None = Header(None)):
    return to_listing(find_listing(listingId, current_user(authorization)))


@app.put("/listings/{listingId}")
def replace_listing(
    listingId: str, body: ListingRequest, request: Request, authorization: str | None = Header(None)
):
    user = require_user(authorization)
    record = find_listing(listingId, user)
    if record["ownerId"] != user["userId"]:
        raise ProblemError(403, "FORBIDDEN", "Редагувати можна лише власне оголошення.")
    photos = resolve_photos(body.photos, request, current=record["photos"])
    # Повна заміна: відсутні необов'язкові поля скидаються до значень за замовчуванням.
    record.pop("description", None)
    record.update(listing_fields(body, photos))
    return to_listing(record)


@app.post("/listings/{listingId}/unpublish")
def unpublish_listing(listingId: str, body: ModerationReasonRequest, authorization: str | None = Header(None)):
    user = require_moderator(authorization)
    record = find_listing(listingId, user)
    if record["status"] == "UNPUBLISHED":
        raise ProblemError(409, "STATE_CONFLICT", "Оголошення вже зняте з публікації.")
    record["status"] = "UNPUBLISHED"
    record["unpublishedBy"] = "MODERATOR"
    return to_listing(record)


@app.post("/listings/{listingId}/publish")
def publish_listing(listingId: str, body: ModerationReasonRequest, authorization: str | None = Header(None)):
    user = require_moderator(authorization)
    record = find_listing(listingId, user)
    if record["status"] == "PUBLISHED":
        raise ProblemError(409, "STATE_CONFLICT", "Оголошення вже опубліковане.")
    if record["unpublishedBy"] != "MODERATOR":
        raise ProblemError(409, "STATE_CONFLICT", "Оголошення, зняте не модератором, повертається лише за оскарженням.")
    record["status"] = "PUBLISHED"
    record["unpublishedBy"] = None
    return to_listing(record)
