Архітектура
===========

Застосунок реалізує 12 операцій контракту з тегами ``Listings`` і ``Bookings``. Запит проходить
три шари: маршрути, сервіси, сховище.

Шари
----

.. csv-table::
   :header: "Шар", "Модулі", "Відповідальність"
   :widths: 15, 30, 55

   "Маршрути", "``src.routers.listings``, ``src.routers.bookings``", "Шляхи й методи HTTP, перевірка ролі через залежності, розбір тіла за схемами. Викликають сервіс і повертають його представлення для API. Правил предметної області не містять."
   "Сервіси", "``src.services.listings``, ``src.services.bookings``", "Правила вимог FR: перевірки, переходи статусів, суми. Відмови подають винятком ``ProblemError``."
   "Сховище", "``src.repository``", "Два словники в пам'яті, для житла й бронювань. Стан зникає після зупинки процесу."

Сховище повертає самі записи, а не копії, тому сервіси змінюють їх на місці. Службові поля записів
в API не виходять: функції ``to_api`` відкидають поля бронювання з префіксом ``_`` та поля житла
``hostId`` і ``unpublishedBy``.

Дії над бронюваннями виконуються послідовно під спільним ``LOCK`` (NFR-01). Перед кожною такою дією
сервіс застосовує переходи статусів, що настали з часом (FR-10, FR-11). Окремого фонового процесу
для цього немає.

Схема залежностей
-----------------

.. code-block:: text

   HTTP-запит
       |
       v
   src.main  --------------------------------------> src.errors
       |                                                 ^
       v                                                 |
   src.routers.listings      src.routers.bookings        |
       |                          |                      |
       |   src.auth, src.schemas  |                      |
       v                          v                      |
   src.services.listings --> src.services.bookings ------+
       |                          |
       +------------+-------------+
                    v
             src.repository

Імпорти між модулями проєкту:

.. csv-table::
   :header: "Модуль", "Імпортує"
   :widths: 35, 65

   "``src.main``", "``src.errors``, ``src.routers.listings``, ``src.routers.bookings``"
   "``src.routers.listings``", "``src.auth``, ``src.schemas``, ``src.services.listings``"
   "``src.routers.bookings``", "``src.auth``, ``src.schemas``, ``src.services.bookings``"
   "``src.services.listings``", "``src.repository``, ``src.errors``, ``src.schemas``, ``src.services.bookings``"
   "``src.services.bookings``", "``src.repository``, ``src.errors``"
   "``src.auth``", "``src.errors``"
   "``src.repository``", "—"
   "``src.errors``", "—"
   "``src.schemas``", "—"

``src.services.listings`` звертається до ``src.services.bookings`` у двох випадках: для перевірки
доступності в пошуку та для відхилення запитів, коли житло знімають із публікації.

Автентифікація
--------------

Операції Users/Auth не реалізовано. Токени зберігаються в словнику ``src.auth.TOKENS`` у форматі
``{token: {"userId": ..., "role": ...}}``, його заповнюють фікстури тестів або
``scripts/serve_contract.py``. Клієнт передає токен у заголовку ``Authorization: Bearer``.

Перевірки побудовано як ланцюжок залежностей FastAPI. Залежності виконуються до розбору тіла, тому
відповіді 401 і 403 мають пріоритет над 422.

.. csv-table::
   :header: "Псевдонім", "Залежність", "Відмова", "Операції"
   :widths: 15, 25, 25, 35

   "—", "немає", "—", "``searchListings``"
   "``OptionalUser``", "``optional_user``", "немає; невідомий токен означає незареєстрованого відвідувача", "``getListing``"
   "``User``", "``require_user``", "``UNAUTHENTICATED``", "``replaceListing``, ``getBooking``, ``confirmBooking``, ``rejectBooking``, ``cancelBooking``"
   "``NonModerator``", "``require_non_moderator``", "``UNAUTHENTICATED``, ``FORBIDDEN`` для модератора", "``createListing``, ``createBooking``, ``listBookings``"
   "``Moderator``", "``require_moderator``", "``UNAUTHENTICATED``, ``FORBIDDEN`` для інших ролей", "``publishListing``, ``unpublishListing``"

Обробка помилок Problem
-----------------------

Сервіси й залежності піднімають ``ProblemError`` з кодом зі словника ``src.errors.PROBLEMS``. Функція
``problem_response`` формує відповідь ``application/problem+json`` (RFC 9457) з полями ``type``,
``title``, ``status``, ``code``, ``correlationId``, а також ``detail`` і додатковими полями, якщо
вони задані. Наприклад, ``DATES_UNAVAILABLE`` додає ``conflictingBookingIds``.

.. csv-table::
   :header: "Код", "HTTP-статус"
   :widths: 70, 30

   "``UNAUTHENTICATED``", "401"
   "``FORBIDDEN``, ``OWN_LISTING``", "403"
   "``NOT_FOUND``", "404"
   "``STATE_CONFLICT``, ``LISTING_UNPUBLISHED``, ``DATES_UNAVAILABLE``", "409"
   "``VALIDATION_FAILED``, ``PHOTO_INVALID``, ``MIN_NIGHTS``, ``GUESTS_OUT_OF_RANGE``, ``CHECKIN_TOO_SOON``", "422"
   "``INTERNAL_ERROR``", "500"

Обробники реєструє ``register_error_handlers``:

.. csv-table::
   :header: "Виняток", "Обробник", "Відповідь"
   :widths: 30, 20, 50

   "``ProblemError``", "``handle_problem``", "Problem із кодом відмови"
   "``RequestValidationError``", "``handle_validation``", "Problem ``VALIDATION_FAILED`` за першим порушенням"
   "``HTTPException`` Starlette", "``handle_http``", "404 — Problem ``NOT_FOUND``; 400 — Problem ``VALIDATION_FAILED``; 405 — JSON із заголовком ``Allow``; інші статуси передаються без змін"
   "``Exception``", "``handle_internal``", "Problem ``INTERNAL_ERROR`` без деталей збою"

Відсутній ресурс і ресурс, недоступний цьому користувачу, дають однакову відповідь ``NOT_FOUND``.

Контракт і згенерована схема
----------------------------

FastAPI будує ``/openapi.json`` і Swagger UI (``/docs``) з коду. Шляхи, методи, параметри запиту,
поля тіл і схема безпеки ``bearerAuth`` збігаються з ``api/openapi.yaml``. Фактичні коди відповідей
12 операцій теж збігаються з контрактом. Винятком є 403 ``ACCOUNT_BLOCKED`` у ``cancelBooking``,
бо блокування поза обсягом. Згенерована схема відрізняється від контракту в такому:

- у відповідях кожної операції є лише код успіху й 422. Кодів 401, 403, 404, 409 і 500 немає,
  а 422 вказано й для ``getListing``, ``getBooking``, ``confirmBooking``, ``rejectBooking`` і
  ``cancelBooking``, які його не повертають;
- ``listingId`` і ``bookingId`` мають тип ``string`` без формату ``uuid``. Ідентифікатор не у
  форматі UUID дає 404 ``NOT_FOUND``;
- ``getListing`` позначено як операцію з ``bearerAuth``, хоча вхід для неї необов'язковий;
- немає тегів, описів і україномовних назв операцій.

Тому опис API для клієнтів — це ``docs/api.html``, зібраний із контракту.

Обмеження
---------

Обмеження обсягу визначено в ``logs/lab5-scope.md``. Номери в дужках — пункти цього файлу.

Пагінацію пошуку (``limit``, ``offset``, заголовок ``X-Total-Count``) реалізовано за адендумом
``spec/addenda/ADD-02.md``, вона належить до контракту 1.1.0.

- **Операції.** Інші 23 операції контракту не реалізовано, зокрема теги ``Availability``,
  ``Reviews``, ``Payments`` і ``Disputes`` (п. 1).
- **Закриті ночі.** Вважається, що їх немає: у ``createBooking`` і ``searchListings`` перевіряється
  лише перетин із бронюваннями в статусі CONFIRMED або COMPLETED з урахуванням технологічної
  перерви (пп. 2–4).
- **Платіжні операції.** Не створюються. ``createBooking`` лише фіксує суми в полях ``Booking``,
  а ``cancelBooking`` виконує перехід у CANCELLED (п. 5).
- **Частка повернення.** Її розраховує сервісний шар і перевіряють модульні тести. В API вона не
  виходить, бо схема ``Booking`` такого поля не має (пп. 5–7).
- **Лічильник скасувань власником і повідомлення.** Поза обсягом (п. 8).
- **Журнал подій.** Не реалізовано (п. 9).
- **Переходи в часі.** FR-10 і FR-11 не мають окремих операцій. Їх перевіряють модульні тести, які
  підміняють годинник ``src.services.bookings.now`` (п. 10).
- **Автентифікація.** Лише перевірка bearer-токена через сховище в пам'яті. ``registerUser``
  і ``createSession`` не реалізовано, блокування користувачів не моделюється (п. 11).
- **Контрактна перевірка.** schemathesis запускається без ``positive_data_acceptance``, бо контракт
  свідомо відхиляє чотири запити, що відповідають схемі (п. 12).
