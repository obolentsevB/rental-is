"""HTTP-маршрути операцій Listings (api/openapi.yaml, тег Listings).

Docstring кожного обробника починається із символу form feed. FastAPI відкидає текст після
цього символу, тому внутрішні секції не потрапляють в OpenAPI: опис операцій задає контракт.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from src.auth import Moderator, NonModerator, OptionalUser, User
from src.schemas import ListingRequest, ListingSort, ModerationReasonRequest, MoneyFilter
from src.services import listings as service

router = APIRouter()


@router.get("/listings")
def search_listings(
    response: Response,
    city: str | None = None,
    checkIn: date | None = None,
    checkOut: date | None = None,
    guestsCount: Annotated[int | None, Query(ge=1)] = None,
    priceMin: MoneyFilter = None,
    priceMax: MoneyFilter = None,
    sort: ListingSort | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """\fШукає опубліковане житло за фільтрами (searchListings, FR-05, FR-ADD-02).

    Args:
        response: Відповідь, у яку записується заголовок `X-Total-Count`.
        city: Місто, порівнюється без урахування регістру.
        checkIn: Дата заїзду, задається разом із `checkOut`.
        checkOut: Дата виїзду.
        guestsCount: Кількість осіб, не менше 1.
        priceMin: Нижня межа ціни за ніч.
        priceMax: Верхня межа ціни за ніч.
        sort: Порядок результату: price_asc, price_desc або rating_desc.
        limit: Розмір сторінки, від 1 до 100.
        offset: Кількість пропущених записів.

    Returns:
        Сторінку записів за схемою Listing.

    Raises:
        ProblemError: VALIDATION_FAILED, якщо задано лише одну дату або діапазон порожній.
    """
    results = service.search(city, checkIn, checkOut, guestsCount, priceMin, priceMax, sort)
    page, total = service.paginate(results, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    return [service.to_api(record) for record in page]


@router.post("/listings", status_code=201)
def create_listing(user: NonModerator, body: ListingRequest, request: Request):
    """\fПублікує нове житло (createListing, FR-02).

    Args:
        user: Автор оголошення, стає його власником.
        body: Картка житла.
        request: Запит, з якого беруть базову адресу для URL фотографій.

    Returns:
        Запис за схемою Listing, відповідь має статус 201.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, FORBIDDEN для модератора, PHOTO_INVALID за
            порушення вимог до фотографій.
    """
    return service.to_api(service.create(user, body, str(request.base_url)))


@router.get("/listings/{listingId}")
def get_listing(listingId: str, user: OptionalUser):
    """\fПовертає картку житла (getListing, FR-02, AC-04.6).

    Args:
        listingId: Ідентифікатор житла.
        user: Користувач або None для незареєстрованого відвідувача.

    Returns:
        Запис за схемою Listing.

    Raises:
        ProblemError: NOT_FOUND, якщо житла немає або воно недоступне цьому користувачу.
    """
    return service.to_api(service.get(listingId, user))


@router.put("/listings/{listingId}")
def replace_listing(listingId: str, user: User, body: ListingRequest, request: Request):
    """\fПовністю замінює картку житла (replaceListing, FR-02).

    Args:
        listingId: Ідентифікатор житла.
        user: Користувач, що редагує картку; має бути її власником.
        body: Нова картка житла.
        request: Запит, з якого беруть базову адресу для URL фотографій.

    Returns:
        Оновлений запис за схемою Listing.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, NOT_FOUND для недоступного житла, FORBIDDEN для
            не власника, PHOTO_INVALID за порушення вимог до фотографій.
    """
    return service.to_api(service.replace(listingId, user, body, str(request.base_url)))


@router.post("/listings/{listingId}/unpublish")
def unpublish_listing(listingId: str, user: Moderator, body: ModerationReasonRequest):
    """\fЗнімає житло з публікації рішенням модератора (unpublishListing, FR-04).

    Args:
        listingId: Ідентифікатор житла.
        user: Модератор.
        body: Підстава рішення; схема її перевіряє, але сервіс не зберігає.

    Returns:
        Оновлений запис за схемою Listing.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, FORBIDDEN не для модератора, NOT_FOUND, якщо
            житла немає, STATE_CONFLICT, якщо воно вже зняте.
    """
    return service.to_api(service.unpublish(listingId, user))


@router.post("/listings/{listingId}/publish")
def publish_listing(listingId: str, user: Moderator, body: ModerationReasonRequest):
    """\fПовертає в публікацію житло, зняте модератором (publishListing, FR-04).

    Args:
        listingId: Ідентифікатор житла.
        user: Модератор.
        body: Підстава рішення; схема її перевіряє, але сервіс не зберігає.

    Returns:
        Оновлений запис за схемою Listing.

    Raises:
        ProblemError: UNAUTHENTICATED без входу, FORBIDDEN не для модератора, NOT_FOUND, якщо
            житла немає, STATE_CONFLICT, якщо воно вже опубліковане або зняте не модератором.
    """
    return service.to_api(service.publish(listingId, user))
