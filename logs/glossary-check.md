# Звірка імен у `src/` із глосарієм і контрактом

| Параметр | Значення |
|----------|----------|
| Дата | 2026-11-10 |
| Джерела | `spec/glossary.md`, `api/openapi.yaml` |
| Обсяг | Класи, функції, поля, коди помилок і маршрути в `src/`; сутності Лаб 5 — Listing і Booking ([`logs/lab5-scope.md`](lab5-scope.md)) |
| Правило змін | Перейменовано лише внутрішні імена, які не входять у контракт і не використовуються тестами |
| Результат | Маршрути, поля й коди помилок відповідають контракту. 9 внутрішніх імен виправлено, решту наведено нижче |

Згенерована FastAPI схема OpenAPI до і після перейменувань побайтно однакова. `pytest -q`: 158 passed.

Значення останнього стовпця:

- **Відповідає** — ім'я збігається з глосарієм або контрактом. Імена Python записано в `snake_case` згідно з `docs/coding-convention.md`.
- **Виправлено** — внутрішнє ім'я перейменовано.
- **Розбіжність** — ім'я або форма відрізняється від глосарія, але не змінювалися; причину вказано.
- **Не реалізовано** — терміна немає в коді, бо він поза обсягом Лаб 5.

Терміни, для яких у глосарії ідентифікатора немає («—»), не наведено.

## 1. Час і доступність

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Часовий пояс (`Europe/Kyiv`, `UTC`) | `KYIV = ZoneInfo("Europe/Kyiv")` | Відповідає. UTC стосується лише журналу подій, якого немає в обсязі |
| Ніч (`Night`, `nights`) | `nights`, `night`; `Night` — схема контракту | Відповідає |
| Дата заїзду (`checkIn`) | API: `checkIn`; Python: `check_in` | Відповідає |
| Дата виїзду (`checkOut`) | API: `checkOut`; Python: `check_out` | Відповідає |
| Час заїзду (`checkInTime`) | `checkInTime` | Відповідає |
| Час виїзду (`checkOutTime`) | `checkOutTime` | Відповідає |
| Момент заїзду (`checkInAt`) | API: `checkInAt`; Python: `check_in_at`; службове поле `_checkInAt` | Відповідає |
| Момент виїзду (`checkOutAt`) | API: `checkOutAt`; Python: `check_out_at`; службове поле `_checkOutAt` | Відповідає |
| Технологічна перерва (`turnoverNights`) | API: `turnoverNights`; Python: `turnover_nights` | Виправлено: `turnover` → `turnover_nights` в `overlaps()` і `conflicts()`. Параметр містить кількість ночей N, а `Turnover` у глосарії — це період |
| Turnover (`Turnover`) | Окремого імені немає, період обчислює `overlaps()` | Розбіжність: потрібна нова сутність, а не перейменування |
| Календар доступності (`Availability`) | — | Не реалізовано |
| Ніч, закрита власником (`ClosedNight`) | `ClosedNight` — лише схема контракту | Не реалізовано (`lab5-scope.md`, пп. 1–2) |
| Доступність діапазону (`isAvailable()`) | `is_available()` | Відповідає |

## 2. Житло

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Житло (`Listing`) | Схеми контракту `Listing`, `ListingRequest`; записи-словники `listing`, `record` | Відповідає. Окремого класу сутності немає, сховище працює зі словниками |
| Назва (`title`) | `title` | Відповідає |
| Опис (`description`) | `description` | Відповідає |
| Місто (`city`) | `city` | Відповідає |
| Адреса (`address`) | `address` | Відповідає |
| Фотографія (`photos`) | `photos`; `NewPhoto`, `ExistingPhoto` | Відповідає |
| Максимальна кількість осіб (`maxGuests`) | `maxGuests` | Відповідає |
| Ціна за ніч (`pricePerNight`) | API: `pricePerNight`; Python: `price_per_night` | Відповідає |
| Опубліковане (`ListingStatus.PUBLISHED`) | Рядок `"PUBLISHED"` у полі `status` | Розбіжність: значення збігається з контрактом, але класу `ListingStatus` немає. Запровадження enum — зміна коду, а не перейменування |
| Зняте з публікації (`ListingStatus.UNPUBLISHED`) | Рядок `"UNPUBLISHED"` у полі `status` | Розбіжність: те саме, що для `PUBLISHED` |
| Пошук житла (`ListingSearch`) | `search_listings()`, `services.listings.search()` | Розбіжність: окремої сутності немає, операцію названо за `operationId` контракту |

## 3. Бронювання

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Бронювання (`Booking`) | Схеми контракту `Booking`, `BookingRequest`; записи-словники `booking` | Відповідає. Окремого класу сутності немає |
| Статуси (`BookingStatus.PENDING`, `CONFIRMED`, `REJECTED`, `CANCELLED`, `COMPLETED`) | Рядки в полі `status` | Розбіжність: значення збігаються з контрактом, але класу `BookingStatus` немає |
| Кількість осіб (`guestsCount`) | API: `guestsCount`; Python: `guests_count` | Відповідає |
| Ініціатор скасування (`cancelledBy`) | API: `cancelledBy`; Python: `cancelled_by` | Виправлено: `initiator` → `cancelled_by` у `refund_share()` і `cancel()` |
| Строк рішення власника (`decisionDeadline`) | API: `decisionDeadline`; Python: `decision_deadline`; службове поле `_decisionDeadline` | Відповідає |
| Код відмови (`RefusalCode`) | Словник `PROBLEMS` в `src/errors.py` | Розбіжність: окремого типу немає, `PROBLEMS` містить усі коди схеми Problem |
| `CHECKIN_TOO_SOON` | `CHECKIN_TOO_SOON` | Відповідає |
| `PHOTO_INVALID` | `PHOTO_INVALID` | Відповідає |
| `ACCOUNT_BLOCKED` | — | Не реалізовано: блокування не моделюється (`lab5-scope.md`, п. 11). Код є в контракті |

## 4. Гроші

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Вартість проживання (`accommodationCost`) | API: `accommodationCost`; Python: `accommodation_cost` | Виправлено: `accommodation` → `accommodation_cost` у `costs()`, `refund()` і `create()` |
| Комісія (`commission`) | `commission` | Відповідає |
| Відсоток комісії (`commissionRate`) | API: `commissionRate`; константа `COMMISSION_RATE`; параметр `commission_rate` | Виправлено: параметр `rate` → `commission_rate` у `costs()` |
| Передоплата (`prepayment`) | `prepayment` | Відповідає |
| Повернення, сума (`refund`) | `refund()` | Виправлено: `refund_amount` → `refund`. Функцію не викликають ні в `src/`, ні в тестах |
| Повернення, частка (`refundRate`) | `refund_share()`, службове поле `_refundShare`, параметр `refund_rate` | Частково виправлено: параметр `share` → `refund_rate`. Розбіжність лишається: `refund_share` імпортують тести, а `_refundShare` читає `tests/unit/test_booking_clock.py` |
| Шкала повернення (`refundScale`) | Гілки всередині `refund_share()` | Розбіжність: окремого імені немає |
| Правило округлення (`roundDown()`, `roundUp()`) | `quantize(..., ROUND_FLOOR)` і `quantize(..., ROUND_CEILING)` | Розбіжність: окремих функцій немає, їх виділення — зміна коду |
| Утримана частка (`retainedAmount`) | — | Не реалізовано (`lab5-scope.md`, п. 5) |
| Виплата власнику (`Payout`) | — | Не реалізовано (`lab5-scope.md`, п. 5) |
| Платіжна операція (`Payment`) | `Payment` — лише схема контракту | Не реалізовано (`lab5-scope.md`, п. 5) |

## 5. Користувачі та ролі

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Користувач (`User`) | Псевдонім залежності `User`, словник з `userId` і `role` | Відповідає. Операції Users/Auth не реалізовано (`lab5-scope.md`, п. 11) |
| Пароль (`passwordHash`) | — | Не реалізовано |
| Тимчасове обмеження входу (`loginLockedUntil`) | — | Не реалізовано |
| Гість (`Role.GUEST`) | Рядок `"GUEST"`; поле `_guestId` | Розбіжність: значення збігається з контрактом, але класу `Role` немає |
| Власник (`Role.HOST`) | Рядок `"HOST"`; поля `hostId`, `_hostId`; параметр `host`; функція `_pending_of_host()` | Виправлено: ключ запису `ownerId` → `hostId`, параметр `owner` → `host`, `_owned_pending()` → `_pending_of_host()`. Класу `Role` немає. Значення `role=owner` у `GET /bookings` задає контракт, його не змінено |
| Модератор (`Role.MODERATOR`) | Рядок `"MODERATOR"`; псевдоніми `Moderator`, `NonModerator` | Розбіжність: значення збігається з контрактом, але класу `Role` немає |
| Заблокований (`UserStatus.BLOCKED`) | — | Не реалізовано (`lab5-scope.md`, п. 11) |
| Параметри платформи (`PlatformConfig`) | Константи `COMMISSION_RATE`, `MIN_TIME_BEFORE_CHECKIN`, `DECISION_PERIOD`, `REVIEW_PERIOD` | Розбіжність: класу немає, а `COMMISSION_RATE` підміняють тести |

## 6. Інші сутності

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Відгук (`Review`) | — | Не реалізовано |
| Прихований відгук (`ReviewVisibility.HIDDEN`, `hiddenReason`) | — | Не реалізовано |
| Середня оцінка (`averageRating`) | `averageRating` | Відповідає |
| Скарга на відгук (`ReviewComplaint`) | — | Не реалізовано. У контракті схема називається `Complaint` |
| Спір (`Dispute`) | — | Не реалізовано |
| Оскарження (`Appeal`) | — | Не реалізовано |
| Лічильник скасувань власником (`hostCancellationCount`) | — | Не реалізовано |
| Подія (`EventLogEntry`) | — | Не реалізовано |
| Журнал подій (`EventLog`) | — | Не реалізовано |
| Наскрізний ідентифікатор операції (`correlationId`) | `correlationId` у тілі Problem | Відповідає |
| `DATES_UNAVAILABLE` | `DATES_UNAVAILABLE` | Відповідає |
| Повідомлення (`Notification`) | — | Не реалізовано |

## 7. Маршрути

Усі 12 операцій обсягу збігаються з контрактом за методом, шляхом, параметрами й `operationId`. Ім'я функції — це `operationId` у `snake_case`. Інші 23 операції контракту поза обсягом.

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Пошук житла — `GET /listings` (`searchListings`) | `search_listings()` | Відповідає |
| Житло — `POST /listings` (`createListing`) | `create_listing()` | Відповідає |
| Житло — `GET /listings/{listingId}` (`getListing`) | `get_listing()` | Відповідає |
| Житло — `PUT /listings/{listingId}` (`replaceListing`) | `replace_listing()` | Відповідає |
| Зняте з публікації — `POST /listings/{listingId}/unpublish` (`unpublishListing`) | `unpublish_listing()` | Відповідає |
| Опубліковане — `POST /listings/{listingId}/publish` (`publishListing`) | `publish_listing()` | Відповідає |
| Запит — `POST /bookings` (`createBooking`) | `create_booking()` | Відповідає |
| Бронювання — `GET /bookings` (`listBookings`) | `list_bookings()` | Відповідає |
| Бронювання — `GET /bookings/{bookingId}` (`getBooking`) | `get_booking()` | Відповідає |
| Підтверджене бронювання — `POST /bookings/{bookingId}/confirm` (`confirmBooking`) | `confirm_booking()` | Відповідає |
| Відхилене бронювання — `POST /bookings/{bookingId}/reject` (`rejectBooking`) | `reject_booking()` | Відповідає |
| Скасоване бронювання — `POST /bookings/{bookingId}/cancel` (`cancelBooking`) | `cancel_booking()` | Відповідає |

## 8. Схеми й коди помилок

Набори полів у схемах запитів і у відповідях Listing та Booking збігаються з контрактом.

| Термін глосарію | Ідентифікатор у коді | Відповідає / розбіжність |
|-----------------|----------------------|--------------------------|
| Схема контракту `ListingRequest` | `ListingRequest` | Відповідає |
| Схема контракту `BookingRequest` | `BookingRequest` | Відповідає |
| Схема контракту `ModerationReasonRequest` | `ModerationReasonRequest` | Відповідає |
| Схеми контракту `NewPhoto`, `ExistingPhoto` | `NewPhoto`, `ExistingPhoto` | Відповідає |
| Схема контракту `Problem` | `ProblemError`, `problem_response()` | Відповідає, поля тіла збігаються зі схемою |
| Код відмови `MIN_NIGHTS`, 422 | `MIN_NIGHTS`, 422 | Відповідає |
| Код відмови `OWN_LISTING`, 403 | `OWN_LISTING`, 403 | Відповідає |
| Код відмови `GUESTS_OUT_OF_RANGE`, 422 | `GUESTS_OUT_OF_RANGE`, 422 | Відповідає |
| Код відмови `LISTING_UNPUBLISHED`, 409 | `LISTING_UNPUBLISHED`, 409 | Відповідає |
| Код відмови `CHECKIN_TOO_SOON`, 422 | `CHECKIN_TOO_SOON`, 422 | Відповідає |
| Код відмови `DATES_UNAVAILABLE`, 409 | `DATES_UNAVAILABLE`, 409 | Відповідає |
| Код `PHOTO_INVALID`, 422 | `PHOTO_INVALID`, 422 | Відповідає |
| Код контракту `UNAUTHENTICATED`, 401 | `UNAUTHENTICATED`, 401 | Відповідає |
| Код контракту `FORBIDDEN`, 403 | `FORBIDDEN`, 403 | Відповідає |
| Код контракту `NOT_FOUND`, 404 | `NOT_FOUND`, 404 | Відповідає |
| Код контракту `STATE_CONFLICT`, 409 | `STATE_CONFLICT`, 409 | Відповідає |
| Код контракту `VALIDATION_FAILED`, 422 | `VALIDATION_FAILED`, 422 | Відповідає |
| Код контракту `INTERNAL_ERROR`, 500 | `INTERNAL_ERROR`, 500 | Відповідає |
| Коди контракту `EMAIL_TAKEN`, `INVALID_CREDENTIALS`, `LOGIN_RESTRICTED` | — | Не реалізовано: операції Users/Auth поза обсягом |

## 9. Псевдонім `src/bookings.py`

Файл видалено. `tests/unit/conftest.py`, `tests/unit/test_commission_config.py` і `tests/unit/test_refund_share.py` тепер імпортують `src.services.bookings`. Записи про `src.bookings` у `logs/test-gate-base.md` описують стан коду на момент того gate, тому їх не змінено.

## 10. Зауваження

Docstring `_fresh_state()` в `src/services/bookings.py` вживає слово «блокування» у значенні потокового `LOCK`. У глосарії (розділ 3, п. 13) це слово закріплене за станом «Заблокований». Імені це не стосується, тому текст не змінено.
