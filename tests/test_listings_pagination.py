"""API-тести пагінації searchListings (FR-ADD-02, spec/addenda/ADD-02.md).

Контракт: api/openapi.yaml, тег api-v1.1. Спільні умови AC-ADD-02.x відтворює фікстура
`catalog`. Замість міста «Пагінація» — унікальне місто, бо сховище спільне для всіх тестів.
"""
import pytest

from tests.test_listings import (  # noqa: F401 (auth, client, host — фікстури pytest)
    assert_problem,
    auth,
    client,
    create_listing,
    host,
    unique_city,
)

TOTAL = 25
FILTERED = 12  # оголошення з ціною 1,00–12,00 мають максимальну кількість осіб 4, решта — 2


def money(*values):
    return [f"{value}.00" for value in values]


def prices(response):
    return [item["pricePerNight"] for item in response.json()]


def total_count(response):
    """Значення заголовка без KeyError: відсутній заголовок має бути невдачею перевірки."""
    return response.headers.get("X-Total-Count")


@pytest.fixture
def catalog(client, host):
    """Спільні умови ADD-02 §3: 25 оголошень із цінами 1,00…25,00 в одному місті."""
    city = unique_city()
    for value in range(1, TOTAL + 1):
        create_listing(
            client,
            host,
            city=city,
            pricePerNight=f"{value}.00",
            maxGuests=4 if value <= FILTERED else 2,
        )
    return city


@pytest.fixture
def same_price_listings(client, host):
    """Дані AC-ADD-02.7: послідовно створені A (50,00), B (30,00) і C (30,00)."""
    city = unique_city()
    ids = {
        name: create_listing(client, host, city=city, pricePerNight=price)["id"]
        for name, price in (("A", "50.00"), ("B", "30.00"), ("C", "30.00"))
    }
    return city, ids


def names_in_order(response, ids):
    name_by_id = {listing_id: name for name, listing_id in ids.items()}
    return [name_by_id[item["id"]] for item in response.json()]


def test_limit_restricts_number_of_items(client, catalog):
    """AC-ADD-02.1: `limit` обмежує кількість елементів."""
    response = client.get("/listings", params={"city": catalog, "limit": 10})

    assert response.status_code == 200
    assert len(response.json()) == 10

    response = client.get("/listings", params={"city": catalog, "limit": 100})

    assert response.status_code == 200
    assert len(response.json()) == TOTAL


def test_offset_skips_first_items(client, catalog):
    """AC-ADD-02.2: `offset` пропускає перші N."""
    response = client.get(
        "/listings", params={"city": catalog, "sort": "price_asc", "offset": 5, "limit": 10}
    )

    assert response.status_code == 200
    assert prices(response) == money(*range(6, 16))


def test_total_count_does_not_depend_on_limit_and_offset(client, catalog):
    """AC-ADD-02.3: `X-Total-Count` не залежить від `limit` і `offset`; за межами результату — порожній масив."""
    variants = ({"limit": 10}, {"limit": 5, "offset": 20}, {"offset": 30}, {})

    responses = [client.get("/listings", params={"city": catalog, **variant}) for variant in variants]

    assert [response.status_code for response in responses] == [200] * len(variants)
    assert [total_count(response) for response in responses] == [str(TOTAL)] * len(variants)
    assert responses[2].json() == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}],
    ids=["limit=0", "limit=101", "offset=-1"],
)
def test_out_of_range_values_are_rejected(client, params):
    """AC-ADD-02.4: значення поза межами дають 422 `VALIDATION_FAILED`."""
    response = client.get("/listings", params={"city": unique_city(), **params})

    assert_problem(response, 422, "VALIDATION_FAILED")


@pytest.mark.parametrize(
    "params",
    [{"limit": 1}, {"limit": 100}, {"offset": 0}],
    ids=["limit=1", "limit=100", "offset=0"],
)
def test_boundary_values_are_accepted(client, params):
    """AC-ADD-02.4: граничні значення `limit=1`, `limit=100` і `offset=0` приймаються."""
    response = client.get("/listings", params={"city": unique_city(), **params})

    assert response.status_code == 200


def test_default_limit_without_pagination_params(client, catalog):
    """AC-ADD-02.5: без параметрів діє `limit` 20, фільтри й сортування не змінюються."""
    response = client.get("/listings", params={"city": catalog})

    assert response.status_code == 200
    assert len(response.json()) == 20
    assert total_count(response) == str(TOTAL)

    response = client.get(
        "/listings", params={"city": catalog, "guestsCount": 3, "sort": "price_desc"}
    )

    assert response.status_code == 200
    assert prices(response) == money(*range(FILTERED, 0, -1))
    assert total_count(response) == str(FILTERED)


def test_pagination_applies_after_filters_and_sort(client, catalog):
    """AC-ADD-02.6: пагінація застосовується після фільтрів і сортування."""
    response = client.get(
        "/listings",
        params={"city": catalog, "guestsCount": 3, "sort": "price_desc", "offset": 5, "limit": 5},
    )

    assert response.status_code == 200
    assert prices(response) == money(7, 6, 5, 4, 3)
    assert total_count(response) == str(FILTERED)


@pytest.mark.parametrize(
    ("sort", "expected"),
    [(None, ["A", "B", "C"]), ("price_asc", ["B", "C", "A"]), ("price_desc", ["A", "B", "C"])],
    ids=["no-sort", "price_asc", "price_desc"],
)
def test_order_is_stable_for_equal_prices(client, same_price_listings, sort, expected):
    """AC-ADD-02.7: без `sort` і для рівних цін порядок — за моментом створення."""
    city, ids = same_price_listings
    params = {"city": city} if sort is None else {"city": city, "sort": sort}

    response = client.get("/listings", params=params)

    assert response.status_code == 200
    assert names_in_order(response, ids) == expected


def test_page_follows_creation_order(client, same_price_listings):
    """AC-ADD-02.7: без `sort` із `limit=1&offset=1` відповідь містить лише B."""
    city, ids = same_price_listings

    response = client.get("/listings", params={"city": city, "limit": 1, "offset": 1})

    assert response.status_code == 200
    assert names_in_order(response, ids) == ["B"]
