"""API-тести операцій Listings (api/openapi.yaml, тег Listings).

Обсяг і обмеження — logs/lab5-scope.md. Шляхи, коди відповідей і поля
взято лише з api/openapi.yaml; вимоги й AC — зі spec/srs.md (v1.1).
Дати бронювань — у далекому майбутньому, щоб не спрацьовувала CHECKIN_TOO_SOON (FR-07 №5).
"""

import base64
import struct
import uuid
import zlib

import pytest
from fastapi.testclient import TestClient

from src.main import app

MAX_PHOTO_BYTES = 5_242_880  # 5 × 1 048 576 (FR-02, ADD-01)


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png_photo(size=None):
    """Коректний PNG 1×1 у base64; `size` — точний розмір файлу в байтах (добирається приватним
    чанком)."""
    head = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    body = _chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
    tail = _chunk(b"IEND", b"")
    if size is not None:
        body += _chunk(b"prVt", b"\x00" * (size - len(head) - len(body) - len(tail) - 12))
    return base64.b64encode(head + body + tail).decode()


PNG_1X1 = png_photo()
# JPEG 1×1, згенерований Pillow.
JPEG_1X1 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0"
    "Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQID"
    "AAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlq"
    "c3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3"
    "+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEI"
    "FEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImK"
    "kpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3"
    "+iiigD//2Q=="
)
# GIF 1×1 — формат поза JPEG і PNG.
GIF_1X1 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(monkeypatch):
    """Засіває in-memory сховище токенів {token → userId, role} (lab5-scope.md, п. 11).

    Єдине місце, що спирається на реалізацію: розташування сховища `src.auth.TOKENS`.
    Ролі — значення `User.roles` з api/openapi.yaml.
    """
    from src import auth as auth_module

    def make(role):
        token = f"test-{role.lower()}-{uuid.uuid4()}"
        monkeypatch.setitem(auth_module.TOKENS, token, {"userId": str(uuid.uuid4()), "role": role})
        return {"Authorization": f"Bearer {token}"}

    return make


@pytest.fixture
def host(auth):
    return auth("HOST")


@pytest.fixture
def other_host(auth):
    return auth("HOST")


@pytest.fixture
def guest(auth):
    return auth("GUEST")


@pytest.fixture
def other_guest(auth):
    return auth("GUEST")


@pytest.fixture
def moderator(auth):
    return auth("MODERATOR")


def listing_request(**overrides):
    """ListingRequest без необов'язкових полів, якщо їх не передано явно."""
    body = {
        "title": "Поділ",
        "city": "Київ",
        "address": "вул. Сагайдачного, 1",
        "maxGuests": 4,
        "pricePerNight": "1234.56",
        "photos": [{"data": PNG_1X1}],
    }
    body.update(overrides)
    return body


def unique_city():
    return f"Місто-{uuid.uuid4().hex[:8]}"


def create_listing(client, headers, **overrides):
    response = client.post("/listings", json=listing_request(**overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def create_booking(client, headers, listing_id, check_in, check_out, guests_count=2):
    body = {
        "listingId": listing_id,
        "checkIn": check_in,
        "checkOut": check_out,
        "guestsCount": guests_count,
    }
    response = client.post("/bookings", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def confirm(client, headers, booking_id):
    response = client.post(f"/bookings/{booking_id}/confirm", headers=headers)
    assert response.status_code == 200
    return response.json()


def unpublish(client, headers, listing_id, reason="Фотографії не відповідають житлу."):
    return client.post(
        f"/listings/{listing_id}/unpublish", json={"reason": reason}, headers=headers
    )


def search_ids(client, **params):
    response = client.get("/listings", params=params)
    assert response.status_code == 200
    return [item["id"] for item in response.json()]


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code


@pytest.fixture
def listing(client, host):
    return create_listing(client, host)


def test_create_listing_returns_201(client, host):
    """FR-02; AC-02.1 (без опису створюється), AC-02.3 (значення за замовчуванням).

    Нове оголошення одразу в стані PUBLISHED (FR-02).
    """
    body = listing_request()

    response = client.post("/listings", json=body, headers=host)

    assert response.status_code == 201
    data = response.json()
    uuid.UUID(data["id"])
    for field in ("title", "city", "address", "maxGuests", "pricePerNight"):
        assert data[field] == body[field]
    assert len(data["photos"]) == 1
    assert {"id", "url"} <= data["photos"][0].keys()
    assert data["checkInTime"] == "14:00"
    assert data["checkOutTime"] == "11:00"
    assert data["turnoverNights"] == 0
    assert data["status"] == "PUBLISHED"
    assert data["averageRating"] is None


@pytest.mark.parametrize("missing", ["title", "address"])
def test_create_listing_without_required_field_returns_422(client, host, missing):
    """FR-02; AC-02.1 (оголошення без назви або без адреси не створюється)."""
    body = listing_request()
    del body[missing]

    response = client.post("/listings", json=body, headers=host)

    assert_problem(response, 422, "VALIDATION_FAILED")


@pytest.mark.parametrize(
    "photos",
    [[], [{"data": PNG_1X1}] * 11, [{"data": png_photo(MAX_PHOTO_BYTES + 1)}]],
    ids=["no-photos", "eleven-photos", "photo-5242881-bytes"],
)
def test_create_listing_with_invalid_photos_returns_422(client, host, photos):
    """FR-02; AC-02.1 (без фотографій, з 11 фотографіями або з файлом 5 242 881 байт —
    PHOTO_INVALID)."""
    response = client.post("/listings", json=listing_request(photos=photos), headers=host)

    assert_problem(response, 422, "PHOTO_INVALID")


def test_create_listing_with_photo_of_max_size_returns_201(client, host):
    """FR-02; AC-02.1 (фотографія розміром рівно 5 242 880 байтів приймається)."""
    response = client.post(
        "/listings",
        json=listing_request(photos=[{"data": png_photo(MAX_PHOTO_BYTES)}]),
        headers=host,
    )

    assert response.status_code == 201


@pytest.mark.parametrize("price", ["0.00", "1000000.01"])
def test_create_listing_with_invalid_price_returns_422(client, host, price):
    """FR-02; AC-02.2 (ціна 0,00 або 1 000 000,01 не приймається)."""
    response = client.post("/listings", json=listing_request(pricePerNight=price), headers=host)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "VALIDATION_FAILED"


@pytest.mark.parametrize("max_guests", [0, 21])
def test_create_listing_with_invalid_max_guests_returns_422(client, host, max_guests):
    """FR-02; AC-02.2 (максимальна кількість осіб 0 або 21 не приймається)."""
    response = client.post("/listings", json=listing_request(maxGuests=max_guests), headers=host)

    assert_problem(response, 422, "VALIDATION_FAILED")


@pytest.mark.parametrize(
    "field, value",
    [
        ("pricePerNight", "0.01"),
        ("pricePerNight", "1000000.00"),
        ("maxGuests", 1),
        ("maxGuests", 20),
    ],
)
def test_create_listing_with_boundary_values_returns_201(client, host, field, value):
    """FR-02; AC-02.2 (позитивна частина: 1, 20, 0,01 і 1 000 000,00 приймаються)."""
    response = client.post("/listings", json=listing_request(**{field: value}), headers=host)

    assert response.status_code == 201
    assert response.json()[field] == value


@pytest.mark.parametrize(
    "field, value", [("checkInTime", "21:00"), ("checkOutTime", "13:00"), ("turnoverNights", 2)]
)
def test_create_listing_with_invalid_times_returns_422(client, host, field, value):
    """FR-02; AC-02.3 (час заїзду 21:00, час виїзду 13:00 або перерва 2 не приймаються)."""
    response = client.post("/listings", json=listing_request(**{field: value}), headers=host)

    assert_problem(response, 422, "VALIDATION_FAILED")


def test_create_listing_with_null_description_returns_422(client, host):
    """FR-02; AC-02.1 (опис необов'язковий, але за `ListingRequest` це рядок: null не приймається,
    картка без поля `description` створюється)."""
    response = client.post("/listings", json=listing_request(description=None), headers=host)

    assert_problem(response, 422, "VALIDATION_FAILED")


@pytest.mark.parametrize("value", [False, True, "0", 0.5])
def test_create_listing_with_non_integer_turnover_returns_422(client, host, value):
    """FR-02; AC-02.3 (перерва — лише ціле 0 або 1 за `ListingRequest`; false, true, "0" і 0.5
    не приймаються)."""
    response = client.post("/listings", json=listing_request(turnoverNights=value), headers=host)

    assert_problem(response, 422, "VALIDATION_FAILED")


def test_create_listing_with_jpeg_and_png_returns_201(client, host):
    """FR-02; AC-02.6 (фотографії у форматах JPEG і PNG приймаються)."""
    response = client.post(
        "/listings",
        json=listing_request(photos=[{"data": JPEG_1X1}, {"data": PNG_1X1}]),
        headers=host,
    )

    assert response.status_code == 201
    assert len(response.json()["photos"]) == 2


def test_create_listing_with_unsupported_photo_format_returns_422(client, host):
    """FR-02; AC-02.6 (фотографія в іншому форматі — PHOTO_INVALID)."""
    response = client.post(
        "/listings", json=listing_request(photos=[{"data": GIF_1X1}]), headers=host
    )

    assert_problem(response, 422, "PHOTO_INVALID")


def test_create_listing_with_ten_max_size_photos_returns_201(client, host):
    """FR-02; AC-02.6 (картка з 10 фотографіями по 5 242 880 байтів зберігається)."""
    photo = png_photo(MAX_PHOTO_BYTES)

    response = client.post(
        "/listings", json=listing_request(photos=[{"data": photo}] * 10), headers=host
    )

    assert response.status_code == 201
    assert len(response.json()["photos"]) == 10


def test_create_listing_photo_invalid_creates_nothing(client, host):
    """FR-02; AC-02.7 (частково: після PHOTO_INVALID нове оголошення не створене).

    Запис WARN у журналі не перевіряється (lab5-scope.md, п. 9).
    """
    city = unique_city()

    response = client.post("/listings", json=listing_request(city=city, photos=[]), headers=host)

    assert_problem(response, 422, "PHOTO_INVALID")
    assert search_ids(client, city=city) == []


def test_create_listing_without_token_returns_401(client):
    """FR-02; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом createListing."""
    response = client.post("/listings", json=listing_request())

    assert_problem(response, 401, "UNAUTHENTICATED")


def test_create_listing_by_moderator_returns_403(client, moderator):
    """FR-02; AC — немає: модератор не створює оголошень — 403 FORBIDDEN (createListing)."""
    response = client.post("/listings", json=listing_request(), headers=moderator)

    assert_problem(response, 403, "FORBIDDEN")


def test_search_listings_returns_200(client, host):
    """FR-05; AC-02.4 (щойно створене оголошення знаходиться пошуком), AC-05.2 (місто без урахування
    регістру)."""
    city = unique_city()
    created = client.post("/listings", json=listing_request(city=city), headers=host).json()

    response = client.get("/listings", params={"city": city.lower()})

    assert response.status_code == 200
    results = response.json()
    assert [item["id"] for item in results] == [created["id"]]
    assert results[0]["status"] == "PUBLISHED"


def test_search_city_is_exact_match(client, host):
    """FR-05; AC-05.2 (частина про точний збіг: «Київська» не знаходить житла в місті «Київ»)."""
    city = unique_city()
    created = create_listing(client, host, city=city)

    assert search_ids(client, city=city.upper()) == [created["id"]]
    assert search_ids(client, city=f"{city}ська") == []


def test_search_excludes_listing_with_confirmed_overlap(client, host, guest):
    """FR-05, FR-08; AC-05.3 (частково: ніч діапазону зайнята бронюванням у CONFIRMED).

    Бронювання в COMPLETED і закриті ночі не перевіряються (lab5-scope.md, пп. 4, 10).
    """
    city = unique_city()
    listing = create_listing(client, host, city=city)
    confirm(
        client, host, create_booking(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"]
    )

    assert search_ids(client, city=city, checkIn="2030-06-11", checkOut="2030-06-13") == []
    assert search_ids(client, city=city, checkIn="2030-06-12", checkOut="2030-06-14") == [
        listing["id"]
    ]


def test_search_excludes_listing_in_turnover(client, host, guest):
    """FR-05, FR-08; AC-05.3 (частково: ніч діапазону зайнята перервою бронювання в CONFIRMED)."""
    city = unique_city()
    listing = create_listing(client, host, city=city, turnoverNights=1)
    confirm(
        client, host, create_booking(client, guest, listing["id"], "2030-06-10", "2030-06-12")["id"]
    )

    assert search_ids(client, city=city, checkIn="2030-06-12", checkOut="2030-06-13") == []
    assert search_ids(client, city=city, checkIn="2030-06-13", checkOut="2030-06-15") == [
        listing["id"]
    ]


def test_search_by_guests_count(client, host):
    """FR-05; AC-05.4 (житло з максимальною кількістю осіб 2 не з'являється в пошуку для 3 осіб)."""
    city = unique_city()
    listing = create_listing(client, host, city=city, maxGuests=2)

    assert search_ids(client, city=city, guestsCount=3) == []
    assert search_ids(client, city=city, guestsCount=2) == [listing["id"]]


# --- getListing --------------------------------------------------------------


def test_get_listing_returns_200(client, listing):
    """FR-02; AC-02.3 (оголошення має значення за замовчуванням).

    getListing доступна без входу для житла в стані PUBLISHED.
    """
    response = client.get(f"/listings/{listing['id']}")

    assert response.status_code == 200
    assert response.json() == listing


def test_get_listing_unknown_id_returns_404(client):
    """FR-02; AC — немає: відповідь 404 NOT_FOUND визначена контрактом getListing."""
    response = client.get(f"/listings/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "NOT_FOUND"


def test_get_unpublished_listing_visible_to_host_and_moderator_only(
    client, host, moderator, listing
):
    """FR-04; AC-04.6 (в описі getListing: без входу — лише PUBLISHED; власник бачить своє,
    модератор — будь-яке)."""
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    assert_problem(client.get(f"/listings/{listing['id']}"), 404, "NOT_FOUND")
    for headers in (host, moderator):
        response = client.get(f"/listings/{listing['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "UNPUBLISHED"


# --- replaceListing ----------------------------------------------------------


def test_replace_listing_returns_200(client, host, listing):
    """FR-02; AC-02.3 (значення в межах приймаються), AC-02.6 (наявна фотографія лишається за
    id)."""
    body = listing_request(
        description="Світла квартира біля Контрактової площі.",
        photos=[{"id": listing["photos"][0]["id"]}],
        checkInTime="16:00",
        checkOutTime="10:00",
        turnoverNights=1,
    )

    response = client.put(f"/listings/{listing['id']}", json=body, headers=host)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == listing["id"]
    assert data["description"] == body["description"]
    assert data["checkInTime"] == "16:00"
    assert data["checkOutTime"] == "10:00"
    assert data["turnoverNights"] == 1
    assert [photo["id"] for photo in data["photos"]] == [listing["photos"][0]["id"]]


def test_replace_listing_by_other_host_returns_403(client, other_host, listing):
    """FR-02; AC-02.5 (користувач не може редагувати чуже оголошення)."""
    body = listing_request(title="Чуже", photos=[{"id": listing["photos"][0]["id"]}])

    response = client.put(f"/listings/{listing['id']}", json=body, headers=other_host)

    assert_problem(response, 403, "FORBIDDEN")
    assert client.get(f"/listings/{listing['id']}").json() == listing


def test_replace_listing_photo_invalid_keeps_card(client, host, listing):
    """FR-02; AC-02.7 (частково: після PHOTO_INVALID наявна картка житла не змінена).

    Запис WARN у журналі не перевіряється (lab5-scope.md, п. 9).
    """
    body = listing_request(title="Нова назва", photos=[{"data": GIF_1X1}])

    response = client.put(f"/listings/{listing['id']}", json=body, headers=host)

    assert_problem(response, 422, "PHOTO_INVALID")
    assert client.get(f"/listings/{listing['id']}").json() == listing


def test_replace_listing_unknown_id_returns_404(client, host):
    """FR-02; AC — немає: відповідь 404 NOT_FOUND визначена контрактом replaceListing."""
    response = client.put(f"/listings/{uuid.uuid4()}", json=listing_request(), headers=host)

    assert_problem(response, 404, "NOT_FOUND")


def test_replace_listing_without_token_returns_401(client, listing):
    """FR-02; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом replaceListing."""
    body = listing_request(photos=[{"id": listing["photos"][0]["id"]}])

    response = client.put(f"/listings/{listing['id']}", json=body)

    assert_problem(response, 401, "UNAUTHENTICATED")


# --- unpublishListing --------------------------------------------------------


def test_unpublish_listing_returns_200(client, moderator, listing):
    """FR-04 (модератор знімає опубліковане оголошення з підставою; стан Unpublished)."""
    response = unpublish(client, moderator, listing["id"])

    assert response.status_code == 200
    assert response.json()["id"] == listing["id"]
    assert response.json()["status"] == "UNPUBLISHED"


@pytest.mark.parametrize("body", [{}, {"reason": ""}], ids=["no-reason", "empty-reason"])
def test_unpublish_listing_without_reason_returns_422(client, moderator, listing, body):
    """FR-04; AC-04.1 (зняття без підстави неможливе)."""
    response = client.post(f"/listings/{listing['id']}/unpublish", json=body, headers=moderator)

    assert_problem(response, 422, "VALIDATION_FAILED")
    assert client.get(f"/listings/{listing['id']}").json()["status"] == "PUBLISHED"


def test_unpublished_listing_hidden_from_search_and_booking(client, host, guest, moderator):
    """FR-04, FR-05; AC-04.2 (немає в пошуку, запит отримує LISTING_UNPUBLISHED), AC-05.1."""
    city = unique_city()
    listing = create_listing(client, host, city=city)
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    assert search_ids(client, city=city) == []
    body = {
        "listingId": listing["id"],
        "checkIn": "2030-06-10",
        "checkOut": "2030-06-12",
        "guestsCount": 2,
    }
    assert_problem(client.post("/bookings", json=body, headers=guest), 409, "LISTING_UNPUBLISHED")


def test_unpublish_rejects_pending_and_keeps_confirmed(
    client, host, guest, other_guest, moderator, listing
):
    """FR-04; AC-04.3 (частково: PENDING → REJECTED, підтверджене лишається в CONFIRMED).

    Операція повернення (lab5-scope.md, п. 5) і перехід у COMPLETED (п. 10) не перевіряються.
    """
    pending = create_booking(client, guest, listing["id"], "2030-06-10", "2030-06-12")
    confirmed = confirm(
        client,
        host,
        create_booking(client, other_guest, listing["id"], "2030-06-20", "2030-06-22")["id"],
    )

    assert unpublish(client, moderator, listing["id"]).status_code == 200

    assert client.get(f"/bookings/{pending['id']}", headers=guest).json()["status"] == "REJECTED"
    assert (
        client.get(f"/bookings/{confirmed['id']}", headers=other_guest).json()["status"]
        == "CONFIRMED"
    )


def test_unpublish_unpublished_listing_returns_409(client, moderator, listing):
    """FR-04; AC — немає: повторне зняття — 409 STATE_CONFLICT (unpublishListing)."""
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    assert_problem(unpublish(client, moderator, listing["id"]), 409, "STATE_CONFLICT")


def test_unpublish_unknown_listing_returns_404(client, moderator):
    """FR-04; AC — немає: відповідь 404 NOT_FOUND визначена контрактом unpublishListing."""
    assert_problem(unpublish(client, moderator, str(uuid.uuid4())), 404, "NOT_FOUND")


def test_unpublish_listing_by_host_returns_403(client, host, listing):
    """FR-04; AC — немає: дія доступна лише модератору — 403 FORBIDDEN (unpublishListing)."""
    assert_problem(unpublish(client, host, listing["id"]), 403, "FORBIDDEN")


def test_unpublish_listing_without_token_returns_401(client, listing):
    """FR-04; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом unpublishListing."""
    response = client.post(f"/listings/{listing['id']}/unpublish", json={"reason": "Підстава."})

    assert_problem(response, 401, "UNAUTHENTICATED")


# --- publishListing ----------------------------------------------------------


def test_publish_listing_by_moderator_returns_200(client, moderator, listing):
    """FR-04; AC-04.6 (модератор може повернути в публікацію оголошення, зняте модератором)."""
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    response = client.post(
        f"/listings/{listing['id']}/publish",
        json={"reason": "Власник замінив фотографії."},
        headers=moderator,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PUBLISHED"


def test_publish_listing_by_host_returns_403(client, host, moderator, listing):
    """FR-04; AC-04.6 (власник не може сам повернути в публікацію оголошення, зняте модератором)."""
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    response = client.post(
        f"/listings/{listing['id']}/publish", json={"reason": "Виправив."}, headers=host
    )

    assert_problem(response, 403, "FORBIDDEN")
    assert client.get(f"/listings/{listing['id']}", headers=host).json()["status"] == "UNPUBLISHED"


def test_publish_published_listing_returns_409(client, moderator, listing):
    """FR-04; AC — немає: оголошення вже опубліковане — 409 STATE_CONFLICT (publishListing)."""
    response = client.post(
        f"/listings/{listing['id']}/publish", json={"reason": "Підстава."}, headers=moderator
    )

    assert_problem(response, 409, "STATE_CONFLICT")


def test_publish_listing_without_reason_returns_422(client, moderator, listing):
    """FR-04; AC — немає: рішення без підстави — 422 VALIDATION_FAILED (publishListing)."""
    assert unpublish(client, moderator, listing["id"]).status_code == 200

    response = client.post(f"/listings/{listing['id']}/publish", json={}, headers=moderator)

    assert_problem(response, 422, "VALIDATION_FAILED")


def test_publish_listing_without_token_returns_401(client, listing):
    """FR-04; AC — немає: відповідь 401 UNAUTHENTICATED визначена контрактом publishListing."""
    response = client.post(f"/listings/{listing['id']}/publish", json={"reason": "Підстава."})

    assert_problem(response, 401, "UNAUTHENTICATED")
