# Diagnostic Test Booking & Simulated Payments Service

FastAPI + SQLAlchemy 2.0 + PostgreSQL (SQLite works for quick local runs/tests). JWT auth.

## Run

```bash
docker compose up -d                      # PostgreSQL
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)
python -m app.seed                        # tables + admin user + sample centres/tests
uvicorn app.main:app --reload             # docs at http://localhost:8000/docs
pytest                                    # runs on SQLite, no DB needed
```

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | – | Register (email, full_name, password ≥ 8 chars with letters+digits) |
| POST | `/auth/login` | – | Returns JWT |
| GET | `/auth/me` | user | Current user |
| GET | `/tests/`, `/centres/`, `/centres/{id}` | – | Browse. `/centres/?location=&test=&limit=&offset=` |
| POST | `/tests/`, `/centres/` | admin | Create test / centre (with tests + prices) |
| PUT | `/centres/{id}/tests` | admin | Offer a test at a centre or change its price |
| POST | `/bookings/` | user | Book `{centre_id, test_id, appointment_at}` → `PENDING` |
| GET | `/bookings/`, `/bookings/{id}` | user | Own bookings only |
| POST | `/bookings/{id}/cancel` | user | Cancel own booking |
| POST | `/payments/` | user | Simulated payment `{booking_id, outcome?}` |
| POST | `/payments/webhook/` | HMAC | Provider status callback (idempotent) |

Seeded admin: `admin@example.com` / `Admin@12345` (from `.env`).

## Data model

`users`, `centres`, `tests` (catalogue), `centre_tests` (centre × test × **price**), `bookings`
(user, centre, test, appointment_at, **amount snapshot**, status), `payments` (booking, amount, status,
unique `provider_reference`), `webhook_events` (unique `event_id`).

## Key design decisions

- **Server-side pricing.** Booking amount is copied from `centre_tests.price` at booking time; the client never
  sends money. Later price changes don't affect existing bookings.
- **State machine** (`app/services.py`), shared by `/payments/` and the webhook:
  payment `PENDING → SUCCESS | FAILED` is one-way; booking `PENDING/FAILED → CONFIRMED` on success,
  `PENDING → FAILED` on failure. A confirmed booking is never downgraded; a cancelled one is never revived.
  A failed booking can be paid again (a new payment row; booking returns to `PENDING`).
- **Simulated payment.** `outcome` (`SUCCESS`/`FAILED`/`PENDING`) forces a result for testing; omitted = random
  (`PAYMENT_SUCCESS_RATE`). `PENDING` simulates an async provider that finishes via the webhook.
- **Webhook idempotency (3 layers).**
  1. `webhook_events.event_id` is UNIQUE. The event row and the state change commit in **one transaction**;
     a replay hits the constraint and returns `200 {"status": "duplicate"}` without touching anything.
     Concurrent deliveries are safe: one wins the insert, the other gets the constraint error.
  2. The transition function is idempotent and ignores events for already-final payments
     (e.g. a late `FAILED` after `SUCCESS` returns `ignored`).
  3. Partial unique indexes: max one `PENDING` and one `SUCCESS` payment per booking → no double charge even under races.
  If processing crashes, the event insert rolls back too, so the provider's retry is processed normally.
- **Webhook authentication.** `X-Signature` = hex HMAC-SHA256 of the raw body with `PAYMENT_WEBHOOK_SECRET`
  (constant-time compare). Unknown `provider_reference` → 404 (event not recorded, so a retry can succeed later).
- **Concurrency.** `SELECT ... FOR UPDATE` on the booking/payment rows when paying, cancelling, or handling webhooks.
- **Authorization.** Other users' bookings return **404** (not 403) so IDs can't be probed. Catalogue writes are admin-only.
  Login returns the same error for unknown email and wrong password.

## Edge cases covered (see `tests/test_flow.py`)

invalid/duplicate signup · wrong password · missing/garbage JWT · non-admin writes · test not offered by centre ·
past or timezone-less appointment · other user's booking · non-existent booking ID · paying twice · paying a cancelled
booking · cancelling twice · failed payment then retry · webhook: bad/missing signature, malformed JSON, invalid
status, unknown reference, replayed event (×4), conflicting late event.

## Triggering a webhook manually

```bash
BODY='{"event_id":"evt_1001","provider_reference":"sim_...","status":"SUCCESS"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$PAYMENT_WEBHOOK_SECRET" | awk '{print $2}')
curl -X POST localhost:8000/payments/webhook/ -H "X-Signature: $SIG" -H "Content-Type: application/json" -d "$BODY"
```
Send it twice: the second response is `{"status":"duplicate"}`.

## Known simplifications / next steps

Alembic migrations instead of `create_all`; refresh tokens; refunds when a payment lands on a cancelled booking
(currently logged); slot-capacity/double-booking rules per centre; rate limiting.
