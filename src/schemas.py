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
    """Базова модель тіла запиту: невідомі поля дають VALIDATION_FAILED."""

    model_config = ConfigDict(extra="forbid")


class NewPhoto(RequestModel):
    """Нова фотографія картки житла в base64 (FR-02)."""

    data: str


class ExistingPhoto(RequestModel):
    """Наявна фотографія картки житла за ідентифікатором (FR-02)."""

    id: uuid.UUID


class ListingRequest(RequestModel):
    """Картка житла для createListing і replaceListing (FR-02)."""

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
        """Перевіряє межі ціни за ніч (FR-02).

        Args:
            value: Ціна, що вже відповідає `MONEY_PATTERN`.

        Returns:
            Незмінене значення.

        Raises:
            ValueError: Якщо ціна поза межами 0.01–1000000.00; клієнт отримує VALIDATION_FAILED.
        """
        if not Decimal("0.01") <= Decimal(value) <= Decimal("1000000.00"):
            raise ValueError("від 0.01 до 1000000.00 включно")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def description_not_null(cls, value: object) -> object:
        """Відхиляє явний null в описі (FR-02, AC-02.1).

        Опис необов'язковий: картка без поля `description` приймається, бо значення за
        замовчуванням не валідується. За контрактом поле має тип лише `string`.

        Args:
            value: Значення з тіла запиту.

        Returns:
            Незмінене значення для подальшої перевірки.

        Raises:
            ValueError: Якщо передано null; клієнт отримує VALIDATION_FAILED.
        """
        if value is None:
            raise ValueError("опис має бути рядком; щоб не задавати опис, не передавайте поле")
        return value

    @field_validator("turnoverNights", mode="before")
    @classmethod
    def turnover_is_integer(cls, value: object) -> object:
        """Відхиляє булеві значення технологічної перерви (FR-02, AC-02.3).

        `Literal[0, 1]` сам приймає `false` і `true` як 0 і 1, бо в Python `bool` — підтип `int`.
        Контракт допускає лише цілі 0 і 1.

        Args:
            value: Значення з тіла запиту до перевірки `Literal`.

        Returns:
            Незмінене значення для подальшої перевірки.

        Raises:
            ValueError: Якщо значення булеве; клієнт отримує VALIDATION_FAILED.
        """
        if isinstance(value, bool):
            raise ValueError("має бути ціле число 0 або 1")
        return value


class ModerationReasonRequest(RequestModel):
    """Підстава рішення модератора (publishListing, unpublishListing, FR-04)."""

    reason: NonEmptyStr


class BookingRequest(RequestModel):
    """Порядок дат і межі guestsCount схема не обмежує: це коди FR-07 (createBooking)."""

    listingId: uuid.UUID
    checkIn: date
    checkOut: date
    guestsCount: StrictInt
