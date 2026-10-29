# TEST-GATE (база): API-тести Listing і Booking до реалізації

| Параметр | Значення |
|----------|----------|
| Дата | 2026-10-29 |
| Коміт | `9ee2e83` |
| Обсяг | [`logs/lab5-scope.md`](lab5-scope.md) |
| Контракт | `api/openapi.yaml`, тег `api-v1.0` |
| Тести | `tests/test_listings.py` (40 функцій, 51 кейс), `tests/test_bookings.py` (9 функцій, 9 кейсів) |
| Реалізація | `src/main.py`: лише `app = FastAPI(title="rental-is")`, маршрутів немає |
| Середовище | Python 3.14.3, pytest 9.2.0 |

## Тести

Тип визначено за таким принципом:
- позитивний — дія вдається;
- негативний — відмова;
- граничний — значення на межі або поруч із нею.

Вимога й AC — за результатами рев'ю проти `spec/srs.md`. «AC — немає» означає, що код відповіді визначено лише контрактом.

### tests/test_listings.py

| Тест | Вимога | AC | Тип |
|------|--------|----|-----|
| `test_create_listing_returns_201` | FR-02 | AC-02.1 (без опису), AC-02.3 (значення за замовчуванням) | позитивний |
| `test_create_listing_without_required_field_returns_422` ×2 | FR-02 | AC-02.1 | негативний |
| `test_create_listing_with_invalid_photos_returns_422` ×3 | FR-02 | AC-02.1 | негативний (0 фото), граничний (11 фото, 5 242 881 байт) |
| `test_create_listing_with_photo_of_max_size_returns_201` | FR-02 | AC-02.1 | граничний |
| `test_create_listing_with_invalid_price_returns_422` ×2 | FR-02 | AC-02.2 | граничний |
| `test_create_listing_with_invalid_max_guests_returns_422` ×2 | FR-02 | AC-02.2 | граничний |
| `test_create_listing_with_boundary_values_returns_201` ×4 | FR-02 | AC-02.2 | граничний |
| `test_create_listing_with_invalid_times_returns_422` ×3 | FR-02 | AC-02.3 | граничний |
| `test_create_listing_with_jpeg_and_png_returns_201` | FR-02 | AC-02.6 | позитивний |
| `test_create_listing_with_unsupported_photo_format_returns_422` | FR-02 | AC-02.6 | негативний |
| `test_create_listing_with_ten_max_size_photos_returns_201` | FR-02 | AC-02.6 | граничний |
| `test_create_listing_photo_invalid_creates_nothing` | FR-02 | AC-02.7 (без журналу) | негативний |
| `test_create_listing_without_token_returns_401` | FR-02 | — | негативний |
| `test_create_listing_by_moderator_returns_403` | FR-02 | — | негативний |
| `test_search_listings_returns_200` | FR-02, FR-05 | AC-02.4, AC-05.2 (регістр) | позитивний |
| `test_search_city_is_exact_match` | FR-05 | AC-05.2 (точний збіг) | позитивний і негативний |
| `test_search_excludes_listing_with_confirmed_overlap` | FR-05, FR-08 | AC-05.3 (частково) | граничний |
| `test_search_excludes_listing_in_turnover` | FR-05, FR-08 | AC-05.3 (частково) | граничний |
| `test_search_by_guests_count` | FR-05 | AC-05.4 | граничний |
| `test_get_listing_returns_200` | FR-02 | AC-02.3 | позитивний |
| `test_get_listing_unknown_id_returns_404` | FR-02 | — | негативний |
| `test_get_unpublished_listing_visible_to_host_and_moderator_only` | FR-04 | AC-04.6 | позитивний і негативний |
| `test_replace_listing_returns_200` | FR-02 | AC-02.3 (позитивна частина) | позитивний |
| `test_replace_listing_by_other_host_returns_403` | FR-02 | AC-02.5 | негативний |
| `test_replace_listing_photo_invalid_keeps_card` | FR-02 | AC-02.7 (без журналу) | негативний |
| `test_replace_listing_unknown_id_returns_404` | FR-02 | — | негативний |
| `test_replace_listing_without_token_returns_401` | FR-02 | — | негативний |
| `test_unpublish_listing_returns_200` | FR-04 | — | позитивний |
| `test_unpublish_listing_without_reason_returns_422` ×2 | FR-04 | AC-04.1 | негативний |
| `test_unpublished_listing_hidden_from_search_and_booking` | FR-04, FR-05 | AC-04.2, AC-05.1 | негативний |
| `test_unpublish_rejects_pending_and_keeps_confirmed` | FR-04 | AC-04.3 (частково) | позитивний |
| `test_unpublish_unpublished_listing_returns_409` | FR-04 | — | негативний |
| `test_unpublish_unknown_listing_returns_404` | FR-04 | — | негативний |
| `test_unpublish_listing_by_host_returns_403` | FR-04 | — | негативний |
| `test_unpublish_listing_without_token_returns_401` | FR-04 | — | негативний |
| `test_publish_listing_by_moderator_returns_200` | FR-04 | AC-04.6 | позитивний |
| `test_publish_listing_by_host_returns_403` | FR-04 | AC-04.6 | негативний |
| `test_publish_published_listing_returns_409` | FR-04 | — | негативний |
| `test_publish_listing_without_reason_returns_422` | FR-04 | — | негативний |
| `test_publish_listing_without_token_returns_401` | FR-04 | — | негативний |

Docstring двох тестів розходяться з рев'ю:
- `test_search_listings_returns_200`: у docstring лише FR-05, а AC-02.4 належить до FR-02;
- `test_replace_listing_returns_200`: docstring заявляє AC-02.6, але тест його не перевіряє. AC-02.6 покривають три окремі тести.

Таблиця відображає фактичне покриття.

### tests/test_bookings.py

| Тест | Вимога | AC | Тип |
|------|--------|----|-----|
| `test_create_booking_returns_201` | FR-06, FR-15 | AC-06.1 (без операції оплати), AC-15.1 | позитивний |
| `test_create_booking_checkout_not_after_checkin_returns_422` ×2 | FR-07 | AC-07.1 (підстава №1, MIN_NIGHTS) | граничний (рівні дати), негативний (виїзд раніше) |
| `test_create_booking_with_max_guests_returns_201` | FR-07 | AC-07.3 | граничний |
| `test_create_booking_above_max_guests_returns_422` | FR-07 | AC-07.3 | граничний |
| `test_create_booking_unknown_listing_returns_404` | FR-06 | — | негативний |
| `test_create_booking_overlapping_confirmed_returns_409` | FR-07, FR-08 | AC-08.2 (без журналу) | негативний |
| `test_get_booking_returns_200` | FR-12 | AC-12.5 (позитивна частина) | позитивний |
| `test_cancel_booking_returns_200` | FR-13 | AC-13.6 | позитивний |

## Запуск pytest

```
python -m pytest -q
2 failed, 1 warning, 58 errors in 0.96s
```

Зібрано 60 кейсів: 0 passed, 2 failed, 58 errors.

| Результат | Кейсів | Причина |
|-----------|--------|---------|
| error (setup) | 58 | Фікстура `auth` імпортує `src.auth`: `ImportError: cannot import name 'auth' from 'src'`. Сховища токенів (lab5-scope.md, п. 11) ще немає |
| failed | 1 | `test_create_listing_without_token_returns_401`: `assert 404 == 401`, бо маршруту `POST /listings` немає |
| failed | 1 | `test_get_listing_unknown_id_returns_404`: статус 404 збігся випадково (маршруту немає), але тіло — `application/json` від FastAPI, а не `application/problem+json` зі схемою `Problem` |

Причина падінь очікувана: реалізації немає. Помилок у тестах немає. Жоден кейс не падає через синтаксис, некоректні дані чи хибне очікування щодо контракту:
- усі 58 errors — це один і той самий відсутній модуль;
- обидва failed отримують відповідь застосунку без маршрутів.

Тести виконуються до кінця і впираються саме у відсутню поведінку, тобто перебувають у червоній фазі TDD (NFR-02).

Попередження `StarletteDeprecationWarning` (httpx → httpx2) стосується версії залежностей, а не тестів.

## Повнота покриття

### Listing — повне в межах обсягу

Покрито всі AC операцій Listings зі статусом «Входить» або «Частково», для яких спосіб перевірки — API-тест:
AC-02.1–02.7, AC-04.1, 04.2, 04.3, 04.6, AC-05.1–05.4.

Для кожної з чотирьох операцій із входом перевірено 401, 403 для недозволеної ролі, а також 404, 409 і 422 там, де їх визначає контракт.

AC зі статусом «Не входить» (AC-04.4, 04.5, 05.5, 15.8, 18.4, 22.8, 23.1) не покрито свідомо.

### Booking — часткове

Покрито AC-06.1, AC-07.1 (лише MIN_NIGHTS), AC-07.3, AC-08.2, AC-12.5 (позитивна частина), AC-13.6, AC-15.1. Окремо в `test_listings.py` покрито LISTING_UNPUBLISHED (AC-04.2).

Не покрито AC, для яких зведення в lab5-scope.md передбачає API-тест:

| Операція | Не покриті AC |
|----------|---------------|
| `createBooking` | AC-06.2, 06.4, 06.5, 06.7; AC-07.1 (OWN_LISTING); AC-07.4; AC-08.1, 08.3, 08.4, 08.7, 08.9 |
| `confirmBooking`, `rejectBooking` | AC-09.1, 09.2, 09.3, 09.4, 09.5, 09.7; AC-N01.1, N01.3 |
| `listBookings`, `getBooking` | AC-12.1, 12.2, 12.4; AC-12.5 (негативна частина) |
| `cancelBooking` | AC-13.5 |
| Усі операції Bookings | 401 без токена, 403 для недозволеної ролі |

Модульних тестів для AC з модульним способом перевірки ще немає:
- AC-06.6, AC-07.2, AC-08.5, AC-12.3, AC-13.1–13.4;
- причина конфлікту в AC-08.2–08.4;
- ACCOUNT_BLOCKED у AC-07.1;
- COMPLETED у AC-13.5.

Ці тести пишуться разом із сервісним шаром.

## Рішення

TEST-GATE: GO
