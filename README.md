# EVE Diagnostic Booking Service

A backend service for managing diagnostic test bookings, diagnostic centres, authentication, simulated payments, and payment webhooks.

The project is built using **FastAPI**, **SQLAlchemy**, **SQLite**, and **JWT-based authentication**, with a lightweight browser-based frontend for demonstrating the complete booking flow.

---

## 🚀 Features

* User registration and authentication
* JWT-based authorization
* Diagnostic test management
* Diagnostic centre management
* Centre-to-test availability mapping
* Search centres by location and test
* Paginated centre listing
* Appointment booking
* View and cancel bookings
* Simulated payment processing
* Payment status tracking
* Payment webhook handling
* Webhook idempotency using unique event IDs
* HMAC-SHA256 webhook signature validation
* Transaction-safe payment updates
* API validation using Pydantic
* Swagger/OpenAPI documentation
* Automated tests using Pytest
* Docker / Docker Compose support
* Browser-based demo UI

---

## 🏗️ Tech Stack

| Component         | Technology              |
| ----------------- | ----------------------- |
| Backend           | FastAPI                 |
| Language          | Python                  |
| ORM               | SQLAlchemy              |
| Database          | SQLite                  |
| Authentication    | JWT                     |
| Password Hashing  | bcrypt/passlib          |
| Validation        | Pydantic                |
| Testing           | Pytest                  |
| API Documentation | Swagger / OpenAPI       |
| Frontend          | HTML, CSS, JavaScript   |
| Containerization  | Docker / Docker Compose |

---

## 📁 Project Structure

```text
eve-booking/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── seed.py
│   ├── services.py
│   │
│   └── routers/
│       ├── auth.py
│       ├── bookings.py
│       ├── centres.py
│       └── payments.py
│
├── tests/
│   ├── conftest.py
│   └── test_flow.py
│
├── eve-booking-demo.html
├── requirements.txt
├── pytest.ini
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

---

# ⚙️ Getting Started

## 1. Clone the repository

```bash
git clone https://github.com/Jaddu1961/eve-diagnostic-booking-service.git
cd eve-diagnostic-booking-service
```

---

## 2. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create a `.env` file using `.env.example`:

```bash
cp .env.example .env
```

Example configuration:

```env
DATABASE_URL=sqlite:///./dev.db
SECRET_KEY=change-this-secret-key
WEBHOOK_SECRET=change-this-webhook-secret
```

---

# ▶️ Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

---

# 📚 API Documentation

FastAPI automatically provides interactive API documentation.

### Swagger UI

```text
http://localhost:8000/docs
```

### OpenAPI JSON

```text
http://localhost:8000/openapi.json
```

---

# 🌐 Browser Demo

The project includes a standalone browser-based frontend:

```text
eve-booking-demo.html
```

Open it in a browser after starting the backend.

### macOS

```bash
open eve-booking-demo.html
```

The frontend communicates with the FastAPI backend running on:

```text
http://localhost:8000
```

The UI demonstrates:

1. User login
2. Diagnostic centre search
3. Test selection
4. Appointment booking
5. Payment simulation
6. Booking history
7. Booking cancellation

---

# 🔐 Authentication

The API uses **JWT Bearer Authentication** for protected endpoints.

## Signup

```http
POST /auth/signup
```

Example:

```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "Test User"
}
```

---

## Login

```http
POST /auth/login
```

Example:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

The API returns an access token.

Use the token for protected requests:

```http
Authorization: Bearer <access_token>
```

---

## Current User

```http
GET /auth/me
```

Requires authentication.

---

# 🧪 Diagnostic Tests

## List Tests

```http
GET /tests/
```

Returns the available diagnostic tests.

---

## Create Test

```http
POST /tests/
```

Requires authentication.

Example:

```json
{
  "name": "Complete Blood Count",
  "description": "Basic blood examination",
  "price": 500
}
```

---

# 🏥 Diagnostic Centres

## Search Centres

```http
GET /centres/
```

Supported query parameters include:

```text
location
test
limit
offset
```

Example:

```text
GET /centres/?location=Pune&test=Blood&limit=10&offset=0
```

---

## Create Centre

```http
POST /centres/
```

Requires authentication.

Example:

```json
{
  "name": "EVE Diagnostics Pune",
  "location": "Pune",
  "address": "123 Main Road, Pune"
}
```

---

## Get Centre

```http
GET /centres/{centre_id}
```

Returns details of a specific diagnostic centre.

---

## Assign Tests to Centre

```http
PUT /centres/{centre_id}/tests
```

Requires authentication.

This endpoint associates available diagnostic tests with a centre.

---

# 📅 Bookings

## Create Booking

```http
POST /bookings/
```

Requires authentication.

Example:

```json
{
  "centre_id": 1,
  "test_id": 1,
  "appointment_at": "2026-10-05T10:00:00"
}
```

The booking is associated with the authenticated user.

---

## List My Bookings

```http
GET /bookings/
```

Requires authentication.

Returns bookings belonging to the current user.

---

## Get Booking

```http
GET /bookings/{booking_id}
```

Requires authentication.

---

## Cancel Booking

```http
POST /bookings/{booking_id}/cancel
```

Requires authentication.

The endpoint cancels the selected booking if it is eligible for cancellation.

---

# 💳 Payments

The project includes a simulated payment flow for demonstration purposes.

## Create Payment

```http
POST /payments/
```

Requires authentication.

Example:

```json
{
  "booking_id": 1,
  "outcome": "SUCCESS"
}
```

Supported demo outcomes:

```text
SUCCESS
FAILED
PENDING
```

The browser demo exposes these payment outcomes to demonstrate different payment states.

---

# 🔄 Payment Webhooks

The payment service provides a webhook endpoint for receiving payment-provider events.

```http
POST /payments/webhook/
```

Example payload:

```json
{
  "event_id": "evt_12345",
  "booking_id": 1,
  "status": "SUCCESS"
}
```

Optional HMAC signature:

```http
X-Signature: <hmac_sha256_signature>
```

### Webhook Security

The webhook implementation is designed around:

* HMAC-SHA256 signature validation
* Unique event IDs
* Idempotent event processing
* Transaction-safe database updates

---

# ♻️ Webhook Idempotency

Payment webhooks may be delivered more than once by an external payment provider.

The service therefore treats the payment event ID as unique.

For example:

```text
Event ID: evt_12345
```

If the same event is received again, it should not create a duplicate payment or apply the same state transition repeatedly.

This provides safer handling of webhook retries.

---

# 🗄️ Database Design

The application uses **SQLite** with **SQLAlchemy ORM**.

The core entities are:

```text
User
 │
 └──< Booking >── DiagnosticCentre
          │
          ├── DiagnosticTest
          │
          └── Payment
```

### User

Stores authentication and user information.

Typical fields include:

```text
id
email
password_hash
name
```

---

### DiagnosticTest

Represents an available diagnostic test.

Example:

```text
id
name
description
price
```

---

### DiagnosticCentre

Represents a diagnostic centre.

Example:

```text
id
name
location
address
```

---

### Booking

Represents a user's appointment.

Example:

```text
id
user_id
centre_id
test_id
appointment_at
status
```

---

### Payment

Represents payment information associated with a booking.

Example:

```text
id
booking_id
status
event_id
created_at
```

---

# 🔗 Main Relationships

### User → Booking

One user can create multiple bookings.

```text
User 1 ──────── * Booking
```

### Diagnostic Centre → Booking

A centre can have multiple bookings.

```text
Centre 1 ──────── * Booking
```

### Diagnostic Test → Booking

A diagnostic test can be associated with multiple bookings.

```text
Test 1 ──────── * Booking
```

### Booking → Payment

A booking can have associated payment information.

```text
Booking 1 ──────── Payment
```

---

# 🧪 Running Tests

The project uses **Pytest**.

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

The test suite covers the main booking workflow and API behaviour.

---

# 🐳 Docker

The project also supports Docker-based execution.

Build and start the application:

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

Stop the containers:

```bash
docker compose down
```

---

# ❤️ Health Check

The service provides a health endpoint:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

This can be used by deployment platforms or container orchestration systems to verify that the service is running.

---

# 🧠 Important Assumptions

The following assumptions were made while implementing the assignment:

1. SQLite is sufficient for the assessment and local development environment.
2. Authentication is handled using JWT access tokens.
3. Payments are simulated rather than connected to a real payment provider.
4. Payment-provider webhook events are identified using a unique event ID.
5. Webhook signatures use HMAC-SHA256.
6. Diagnostic centre availability is represented through the centre/test relationship.
7. Appointment availability is validated by the backend before creating a booking.
8. Users can access their own bookings through authenticated endpoints.
9. The browser frontend is provided as a lightweight demonstration client rather than a production frontend application.
10. Payment outcomes are simulated for demonstrating successful, failed, and pending payment flows.

---

# ⚠️ Edge Cases Considered

The application considers common booking and payment scenarios such as:

* Invalid login credentials
* Duplicate user registration
* Unauthorized API requests
* Invalid authentication tokens
* Invalid centre or test IDs
* Invalid booking requests
* Booking cancellation
* Duplicate payment webhook events
* Invalid webhook signatures
* Repeated webhook delivery
* Invalid payment states
* Pagination of centre results

---

# 🔒 Security Considerations

The following security practices are incorporated into the service:

* Passwords are stored as hashes rather than plaintext.
* Protected endpoints require JWT authentication.
* Webhook requests can be verified using HMAC-SHA256.
* Webhook event IDs are treated as unique for idempotency.
* Secrets are loaded from environment variables.
* `.env` files are excluded from version control.
* API request payloads are validated using Pydantic.

For a production deployment, additional security controls would be required.

---

# 📈 Possible Improvements

If more development time were available, I would consider adding:

### 1. Redis Caching

Cache frequently accessed data such as:

* Diagnostic tests
* Centre searches
* Centre/test mappings

This could reduce database load.

### 2. Background Jobs

Introduce Celery or another background task system for:

* Email notifications
* Payment reconciliation
* Webhook retry processing
* Booking reminders

### 3. Production Database

Replace SQLite with PostgreSQL for production workloads.

### 4. Rate Limiting

Add rate limiting for:

* Login
* Signup
* Payment endpoints
* Webhook endpoints

### 5. Observability

Add structured logging, metrics, and distributed tracing.

### 6. Better Booking Availability

Introduce explicit time-slot management and prevent overlapping appointments using database-level constraints.

### 7. CI/CD

Add GitHub Actions to automatically:

* Install dependencies
* Run tests
* Perform linting
* Build the Docker image
* Validate the application before merging

### 8. Frontend Improvements

Replace the standalone HTML demo with a production frontend using React/Next.js.

---

# 📊 API Summary

| Method | Endpoint                        | Authentication     | Purpose                  |
| ------ | ------------------------------- | ------------------ | ------------------------ |
| POST   | `/auth/signup`                  | No                 | Register user            |
| POST   | `/auth/login`                   | No                 | Login                    |
| GET    | `/auth/me`                      | Yes                | Get current user         |
| GET    | `/tests/`                       | No                 | List tests               |
| POST   | `/tests/`                       | Yes                | Create test              |
| GET    | `/centres/`                     | No                 | Search centres           |
| POST   | `/centres/`                     | Yes                | Create centre            |
| GET    | `/centres/{centre_id}`          | No                 | Get centre               |
| PUT    | `/centres/{centre_id}/tests`    | Yes                | Update centre tests      |
| GET    | `/bookings/`                    | Yes                | List user bookings       |
| POST   | `/bookings/`                    | Yes                | Create booking           |
| GET    | `/bookings/{booking_id}`        | Yes                | Get booking              |
| POST   | `/bookings/{booking_id}/cancel` | Yes                | Cancel booking           |
| POST   | `/payments/`                    | Yes                | Create simulated payment |
| POST   | `/payments/webhook/`            | Optional signature | Process payment webhook  |
| GET    | `/health`                       | No                 | Health check             |

---

# 📌 Example End-to-End Flow

The intended workflow is:

```text
                ┌───────────────┐
                │     Signup    │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │     Login     │
                └───────┬───────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Search Diagnostic │
              │     Centres       │
              └─────────┬─────────┘
                        │
                        ▼
                ┌───────────────┐
                │ Select Test   │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ Create Booking│
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │    Payment    │
                └───────┬───────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          SUCCESS     FAILED     PENDING
             │          │          │
             └──────────┼──────────┘
                        ▼
                ┌───────────────┐
                │ Payment State │
                │    Updated    │
                └───────────────┘
```


---

# 👨‍💻 Author

**Jadeja Kirtiraj**

M.Tech Student
IIIT Pune

GitHub: [Jaddu1961](https://github.com/Jaddu1961)

---

## 📄 License

This project was developed as part of a technical assessment and is intended for educational and evaluation purposes.
