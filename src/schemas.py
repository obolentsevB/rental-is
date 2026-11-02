"""Схеми запитів і спільні обмеження полів за api/openapi.yaml."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

MONEY_PATTERN = r"^\d+\.\d{2}$"

Money = Annotated[str, Field(pattern=MONEY_PATTERN)]
MoneyFilter = Annotated[str | None, Query(pattern=MONEY_PATTERN)]
NonEmptyStr = Annotated[str, Field(min_length=1)]
ListingSort = Literal["price_asc", "price_desc", "rating_desc"]
BookingListRole = Literal["guest", "owner"]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewPhoto(RequestModel):
    data: str


class ExistingPhoto(RequestModel):
    id: uuid.UUID


class ListingRequest(RequestModel):
    title: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str, Field(max_length=2000)] | None = None
    city: NonEmptyStr
    address: NonEmptyStr
    maxGuests: Annotated[StrictInt, Field(ge=1, le=20)]
    pricePerNight: Money
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


class ModerationReasonRequest(RequestModel):
    reason: NonEmptyStr


class BookingRequest(RequestModel):
    """Порядок дат і межі guestsCount схема не обмежує: це коди FR-07 (createBooking)."""

    listingId: uuid.UUID
    checkIn: date
    checkOut: date
    guestsCount: StrictInt
