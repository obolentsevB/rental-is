# API-GATE (повторний): контракт REST API «rental-is» 1.1.0

| Параметр | Значення |
|----------|----------|
| Дата | 2026-11-08 |
| Специфікація | `api/openapi.yaml` (OpenAPI 3.1, 35 операцій), версія 1.1.0, коміт `4d06561`, робоча копія файлу збігається з комітом |
| Підстава | [`spec/addenda/ADD-02.md`](../spec/addenda/ADD-02.md) (FR-ADD-02, ризик 7), [`logs/addendum-gate.md`](addendum-gate.md) (SPEC-ADDENDUM-GATE: GO) |
| Еталон порівняння | тег `api-v1.0` (коміт `25816cf`) |
| Критерії й інструменти | ті самі, що в [`logs/gate-api.md`](gate-api.md) |
| Фокус | змінена операція `searchListings` |
| Тікет | #114 |
| Рішення | **GO** |

## Diff відносно тега `api-v1.0`

Очікування: змінено лише `info` і `searchListings`. **Підтверджено** двома способами: текстовим `git diff` і порівнянням розібраних YAML-документів.

`git diff --stat api-v1.0 -- api/openapi.yaml`: 1 файл, 31 додавання, 3 видалення.

| Шлях | Зміна |
|------|-------|
| `info.version` | 1.0.0 → 1.1.0 (`title` і `description` без змін) |
| `paths./listings.get.description` | додано абзац про пагінацію й порядок результату |
| `paths./listings.get.x-req-ids` | додано FR-ADD-02 |
| `paths./listings.get.x-acceptance-criteria` | додано AC-ADD-02.1–02.7 |
| `paths./listings.get.parameters` | додано `limit` і `offset` |
| `paths./listings.get.responses.200.headers` | додано `X-Total-Count` |

Без змін: `openapi`, `servers`, `security`, `tags`, `components`, набір шляхів, решта 34 операції. Кількість операцій — 35, доданих і видалених немає.

```diff
@@ info
-  version: 1.0.0
+  version: 1.1.0

@@ /listings get: description
+
+        **Пагінація (з версії 1.1.0, FR-ADD-02).** Повертається не більше
+        `limit` елементів, за замовчуванням 20, починаючи з позиції `offset`.
+        Запит без параметрів пагінації повертає лише перші 20 результатів;
+        загальну кількість знайденого містить заголовок `X-Total-Count`.
+        Порядок: без `sort` — за моментом створення оголошення, від ранішого;
+        з `sort` — за ключем сортування, рівні значення — за моментом створення.

@@ /listings get: x-req-ids, x-acceptance-criteria
-      x-req-ids: [FR-05]
-      x-acceptance-criteria: [AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5]
+      x-req-ids: [FR-05, FR-ADD-02]
+      x-acceptance-criteria: [AC-05.1, AC-05.2, AC-05.3, AC-05.4, AC-05.5, AC-ADD-02.1, AC-ADD-02.2, AC-ADD-02.3, AC-ADD-02.4, AC-ADD-02.5, AC-ADD-02.6, AC-ADD-02.7]

@@ /listings get: parameters
+        - name: limit
+          in: query
+          description: Найбільша кількість елементів у відповіді (FR-ADD-02, spec/addenda/ADD-02.md).
+          schema:
+            type: integer
+            minimum: 1
+            maximum: 100
+            default: 20
+        - name: offset
+          in: query
+          description: Скільки перших елементів упорядкованого результату пропустити (FR-ADD-02).
+          schema:
+            type: integer
+            minimum: 0
+            default: 0

@@ /listings get: responses.200
+          headers:
+            X-Total-Count:
+              description: Загальна кількість знайденого після фільтрів, до застосування limit і offset (FR-ADD-02).
+              schema:
+                type: integer
+                minimum: 0
```

## Критерії контрольної точки

| № | Критерій | Результат | Пояснення |
|---|----------|-----------|-----------|
| 1 | Кожна суттєва операція має обґрунтований зв'язок з REQ-ID | PASS | Усі 35 операцій мають `x-req-ids`. `searchListings` посилається на FR-05 і FR-ADD-02; FR-ADD-02 визначено в затвердженому адендумі. Різних AC у `x-acceptance-criteria` було 128, стало 135, додано рівно AC-ADD-02.1–02.7. Матриці простежуваності ще не оновлено (застереження 4) |
| 2 | Ресурси та термінологія відповідають предметній області та глосарію | PASS | Нових ресурсів і полів предметної області немає. `limit`, `offset`, `X-Total-Count` — технічні ідентифікатори контракту. Терміни, яких слід уникати, у доданому тексті не вживаються. Слово «запит» у значенні HTTP-запиту в новому абзаці опису відповідає вжитку у v1.0 («Запит порушує схему») і не створює неоднозначності, хоча глосарій закріплює за ним значення «бронювання в PENDING» |
| 3 | URI та HTTP-методи використовуються послідовно | PASS | Нових шляхів і методів немає. Пагінація — query-параметри `GET /listings`, за правилом 6 `docs/api-resources.md` (пошук і фільтри — параметри `GET` колекції) |
| 4 | Для операцій визначені request і response schemas | PASS | `limit`: integer, 1–100, `default: 20`. `offset`: integer, ≥ 0, `default: 0`. `X-Total-Count`: integer, ≥ 0. Тіло 200 лишається масивом `Listing`. Значення збігаються з ADD-02 §2 і §4 |
| 5 | Визначені необхідні коди стану HTTP та єдина модель помилок | PASS | `searchListings`: 200, 422, 500. Значення поза межами й не цілі числа дають 422 `application/problem+json` зі схемою `Problem` і кодом `VALIDATION_FAILED` (перевірено S-06…S-10). Нових кодів немає, `components` ідентичні `api-v1.0` |
| 6 | Передбачені позитивні й негативні сценарії | PASS | 16 базових сценаріїв `tests/contract/` без змін. Для `searchListings` на цьому GATE виконано 5 позитивних і 5 негативних перевірок (S-01…S-10, нижче). Сценарії на рівні вимог задано в AC-ADD-02.1–02.7 |
| 7 | API не розкриває без необхідності деталі внутрішньої реалізації | PASS | Додано лише параметри сторінки та загальну кількість результату. Внутрішніх ідентифікаторів, полів сховища чи курсорів немає |
| 8 | OpenAPI specification проходить автоматичну валідацію | PASS | Redocly CLI 2.76.0, набір правил recommended (`redocly.yaml`): 0 помилок, 1 попередження. Попередження те саме, що у v1.0: `info-license` (застереження 1 `logs/gate-api.md`) |
| 9 | Mock API запускається на основі затверджуваної специфікації | PASS | `npx @stoplight/prism-cli mock api/openapi.yaml --port 4010 --errors`, Prism 5.16.0, 35 маршрутів |
| 10 | Основні позитивні й негативні сценарії відтворюються через mock API | PASS | `tests/contract/run-scenarios.ps1` на коміті `4d06561`: 16/16 PASS. Перевірки `searchListings`: 10/10 PASS |

## Перевірки `searchListings` через mock

Запит: `GET /listings` із наведеними параметрами. Для 200 перевірялися статус, цілочисловий заголовок `X-Total-Count` і відсутність порушень у `sl-violations`. Для 422 перевірялися статус, `application/problem+json` і поле `code`.

| Id | Параметри | Очікувано | Отримано | Результат |
|----|-----------|-----------|----------|-----------|
| S-01 | без параметрів | 200 | 200, `X-Total-Count` є | PASS |
| S-02 | `limit=1` | 200 | 200, `X-Total-Count` є | PASS |
| S-03 | `limit=100` | 200 | 200, `X-Total-Count` є | PASS |
| S-04 | `offset=0` | 200 | 200, `X-Total-Count` є | PASS |
| S-05 | `limit=10&offset=30&sort=price_asc` | 200 | 200, `X-Total-Count` є | PASS |
| S-06 | `limit=0` | 422 `VALIDATION_FAILED` | 422 `VALIDATION_FAILED` (`minimum`) | PASS |
| S-07 | `limit=101` | 422 `VALIDATION_FAILED` | 422 `VALIDATION_FAILED` (`maximum`) | PASS |
| S-08 | `offset=-1` | 422 `VALIDATION_FAILED` | 422 `VALIDATION_FAILED` (`minimum`) | PASS |
| S-09 | `limit=abc` | 422 `VALIDATION_FAILED` | 422 `VALIDATION_FAILED` (`type`) | PASS |
| S-10 | `offset=1.5` | 422 `VALIDATION_FAILED` | 422 `VALIDATION_FAILED` (`type`) | PASS |

## Застереження

1. **Mock не обчислює пагінацію.** Prism не зберігає стан, ігнорує значення `limit` і `offset` у відповіді й повертає `X-Total-Count: 0` разом із прикладом з одним елементом. Через mock підтверджено форму контракту та AC-ADD-02.4. Поведінку AC-ADD-02.1–02.3 і 02.5–02.7 мають перевірити API-тести.
2. **Schemathesis не запускався.** У `logs/gate-api.md` цього інструмента не було, тому він не входить до критеріїв цього GATE. Ризик 7 адендуму ADD-02 його називає. У `src/` реалізації `limit`, `offset` і `X-Total-Count` ще немає, тож прогін проти сервера має сенс після реалізації.
3. **Перевірки S-01…S-10 не додано до `tests/contract/`.** Їх результат зафіксовано лише в цьому документі. Сценарій P-03 пагінацію не використовує.
4. **Супутні документи ще описують версію 1.0.0.**
   - `docs/api-resources.md`: у §4 для `GET /listings` указано лише FR-05; у §6 лишився запис «Пагінація списків — не вводиться у v1»; `limit`, `offset`, `X-Total-Count` не внесено до переліку ідентифікаторів поза глосарієм.
   - `docs/api-traceability.md` (генерований файл): для `searchListings` лише FR-05 і 5 AC.
   - `spec/traceability.csv` і `spec/srs.md` оновлюються за ADD-02 §4 після затвердження.
   - Двох файлів `docs/api-*.md` немає в переліку впливу ADD-02 §4.
5. **Застереження 5 `logs/gate-api.md` закрито лише для `searchListings`.** Інші переліки, зокрема журнал подій, пагінації не мають.
6. **Протоколи v1.0 не перезаписано.** `logs/api-lint.log` і `logs/api-scenarios.log` лишаються доказами для `api-v1.0`; результати цього прогону наведено тут.
7. **Тег `api-v1.1` не створено**, цей документ не закомічено.

## Рішення

Усі 10 критеріїв — PASS.

API-GATE: GO
