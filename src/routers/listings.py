"""HTTP-маршрути операцій Listings (api/openapi.yaml, тег Listings)."""

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
    results = service.search(city, checkIn, checkOut, guestsCount, priceMin, priceMax, sort)
    page, total = service.paginate(results, limit, offset)
    response.headers["X-Total-Count"] = str(total)
    return [service.to_api(record) for record in page]


@router.post("/listings", status_code=201)
def create_listing(user: NonModerator, body: ListingRequest, request: Request):
    return service.to_api(service.create(user, body, str(request.base_url)))


@router.get("/listings/{listingId}")
def get_listing(listingId: str, user: OptionalUser):
    return service.to_api(service.get(listingId, user))


@router.put("/listings/{listingId}")
def replace_listing(listingId: str, user: User, body: ListingRequest, request: Request):
    return service.to_api(service.replace(listingId, user, body, str(request.base_url)))


@router.post("/listings/{listingId}/unpublish")
def unpublish_listing(listingId: str, user: Moderator, body: ModerationReasonRequest):
    return service.to_api(service.unpublish(listingId, user))


@router.post("/listings/{listingId}/publish")
def publish_listing(listingId: str, user: Moderator, body: ModerationReasonRequest):
    return service.to_api(service.publish(listingId, user))
