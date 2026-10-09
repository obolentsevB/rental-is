# Простежуваність REQ-ID ↔ API operations

Згенеровано `docs/scripts/api_traceability.py` з `api/openapi.yaml` (розширення `x-req-ids`, `x-side-effects`, `x-acceptance-criteria`, `x-roles`) і `tests/contract/run-scenarios.ps1`. Вручну не редагувати.

## 1. Операції

| № | operationId | Метод і шлях | REQ-ID | Наслідки | AC | Хто | Сценарії |
|---|---|---|---|---|---|---|---|
| 1 | `registerUser` | POST `/users` | FR-01 | — | 4 | anonymous | P-01, N-03 |
| 2 | `getCurrentUser` | GET `/users/me` | FR-01 | — | 1 | guest, host, moderator, blocked | — |
| 3 | `blockUser` | POST `/users/{userId}/block` | FR-19 | FR-04, FR-13, FR-14, FR-15, FR-18, FR-23 | 11 | moderator | — |
| 4 | `createSession` | POST `/auth/session` | FR-01, NFR-11 | FR-22 | 6 | anonymous | P-02 |
| 5 | `deleteSession` | DELETE `/auth/session` | FR-01 | — | 0 | guest, host, moderator, blocked | — |
| 6 | `searchListings` | GET `/listings` | FR-05 | — | 5 | anonymous, guest, host, moderator | P-03 |
| 7 | `createListing` | POST `/listings` | FR-02 | FR-22 | 7 | host | N-07 |
| 8 | `getListing` | GET `/listings/{listingId}` | FR-02 | — | 3 | anonymous, guest, host, moderator | — |
| 9 | `replaceListing` | PUT `/listings/{listingId}` | FR-02 | FR-22 | 7 | host | — |
| 10 | `unpublishListing` | POST `/listings/{listingId}/unpublish` | FR-04 | FR-15, FR-23 | 6 | moderator | — |
| 11 | `publishListing` | POST `/listings/{listingId}/publish` | FR-04 | — | 2 | moderator | — |
| 12 | `listClosedNights` | GET `/listings/{listingId}/closed-nights` | FR-03 | — | 0 | host | — |
| 13 | `closeNight` | PUT `/listings/{listingId}/closed-nights/{date}` | FR-03 | FR-15, FR-23 | 5 | host | — |
| 14 | `openNight` | DELETE `/listings/{listingId}/closed-nights/{date}` | FR-03 | — | 1 | host | — |
| 15 | `listListingReviews` | GET `/listings/{listingId}/reviews` | FR-18 | — | 5 | anonymous, guest, host, moderator | — |
| 16 | `listBookings` | GET `/bookings` | FR-12 | — | 5 | guest, host, blocked | P-06 |
| 17 | `createBooking` | POST `/bookings` | FR-06, FR-07, FR-08, FR-15 | FR-22 | 22 | guest | P-04, N-01, N-02, N-04, N-05, N-06, C-01 |
| 18 | `getBooking` | GET `/bookings/{bookingId}` | FR-12 | — | 1 | guest, host, blocked | — |
| 19 | `confirmBooking` | POST `/bookings/{bookingId}/confirm` | FR-09, NFR-01 | FR-15, FR-22, FR-23 | 12 | host | P-05, N-08 |
| 20 | `rejectBooking` | POST `/bookings/{bookingId}/reject` | FR-09 | FR-15, FR-23 | 5 | host | — |
| 21 | `cancelBooking` | POST `/bookings/{bookingId}/cancel` | FR-13 | FR-14, FR-15, FR-16, FR-23 | 20 | guest, host | — |
| 22 | `listBookingPayments` | GET `/bookings/{bookingId}/payments` | FR-15, FR-16 | — | 13 | guest, host | — |
| 23 | `createReview` | POST `/bookings/{bookingId}/reviews` | FR-17 | — | 4 | guest | P-07 |
| 24 | `replaceReview` | PUT `/reviews/{reviewId}` | FR-17 | — | 2 | guest | — |
| 25 | `createComplaint` | POST `/reviews/{reviewId}/complaints` | FR-18 | FR-22, FR-23 | 4 | host | — |
| 26 | `listComplaints` | GET `/complaints` | FR-18 | — | 1 | moderator | — |
| 27 | `decideComplaint` | POST `/complaints/{complaintId}/decision` | FR-18 | FR-23 | 4 | moderator | — |
| 28 | `createDispute` | POST `/bookings/{bookingId}/disputes` | FR-20 | FR-22, FR-23 | 5 | guest | — |
| 29 | `listDisputes` | GET `/disputes` | FR-20 | — | 1 | moderator | — |
| 30 | `decideDispute` | POST `/disputes/{disputeId}/decision` | FR-20 | FR-15, FR-16, FR-23 | 8 | moderator | — |
| 31 | `listAppeals` | GET `/appeals` | FR-21 | — | 1 | moderator | — |
| 32 | `createAppeal` | POST `/appeals` | FR-21 | FR-22, FR-23 | 4 | blocked, host | — |
| 33 | `decideAppeal` | POST `/appeals/{appealId}/decision` | FR-21 | FR-04, FR-18, FR-23 | 7 | moderator | — |
| 34 | `listEvents` | GET `/events` | FR-22, NFR-06 | — | 9 | guest, host, moderator | — |
| 35 | `listNotifications` | GET `/notifications` | FR-23 | — | 3 | guest, host, moderator, blocked | — |

## 2. Покриття функціональних вимог

| Вимога | Основна операція | Операції, що спричиняють наслідки |
|---|---|---|
| FR-01 | `registerUser`, `getCurrentUser`, `createSession`, `deleteSession` | — |
| FR-02 | `createListing`, `getListing`, `replaceListing` | — |
| FR-03 | `listClosedNights`, `closeNight`, `openNight` | — |
| FR-04 | `unpublishListing`, `publishListing` | `blockUser`, `decideAppeal` |
| FR-05 | `searchListings` | — |
| FR-06 | `createBooking` | — |
| FR-07 | `createBooking` | — |
| FR-08 | `createBooking` | — |
| FR-09 | `confirmBooking`, `rejectBooking` | — |
| FR-10 | — | — |
| FR-11 | — | — |
| FR-12 | `listBookings`, `getBooking` | — |
| FR-13 | `cancelBooking` | `blockUser` |
| FR-14 | — | `blockUser`, `cancelBooking` |
| FR-15 | `createBooking`, `listBookingPayments` | `blockUser`, `unpublishListing`, `closeNight`, `confirmBooking`, `rejectBooking`, `cancelBooking`, `decideDispute` |
| FR-16 | `listBookingPayments` | `cancelBooking`, `decideDispute` |
| FR-17 | `createReview`, `replaceReview` | — |
| FR-18 | `listListingReviews`, `createComplaint`, `listComplaints`, `decideComplaint` | `blockUser`, `decideAppeal` |
| FR-19 | `blockUser` | — |
| FR-20 | `createDispute`, `listDisputes`, `decideDispute` | — |
| FR-21 | `listAppeals`, `createAppeal`, `decideAppeal` | — |
| FR-22 | `listEvents` | `createSession`, `createListing`, `replaceListing`, `createBooking`, `confirmBooking`, `createComplaint`, `createDispute`, `createAppeal` |
| FR-23 | `listNotifications` | `blockUser`, `unpublishListing`, `closeNight`, `confirmBooking`, `rejectBooking`, `cancelBooking`, `createComplaint`, `decideComplaint`, `createDispute`, `decideDispute`, `createAppeal`, `decideAppeal` |

## 3. Вимоги без операцій

| Вимога | Чому немає операції |
|---|---|
| FR-10 | Автоматична дія системи, операції немає: результат видно через getBooking і listBookings. |
| FR-11 | Автоматична дія системи, операції немає: результат видно через getBooking і listBookings. |

## 4. Підсумок

- Операцій: 35; зі сценаріями: 8.
- Функціональних вимог: 23; з основною операцією: 20; лише як наслідок: 1; без операцій: 2.
- Нефункціональні вимоги в контракті: NFR-01, NFR-06, NFR-11.
- Критеріїв прийняття в SRS: 157; позначено в операціях: 128; перевіряються сценаріями проти mock: 8.
