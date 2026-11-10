# Верифікація реалізації: обсяг Лаб 5 і FR-ADD-02

| Параметр | Значення |
|----------|----------|
| Дата | 2026-11-10 |
| Коміт | `6dee34b` |
| Контракт | `api/openapi.yaml`, тег `api-v1.1` (файл збігається з тегом) |
| Обсяг | [`logs/lab5-scope.md`](lab5-scope.md): 12 операцій Listings і Bookings, 59 AC (47 «Входить», 12 «Частково») |
| Адендум | [`spec/addenda/ADD-02.md`](../spec/addenda/ADD-02.md), тікет #114 |
| Результат | **PASSED:** усі 59 AC обсягу, 158 із 158 тестів, контрактна перевірка для трьох ролей |

Статуси в таблицях узято з виводу `pytest -v`. Тести для кожного AC визначено читанням їхнього коду й звіркою з текстом AC у `spec/srs.md`, а не за докстрінгами. Перелік AC обсягу збігається з `x-acceptance-criteria` 12 операцій контракту.

## Звірка вимог

Код: `src/routers/listings.py`, `src/routers/bookings.py`, `src/services/listings.py`, `src/services/bookings.py`, `src/auth.py`.

| Вимога | AC (Входить/Частково) | Тест(и) | Результат | Відповідність OpenAPI |
|--------|-----------------------|---------|-----------|-----------------------|
| FR-02 | AC-02.1 (Входить) | `test_listings.py::test_create_listing_returns_201` — PASSED<br>`test_listings.py::test_create_listing_without_required_field_returns_422` ×2 — PASSED<br>`test_listings.py::test_create_listing_with_invalid_photos_returns_422` ×3 — PASSED<br>`test_listings.py::test_create_listing_with_photo_of_max_size_returns_201` — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.2 (Входить) | `test_listings.py::test_create_listing_with_invalid_price_returns_422` ×2 — PASSED<br>`test_listings.py::test_create_listing_with_invalid_max_guests_returns_422` ×2 — PASSED<br>`test_listings.py::test_create_listing_with_boundary_values_returns_201` ×4 — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.3 (Входить) | `test_listings.py::test_create_listing_returns_201` — PASSED<br>`test_listings.py::test_create_listing_with_invalid_times_returns_422` ×3 — PASSED<br>`test_listings.py::test_get_listing_returns_200` — PASSED<br>`test_listings.py::test_replace_listing_returns_200` — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.4 (Входить) | `test_listings.py::test_search_listings_returns_200` — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.5 (Входить) | `test_listings.py::test_replace_listing_by_other_host_returns_403` — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.6 (Входить) | `test_listings.py::test_create_listing_with_jpeg_and_png_returns_201` — PASSED<br>`test_listings.py::test_create_listing_with_unsupported_photo_format_returns_422` — PASSED<br>`test_listings.py::test_create_listing_with_ten_max_size_photos_returns_201` — PASSED | **PASSED** | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-02 | AC-02.7 (Частково) | `test_listings.py::test_create_listing_photo_invalid_creates_nothing` — PASSED<br>`test_listings.py::test_replace_listing_photo_invalid_keeps_card` — PASSED | **PASSED** у межах обсягу. Те, що картку не створено і не змінено, перевіряється; запис WARN у журналі — ні, бо Events поза обсягом | `createListing`, `getListing`, `replaceListing`: 200/201, 401, 403, 404, 422 перевірено; 403 `ACCOUNT_BLOCKED` не моделюється |
| FR-04 | AC-04.1 (Входить) | `test_listings.py::test_unpublish_listing_without_reason_returns_422` ×2 — PASSED | **PASSED** | `unpublishListing`, `publishListing`: 200, 401, 403, 409, 422 перевірено; 404 — лише для `unpublishListing` |
| FR-04 | AC-04.2 (Входить) | `test_listings.py::test_unpublished_listing_hidden_from_search_and_booking` — PASSED | **PASSED** | `unpublishListing`, `publishListing`: 200, 401, 403, 409, 422 перевірено; 404 — лише для `unpublishListing` |
| FR-04 | AC-04.3 (Частково) | `test_listings.py::test_unpublish_rejects_pending_and_keeps_confirmed` — PASSED | **PASSED** у межах обсягу. PENDING → REJECTED і збереження CONFIRMED — так; операція повернення — ні (п. 5); перехід у COMPLETED у момент виїзду — ні, бо FR-11 — автоматична дія поза операціями обсягу | `unpublishListing`, `publishListing`: 200, 401, 403, 409, 422 перевірено; 404 — лише для `unpublishListing` |
| FR-04 | AC-04.6 (Входить) | `test_listings.py::test_get_unpublished_listing_visible_to_host_and_moderator_only` — PASSED<br>`test_listings.py::test_publish_listing_by_moderator_returns_200` — PASSED<br>`test_listings.py::test_publish_listing_by_host_returns_403` — PASSED | **PASSED** | `unpublishListing`, `publishListing`: 200, 401, 403, 409, 422 перевірено; 404 — лише для `unpublishListing` |
| FR-05 | AC-05.1 (Входить) | `test_listings.py::test_unpublished_listing_hidden_from_search_and_booking` — PASSED | **PASSED** | `searchListings`: 200, 422 перевірено |
| FR-05 | AC-05.2 (Входить) | `test_listings.py::test_search_listings_returns_200` — PASSED<br>`test_listings.py::test_search_city_is_exact_match` — PASSED | **PASSED** | `searchListings`: 200, 422 перевірено |
| FR-05 | AC-05.3 (Частково) | `test_listings.py::test_search_excludes_listing_with_confirmed_overlap` — PASSED<br>`test_listings.py::test_search_excludes_listing_in_turnover` — PASSED<br>`test_booking_clock.py::test_search_excludes_listing_with_completed_booking` — PASSED | **PASSED** у межах обсягу. Бронювання CONFIRMED і перерва — API; COMPLETED — модульний тест; закриті ночі — ні (п. 4) | `searchListings`: 200, 422 перевірено |
| FR-05 | AC-05.4 (Входить) | `test_listings.py::test_search_by_guests_count` — PASSED | **PASSED** | `searchListings`: 200, 422 перевірено |
| FR-06 | AC-06.1 (Частково) | `test_bookings.py::test_create_booking_returns_201` — PASSED | **PASSED** у межах обсягу. PENDING, дати й кількість осіб — так; операція оплати — ні (п. 5) | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-06 | AC-06.2 (Входить) | `test_bookings.py::test_two_guests_pending_on_same_nights` — PASSED | **PASSED** | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-06 | AC-06.4 (Входить) | `test_bookings.py::test_booking_keeps_terms_after_listing_change` — PASSED<br>`test_booking_clock.py::test_refund_scale_uses_check_in_time_fixed_at_creation` — PASSED | **PASSED** | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-06 | AC-06.5 (Входить) | `test_bookings.py::test_new_request_after_turnover_change_on_previous_checkout` — PASSED | **PASSED** | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-06 | AC-06.6 (Входить) | `test_commission_config.py::test_commission_change_applies_only_to_new_requests` — PASSED | **PASSED** | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-06 | AC-06.7 (Входить) | `test_bookings.py::test_confirmed_booking_keeps_terms_from_creation` — PASSED | **PASSED** | `createBooking`: 201, 401, 403, 404 перевірено; поля схеми `Booking` |
| FR-07 | AC-07.1 (Частково) | `test_bookings.py::test_create_booking_checkout_not_after_checkin_returns_422` ×2 — PASSED<br>`test_bookings.py::test_create_booking_own_listing_returns_403` — PASSED<br>`test_bookings.py::test_create_booking_with_zero_guests_returns_422` — PASSED<br>`test_bookings.py::test_create_booking_with_past_check_in_returns_422` — PASSED<br>`test_bookings.py::test_fr07_checks_order` ×5 — PASSED<br>`test_bookings.py::test_refused_request_creates_no_booking` ×6 — PASSED | **PASSED** у межах обсягу. Код і відсутність бронювання за підставами 1–6 — так; ACCOUNT_BLOCKED (підстава 0) — ні, блокування не моделюється (п. 11); платіжних операцій немає за п. 5; запис WARN у журналі — ні | `createBooking`: коди й порядок FR-07, крім `ACCOUNT_BLOCKED` |
| FR-07 | AC-07.2 (Входить) | `test_booking_clock.py::test_checkin_too_soon_boundary` — PASSED | **PASSED** | `createBooking`: коди й порядок FR-07, крім `ACCOUNT_BLOCKED` |
| FR-07 | AC-07.3 (Входить) | `test_bookings.py::test_create_booking_with_max_guests_returns_201` — PASSED<br>`test_bookings.py::test_create_booking_above_max_guests_returns_422` — PASSED | **PASSED** | `createBooking`: коди й порядок FR-07, крім `ACCOUNT_BLOCKED` |
| FR-07 | AC-07.4 (Входить) | `test_bookings.py::test_fr07_checks_order` ×5 — PASSED | **PASSED** | `createBooking`: коди й порядок FR-07, крім `ACCOUNT_BLOCKED` |
| FR-08 | AC-08.1 (Входить) | `test_bookings.py::test_check_in_on_previous_checkout_is_created` — PASSED | **PASSED** | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.2 (Частково) | `test_bookings.py::test_create_booking_overlapping_confirmed_returns_409` — PASSED | **PASSED** у межах обсягу. Код і `conflictingBookingIds` — так; причина конфлікту (`conflictReasons`) є лише в журналі, Events поза обсягом (п. 9) | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.3 (Частково) | `test_bookings.py::test_night_in_booking_turnover_returns_409` — PASSED | **PASSED** у межах обсягу. Як AC-08.2 | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.4 (Частково) | `test_bookings.py::test_new_request_turnover_covering_check_in_returns_409` — PASSED | **PASSED** у межах обсягу. Як AC-08.2 | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.5 (Частково) | `test_booking_clock.py::test_turnover_remains_after_completion` — PASSED | **PASSED** у межах обсягу. Перехід у COMPLETED, код і ідентифікатор B — так; причина — ні, як AC-08.2 | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.7 (Входить) | `test_bookings.py::test_pending_request_does_not_block_same_nights` — PASSED | **PASSED** | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-08 | AC-08.9 (Входить) | `test_bookings.py::test_night_after_turnover_is_available` — PASSED | **PASSED** | `createBooking`: 201, 409 `DATES_UNAVAILABLE` із `conflictingBookingIds` |
| FR-09 | AC-09.1 (Частково) | `test_bookings.py::test_confirm_rejects_incompatible_pending` ×2 — PASSED | **PASSED** у межах обсягу. Статуси A, C, D — так; операція повернення — ні (п. 5) | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-09 | AC-09.2 (Входить) | `test_bookings.py::test_confirm_rejects_incompatible_pending` ×2 — PASSED | **PASSED** | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-09 | AC-09.3 (Частково) | `test_bookings.py::test_reject_pending_returns_200` — PASSED | **PASSED** у межах обсягу. REJECTED — так; операція повернення — ні (п. 5) | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-09 | AC-09.4 (Входить) | `test_bookings.py::test_decision_by_non_owner_returns_403` ×4 — PASSED | **PASSED** | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-09 | AC-09.5 (Входить) | `test_bookings.py::test_decision_on_non_pending_returns_409` ×4 — PASSED<br>`test_booking_clock.py::test_pending_request_is_rejected_at_decision_deadline` — PASSED | **PASSED** | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-09 | AC-09.7 (Входить) | `test_bookings.py::test_confirm_single_pending_returns_200` — PASSED<br>`test_booking_clock.py::test_confirm_one_minute_before_deadline` — PASSED | **PASSED** | `confirmBooking`, `rejectBooking`: 200, 401, 403, 404, 409 перевірено |
| FR-12 | AC-12.1 (Входить) | `test_bookings.py::test_list_bookings_as_guest_returns_own_trips` — PASSED | **PASSED** | `listBookings`, `getBooking`: 200, 401, 403, 404, 422 перевірено |
| FR-12 | AC-12.2 (Входить) | `test_bookings.py::test_list_bookings_as_guest_returns_own_trips` — PASSED | **PASSED** | `listBookings`, `getBooking`: 200, 401, 403, 404, 422 перевірено |
| FR-12 | AC-12.3 (Входить) | `test_booking_clock.py::test_turnover_remains_after_completion` — PASSED | **PASSED** | `listBookings`, `getBooking`: 200, 401, 403, 404, 422 перевірено |
| FR-12 | AC-12.4 (Входить) | `test_bookings.py::test_list_bookings_as_owner_returns_own_listing_requests` — PASSED | **PASSED** | `listBookings`, `getBooking`: 200, 401, 403, 404, 422 перевірено |
| FR-12 | AC-12.5 (Входить) | `test_bookings.py::test_get_booking_returns_200` — PASSED<br>`test_bookings.py::test_get_foreign_booking_returns_404` — PASSED<br>`test_bookings.py::test_list_bookings_as_guest_returns_own_trips` — PASSED<br>`test_bookings.py::test_list_bookings_as_owner_returns_own_listing_requests` — PASSED | **PASSED** | `listBookings`, `getBooking`: 200, 401, 403, 404, 422 перевірено |
| FR-13 | AC-13.1 (Входить) | `test_refund_share.py::test_guest_cancels_confirmed_by_scale` ×5 — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-13 | AC-13.2 (Входить) | `test_refund_share.py::test_guest_cancels_pending_gets_full_refund` ×3 — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-13 | AC-13.3 (Входить) | `test_refund_share.py::test_host_cancels_gets_full_refund` ×3 — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-13 | AC-13.4 (Входить) | `test_booking_clock.py::test_cancel_at_and_after_check_in_moment_is_refused` — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-13 | AC-13.5 (Входить) | `test_bookings.py::test_cancel_finished_booking_returns_409` ×2 — PASSED<br>`test_booking_clock.py::test_cancel_completed_booking_is_refused` — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-13 | AC-13.6 (Входить) | `test_bookings.py::test_cancel_booking_returns_200` — PASSED | **PASSED** | `cancelBooking`: 200, 401, 404, 409 перевірено; 403 лише для заблокованого, не моделюється |
| FR-15 | AC-15.1 (Входить) | `test_bookings.py::test_create_booking_returns_201` — PASSED | **PASSED** | Поля сум схеми `Booking` |
| NFR-01 | AC-N01.1 (Частково) | `test_bookings.py::test_parallel_confirmations_leave_one_confirmed` ×3 — PASSED | **PASSED** у межах обсягу. Перевіряється паралельними запитами: рівно один CONFIRMED, решта REJECTED — так; повернення — ні (п. 5) | `confirmBooking`: 200 і 409 `STATE_CONFLICT` за описом операції |
| NFR-01 | AC-N01.3 (Входить) | `test_bookings.py::test_parallel_confirmations_leave_one_confirmed` ×3 — PASSED | **PASSED** | `confirmBooking`: 200 і 409 `STATE_CONFLICT` за описом операції |
| FR-ADD-02 | AC-ADD-02.1 (Входить) | `test_listings_pagination.py::test_limit_restricts_number_of_items` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.2 (Входить) | `test_listings_pagination.py::test_offset_skips_first_items` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.3 (Входить) | `test_listings_pagination.py::test_total_count_does_not_depend_on_limit_and_offset` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.4 (Входить) | `test_listings_pagination.py::test_out_of_range_values_are_rejected` ×3 — PASSED<br>`test_listings_pagination.py::test_boundary_values_are_accepted` ×3 — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.5 (Входить) | `test_listings_pagination.py::test_default_limit_without_pagination_params` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.6 (Входить) | `test_listings_pagination.py::test_pagination_applies_after_filters_and_sort` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |
| FR-ADD-02 | AC-ADD-02.7 (Входить) | `test_listings_pagination.py::test_order_is_stable_for_equal_prices` ×3 — PASSED<br>`test_listings_pagination.py::test_page_follows_creation_order` — PASSED | **PASSED** | `searchListings`: `limit`, `offset`, `X-Total-Count`, 422 за тегом `api-v1.1` |

Відповідь 500 `INTERNAL_ERROR` оголошена в кожній операції, окремими тестами не перевіряється.

## Що змінилося після першого прогону верифікації

Перший прогін цього дня виявив AC без тестів. Після рішення власника вимог закрито так.

**Додано 4 тестові функції, 9 кейсів (149 → 158).** Вони написані після коду, тому перевірені мутаціями на тимчасовій копії `src/`; `src/` репозиторію не змінювався.

| AC | Новий тест | Мутація | Результат мутації |
|----|------------|---------|-------------------|
| AC-06.6 | `test_commission_change_applies_only_to_new_requests` | нові запити рахуються за старим відсотком | упав: `(15, '246.91', '2716.03') == (15, '370.36', '2839.48')` |
| AC-06.6 | те саме | збережене бронювання показує поточний відсоток | упав: `(15, …) == (10, …)` |
| AC-05.3 | `test_search_excludes_listing_with_completed_booking` | COMPLETED не займає ночей | упав: оголошення знайдено замість `[]` |
| AC-06.4 | `test_refund_scale_uses_check_in_time_fixed_at_creation` | шкала рахується від поточного часу заїзду житла | упав: `50 == 0` |
| AC-07.1 | `test_refused_request_creates_no_booking` ×6 | бронювання зберігається до перевірок | упали всі 6 кейсів |

Тест AC-06.4 читає службове поле `_refundShare`, бо p в API не виходить (п. 6), а тест AC-06.6 підміняє `COMMISSION_RATE`. Обидва спираються на внутрішні точки реалізації.

**Звужено обсяг у `logs/lab5-scope.md`.** Ці частини не реалізовані; PASSED для цих AC означає лише перевірену частину.

| AC | Було | Стало | Що лишається неперевіреним |
|----|------|-------|----------------------------|
| AC-08.2, 08.3, 08.4, 08.5 | Входить (причина конфлікту — модульно) | Частково | Причина конфлікту: є лише в журналі подій, Events поза обсягом (п. 9), у коді не формується |
| AC-07.1 | Частково (`ACCOUNT_BLOCKED` — модульно) | Частково (без підстави 0) | `ACCOUNT_BLOCKED`: блокування не моделюється (п. 11) |

Зведення обсягу змінилося: «Входить» 51 → 47, «Частково» 8 → 12, «Не входить» 26.

## Підсумок pytest

```
python -m pytest -v
158 passed, 1 warning in 31.15s
```

| Файл | Кейсів | Результат |
|------|--------|-----------|
| `test_booking_clock.py` | 11 | 11 PASSED |
| `test_bookings.py` | 69 | 69 PASSED |
| `test_commission_config.py` | 1 | 1 PASSED |
| `test_listings.py` | 51 | 51 PASSED |
| `test_listings_pagination.py` | 15 | 15 PASSED |
| `test_refund_share.py` | 11 | 11 PASSED |

Із них 34 кейсів не прив'язані до AC обсягу: це коди контракту (401, 403, 404, 409, 422), порядок перевірок і FR-10. Усі функції наведено в додатку. Попередження `StarletteDeprecationWarning` (httpx → httpx2) стосується версії залежностей.

## Контрактна перевірка `scripts/contract_check.ps1`

Прогін 2026-11-10; після нього `src/` і `api/` не змінювалися. Schemathesis 4.32.7, сервер `scripts/serve_contract.py` на 127.0.0.1:8765. Перевірено 12 із 35 операцій (теги Listings і Bookings), фази Examples, Coverage, Fuzzing, Stateful. Перевірку `positive_data_acceptance` вимкнено свідомо (`logs/lab5-scope.md`, п. 12). Код виходу скрипта: 0.

| Токен | Операцій | Згенеровано | Пройшло | Пропущено | Невідповідностей | Результат |
|-------|----------|-------------|---------|-----------|------------------|-----------|
| `guest-token` | 12 | 1592 | 1592 | 10 | 0 | PASSED |
| `host-token` | 12 | 2553 | 2553 | 12 | 0 | PASSED |
| `moderator-token` | 12 | 2214 | 2214 | 4 | 0 | PASSED |

Попередження schemathesis обмежують глибину перевірки, але не є невідповідностями:

| Попередження | Операції | Пояснення |
|--------------|----------|-----------|
| Лише 401/403 | guest і host: `publishListing`, `unpublishListing`; moderator: `listBookings`, `createBooking`, `createListing`, `replaceListing` | Очікувано: ролі не мають доступу до цих дій |
| Постійно 404 | guest: `confirmBooking`, `rejectBooking`, `replaceListing`; host: `confirmBooking`, `replaceListing`; moderator: `getBooking`, `cancelBooking`, `confirmBooking`, `rejectBooking`, `replaceListing` | Випадкові ідентифікатори не існують, тож успішні гілки цих операцій schemathesis майже не досягає. Їх перевіряють API-тести |
| Переважно відхилені дані | guest і host: `createListing`, `replaceListing`; moderator: `replaceListing` | Згенеровані тіла зазвичай не проходять перевірки фотографій і меж |

## Свідомі обмеження

Перші чотири — із `logs/lab5-scope.md`. Останні три в цьому файлі не описані, їх джерело — код.

| Обмеження | Джерело | Суть |
|-----------|---------|------|
| Закриті ночі (closed-nights) | `lab5-scope.md`, пп. 1, 2, 4 | Операції Availability не реалізуються; у FR-08 і пошуку вважається, що закритих ночей немає. AC-08.6 не входить |
| Payments | пп. 1, 5, 7 | Платіжні операції не створюються, у відповідях лише поля схеми `Booking`; p не виходить в API (п. 6) |
| Events | п. 9 | Журнал подій не реалізується; записи WARN і причини конфліктів не спостерігаються |
| Auth-заглушка | п. 11 | Users/Auth не реалізуються: bearer-перевірка за in-memory сховищем `src.auth.TOKENS`. Блокування не моделюється, 403 `ACCOUNT_BLOCKED` не повертається |
| RLock в одному процесі | `src/services/bookings.py` (`LOCK`) | `threading.RLock` серіалізує дії над бронюваннями лише всередині одного процесу. NFR-01 і in-memory сховище не працюватимуть за кількох процесів сервера |
| Ліниве застосування FR-10/FR-11 | `src/services/bookings.py` (`refresh`, `_fresh_state`); годинник — п. 10 обсягу | Автоматичне відхилення й завершення виконуються перед кожною дією над бронюваннями, фонового процесу немає |
| Порядок 401→403→422 | `src/auth.py` | Перевірка входу й ролі виконується до валідації запиту. Виняток: 403 за належністю (`replaceListing`, чуже оголошення) визначається в сервісі, тому невалідне тіло від не-власника дає 422. Порядок перевірено разовими запитами до застосунку; окремих тестів у `tests/` немає |

## Дефект, виявлений валідацією

Знайдено під час ручної валідації в Swagger UI, після прогонів, описаних вище. Автотести й schemathesis його не виявляли: вони надсилають заголовок `Authorization` напряму, а не через форму `/docs`.

| Параметр | Значення |
|----------|----------|
| Симптом | З `/docs` усі захищені операції повертають 401 `UNAUTHENTICATED` навіть із дійсним токеном |
| Причина 1 | `src/auth.py` оголошував токен як параметр-заголовок `authorization` (`Header()`). За специфікацією OpenAPI параметр-заголовок із назвою `Authorization` ігнорується, і Swagger UI його не надсилає |
| Причина 2 | Контракт `api/openapi.yaml` оголошує `securitySchemes.bearerAuth`, а схема, згенерована реалізацією, — ні, тому кнопки Authorize в `/docs` не було |
| Виправлення | `optional_user` отримує токен через `fastapi.security.HTTPBearer(auto_error=False, scheme_name="bearerAuth")`. Змінено лише `src/auth.py`; `tests/`, `api/`, `spec/` не змінювалися |

Поведінка збережена:

| Запит | Результат |
|-------|-----------|
| Без заголовка, невідомий токен, схема не Bearer, `Bearer` без токена, токен без схеми | `optional_user` → `None`; у `require_user` — 401 `UNAUTHENTICATED`, зокрема за невалідного тіла |
| `bearer` у нижньому регістрі, зайві пробіли навколо токена | Токен розпізнається, як і раніше |
| Роль без доступу, зокрема за невалідного тіла | 403 `FORBIDDEN` до валідації тіла |
| Необов'язкова автентифікація (`getListing`) із невідомим токеном | Запит обробляється як анонімний, без 401 |

Перевірка після виправлення:

- `python -m pytest -v`: 158 passed, 1 warning.
- Разові запити до застосунку підтвердили таблицю вище. У згенерованій схемі є `securitySchemes.bearerAuth` (`type: http`, `scheme: bearer`), параметра-заголовка `authorization` немає в жодній операції, 11 операцій мають `security: [{bearerAuth: []}]`, `searchListings` — без `security`.

Обмеження цієї перевірки:

- Контрактну перевірку `scripts/contract_check.ps1` після виправлення не повторювали. Твердження вище про незмінність `src/` після її прогону стосується стану до цього виправлення.
- Повторний прогін через форму Authorize у браузері не виконувався.
- Лишається розбіжність документації для `getListing`: контракт оголошує необов'язкову автентифікацію (`security: [{}, {bearerAuth: []}]`), а згенерована схема — `[{bearerAuth: []}]`. Фактична поведінка відповідає контракту: запит без токена не отримує 401.

## Висновок

Реалізація відповідає обсягу Лаб 5 і FR-ADD-02. Усі 59 AC обсягу мають тести зі статусом PASSED, 158 із 158 тестів пройшли, контрактна перевірка для трьох ролей не знайшла невідповідностей.

Цей результат стосується обсягу, зафіксованого в `logs/lab5-scope.md` після звуження: для 12 AC зі статусом «Частково» перевірено лише частину, зазначену в таблиці.

## Додаток: усі тестові функції

| Файл | Функція | Кейсів | Результат | Прив'язка до AC обсягу |
|------|---------|--------|-----------|------------------------|
| `test_booking_clock.py` | `test_cancel_at_and_after_check_in_moment_is_refused` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_cancel_completed_booking_is_refused` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_checkin_too_soon_boundary` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_checkin_too_soon_precedes_dates_unavailable` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_booking_clock.py` | `test_confirm_one_minute_before_deadline` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_decision_deadline_is_24_hours_after_creation` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_booking_clock.py` | `test_decision_deadline_is_check_in_when_earlier` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_booking_clock.py` | `test_pending_request_is_rejected_at_decision_deadline` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_refund_scale_uses_check_in_time_fixed_at_creation` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_search_excludes_listing_with_completed_booking` | 1 | PASSED | так |
| `test_booking_clock.py` | `test_turnover_remains_after_completion` | 1 | PASSED | так |
| `test_bookings.py` | `test_booking_keeps_terms_after_listing_change` | 1 | PASSED | так |
| `test_bookings.py` | `test_cancel_booking_returns_200` | 1 | PASSED | так |
| `test_bookings.py` | `test_cancel_finished_booking_returns_409` | 2 | PASSED | так |
| `test_bookings.py` | `test_cancel_foreign_booking_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_cancel_unknown_booking_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_cancel_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_check_in_on_previous_checkout_is_created` | 1 | PASSED | так |
| `test_bookings.py` | `test_confirm_rejects_incompatible_pending` | 2 | PASSED | так |
| `test_bookings.py` | `test_confirm_single_pending_returns_200` | 1 | PASSED | так |
| `test_bookings.py` | `test_confirmed_booking_keeps_terms_from_creation` | 1 | PASSED | так |
| `test_bookings.py` | `test_conflict_with_two_bookings_lists_both_ids` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_create_booking_above_max_guests_returns_422` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_by_moderator_returns_403` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_create_booking_checkout_not_after_checkin_returns_422` | 2 | PASSED | так |
| `test_bookings.py` | `test_create_booking_overlapping_confirmed_returns_409` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_own_listing_returns_403` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_returns_201` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_unknown_listing_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_create_booking_with_max_guests_returns_201` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_with_past_check_in_returns_422` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_with_zero_guests_returns_422` | 1 | PASSED | так |
| `test_bookings.py` | `test_create_booking_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_decision_by_non_owner_returns_403` | 4 | PASSED | так |
| `test_bookings.py` | `test_decision_on_non_pending_returns_409` | 4 | PASSED | так |
| `test_bookings.py` | `test_decision_on_unknown_booking_returns_404` | 2 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_decision_without_token_returns_401` | 2 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_fr07_checks_order` | 5 | PASSED | так |
| `test_bookings.py` | `test_get_booking_returns_200` | 1 | PASSED | так |
| `test_bookings.py` | `test_get_booking_visible_to_listing_host` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_get_booking_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_get_foreign_booking_returns_404` | 1 | PASSED | так |
| `test_bookings.py` | `test_get_unknown_booking_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_host_cancels_confirmed_booking` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_list_bookings_as_guest_returns_own_trips` | 1 | PASSED | так |
| `test_bookings.py` | `test_list_bookings_as_owner_returns_own_listing_requests` | 1 | PASSED | так |
| `test_bookings.py` | `test_list_bookings_by_moderator_returns_403` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_list_bookings_without_role_returns_422` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_list_bookings_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_bookings.py` | `test_new_request_after_turnover_change_on_previous_checkout` | 1 | PASSED | так |
| `test_bookings.py` | `test_new_request_turnover_covering_check_in_returns_409` | 1 | PASSED | так |
| `test_bookings.py` | `test_night_after_turnover_is_available` | 1 | PASSED | так |
| `test_bookings.py` | `test_night_in_booking_turnover_returns_409` | 1 | PASSED | так |
| `test_bookings.py` | `test_parallel_confirmations_leave_one_confirmed` | 3 | PASSED | так |
| `test_bookings.py` | `test_pending_request_does_not_block_same_nights` | 1 | PASSED | так |
| `test_bookings.py` | `test_refused_request_creates_no_booking` | 6 | PASSED | так |
| `test_bookings.py` | `test_reject_pending_returns_200` | 1 | PASSED | так |
| `test_bookings.py` | `test_two_guests_pending_on_same_nights` | 1 | PASSED | так |
| `test_commission_config.py` | `test_commission_change_applies_only_to_new_requests` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_by_moderator_returns_403` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_create_listing_photo_invalid_creates_nothing` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_returns_201` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_boundary_values_returns_201` | 4 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_invalid_max_guests_returns_422` | 2 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_invalid_photos_returns_422` | 3 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_invalid_price_returns_422` | 2 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_invalid_times_returns_422` | 3 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_jpeg_and_png_returns_201` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_photo_of_max_size_returns_201` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_ten_max_size_photos_returns_201` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_with_unsupported_photo_format_returns_422` | 1 | PASSED | так |
| `test_listings.py` | `test_create_listing_without_required_field_returns_422` | 2 | PASSED | так |
| `test_listings.py` | `test_create_listing_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_get_listing_returns_200` | 1 | PASSED | так |
| `test_listings.py` | `test_get_listing_unknown_id_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_get_unpublished_listing_visible_to_host_and_moderator_only` | 1 | PASSED | так |
| `test_listings.py` | `test_publish_listing_by_host_returns_403` | 1 | PASSED | так |
| `test_listings.py` | `test_publish_listing_by_moderator_returns_200` | 1 | PASSED | так |
| `test_listings.py` | `test_publish_listing_without_reason_returns_422` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_publish_listing_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_publish_published_listing_returns_409` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_replace_listing_by_other_host_returns_403` | 1 | PASSED | так |
| `test_listings.py` | `test_replace_listing_photo_invalid_keeps_card` | 1 | PASSED | так |
| `test_listings.py` | `test_replace_listing_returns_200` | 1 | PASSED | так |
| `test_listings.py` | `test_replace_listing_unknown_id_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_replace_listing_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_search_by_guests_count` | 1 | PASSED | так |
| `test_listings.py` | `test_search_city_is_exact_match` | 1 | PASSED | так |
| `test_listings.py` | `test_search_excludes_listing_in_turnover` | 1 | PASSED | так |
| `test_listings.py` | `test_search_excludes_listing_with_confirmed_overlap` | 1 | PASSED | так |
| `test_listings.py` | `test_search_listings_returns_200` | 1 | PASSED | так |
| `test_listings.py` | `test_unpublish_listing_by_host_returns_403` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_unpublish_listing_returns_200` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_unpublish_listing_without_reason_returns_422` | 2 | PASSED | так |
| `test_listings.py` | `test_unpublish_listing_without_token_returns_401` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_unpublish_rejects_pending_and_keeps_confirmed` | 1 | PASSED | так |
| `test_listings.py` | `test_unpublish_unknown_listing_returns_404` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_unpublish_unpublished_listing_returns_409` | 1 | PASSED | ні (коди контракту, порядок, FR-10) |
| `test_listings.py` | `test_unpublished_listing_hidden_from_search_and_booking` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_boundary_values_are_accepted` | 3 | PASSED | так |
| `test_listings_pagination.py` | `test_default_limit_without_pagination_params` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_limit_restricts_number_of_items` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_offset_skips_first_items` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_order_is_stable_for_equal_prices` | 3 | PASSED | так |
| `test_listings_pagination.py` | `test_out_of_range_values_are_rejected` | 3 | PASSED | так |
| `test_listings_pagination.py` | `test_page_follows_creation_order` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_pagination_applies_after_filters_and_sort` | 1 | PASSED | так |
| `test_listings_pagination.py` | `test_total_count_does_not_depend_on_limit_and_offset` | 1 | PASSED | так |
| `test_refund_share.py` | `test_guest_cancels_confirmed_by_scale` | 5 | PASSED | так |
| `test_refund_share.py` | `test_guest_cancels_pending_gets_full_refund` | 3 | PASSED | так |
| `test_refund_share.py` | `test_host_cancels_gets_full_refund` | 3 | PASSED | так |
