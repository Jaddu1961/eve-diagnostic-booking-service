import json

from app.security import sign_webhook
from tests.conftest import signup_login

FUTURE = "2099-01-01T10:00:00+05:30"


def make_booking(client, headers, centre_id=1, test_id=1):
    return client.post("/bookings/", headers=headers,
                       json={"centre_id": centre_id, "test_id": test_id, "appointment_at": FUTURE})


def send_webhook(client, payload, signature=None):
    raw = json.dumps(payload).encode()
    return client.post("/payments/webhook/", content=raw,
                       headers={"X-Signature": signature or sign_webhook(raw), "Content-Type": "application/json"})


# ---------- auth ----------
def test_signup_validation_and_duplicate(client):
    assert client.post("/auth/signup", json={"email": "bad", "full_name": "x", "password": "Passw0rd123"}).status_code == 422
    assert client.post("/auth/signup", json={"email": "a@b.com", "full_name": "x", "password": "short"}).status_code == 422
    ok = {"email": "a@b.com", "full_name": "x", "password": "Passw0rd123"}
    assert client.post("/auth/signup", json=ok).status_code == 201
    assert client.post("/auth/signup", json=ok).status_code == 409


def test_login_wrong_password_and_protected_routes(client):
    signup_login(client)
    assert client.post("/auth/login", json={"email": "user@example.com", "password": "nope12345"}).status_code == 401
    assert client.get("/bookings/").status_code == 401
    assert client.get("/bookings/", headers={"Authorization": "Bearer garbage"}).status_code == 401


# ---------- catalogue ----------
def test_centres_public_read_admin_only_write(client):
    assert client.get("/centres/").status_code == 200
    assert len(client.get("/centres/?location=ahmed").json()) == 1
    assert len(client.get("/centres/?test=mri").json()) == 1
    user = signup_login(client)
    assert client.post("/centres/", headers=user, json={"name": "X", "location": "Y"}).status_code == 403
    assert client.post("/centres/", json={"name": "X", "location": "Y"}).status_code == 401
    admin = client.post("/auth/login", json={"email": "admin@example.com", "password": "Admin@12345"}).json()
    r = client.post("/centres/", headers={"Authorization": f"Bearer {admin['access_token']}"},
                    json={"name": "New", "location": "Pune", "tests": [{"test_id": 1, "price": "199.50"}]})
    assert r.status_code == 201 and r.json()["offerings"][0]["price"] in ("199.50", "199.5")


# ---------- booking ----------
def test_booking_rules(client):
    h = signup_login(client)
    b = make_booking(client, h)
    assert b.status_code == 201
    assert b.json()["status"] == "PENDING" and float(b.json()["amount"]) == 350.0
    # centre 1 doesn't offer test 3 (MRI)
    assert make_booking(client, h, 1, 3).status_code == 404
    past = client.post("/bookings/", headers=h, json={"centre_id": 1, "test_id": 1, "appointment_at": "2000-01-01T10:00:00+00:00"})
    assert past.status_code == 422
    naive = client.post("/bookings/", headers=h, json={"centre_id": 1, "test_id": 1, "appointment_at": "2099-01-01T10:00:00"})
    assert naive.status_code == 422


def test_cannot_touch_other_users_booking(client):
    owner = signup_login(client, "owner@example.com")
    other = signup_login(client, "other@example.com")
    bid = make_booking(client, owner).json()["id"]
    assert client.get(f"/bookings/{bid}", headers=other).status_code == 404
    assert client.post(f"/bookings/{bid}/cancel", headers=other).status_code == 404
    assert client.post("/payments/", headers=other, json={"booking_id": bid}).status_code == 404
    assert client.get("/bookings/99999", headers=owner).status_code == 404


# ---------- payments ----------
def test_payment_success_confirms_booking_and_blocks_double_pay(client):
    h = signup_login(client)
    bid = make_booking(client, h).json()["id"]
    r = client.post("/payments/", headers=h, json={"booking_id": bid, "outcome": "SUCCESS"})
    assert r.status_code == 201 and r.json()["status"] == "SUCCESS"
    assert client.get(f"/bookings/{bid}", headers=h).json()["status"] == "CONFIRMED"
    assert client.post("/payments/", headers=h, json={"booking_id": bid, "outcome": "SUCCESS"}).status_code == 409


def test_failed_payment_then_retry(client):
    h = signup_login(client)
    bid = make_booking(client, h).json()["id"]
    assert client.post("/payments/", headers=h, json={"booking_id": bid, "outcome": "FAILED"}).json()["status"] == "FAILED"
    assert client.get(f"/bookings/{bid}", headers=h).json()["status"] == "FAILED"
    assert client.post("/payments/", headers=h, json={"booking_id": bid, "outcome": "SUCCESS"}).status_code == 201
    assert client.get(f"/bookings/{bid}", headers=h).json()["status"] == "CONFIRMED"


def test_invalid_payment_requests(client):
    h = signup_login(client)
    assert client.post("/payments/", headers=h, json={"booking_id": 424242}).status_code == 404
    assert client.post("/payments/", headers=h, json={}).status_code == 422
    assert client.post("/payments/", json={"booking_id": 1}).status_code == 401
    bid = make_booking(client, h).json()["id"]
    client.post(f"/bookings/{bid}/cancel", headers=h)
    assert client.post("/payments/", headers=h, json={"booking_id": bid}).status_code == 409
    assert client.post(f"/bookings/{bid}/cancel", headers=h).status_code == 409


# ---------- webhook ----------
def pending_payment(client, h):
    bid = make_booking(client, h).json()["id"]
    pay = client.post("/payments/", headers=h, json={"booking_id": bid, "outcome": "PENDING"}).json()
    return bid, pay


def test_webhook_is_idempotent(client):
    h = signup_login(client)
    bid, pay = pending_payment(client, h)
    evt = {"event_id": "evt_1", "provider_reference": pay["provider_reference"], "status": "SUCCESS"}

    first = send_webhook(client, evt)
    assert first.status_code == 200 and first.json()["status"] == "processed"
    for _ in range(3):
        again = send_webhook(client, evt)
        assert again.status_code == 200 and again.json()["status"] == "duplicate"

    booking = client.get(f"/bookings/{bid}", headers=h).json()
    assert booking["status"] == "CONFIRMED"
    assert len(booking["payments"]) == 1  # no duplicate payments


def test_webhook_late_conflicting_event_is_ignored(client):
    h = signup_login(client)
    bid, pay = pending_payment(client, h)
    ref = pay["provider_reference"]
    send_webhook(client, {"event_id": "e1", "provider_reference": ref, "status": "SUCCESS"})
    r = send_webhook(client, {"event_id": "e2", "provider_reference": ref, "status": "FAILED"})
    assert r.status_code == 200 and r.json()["status"] == "ignored"
    assert client.get(f"/bookings/{bid}", headers=h).json()["status"] == "CONFIRMED"


def test_webhook_failure_marks_booking_failed(client):
    h = signup_login(client)
    bid, pay = pending_payment(client, h)
    send_webhook(client, {"event_id": "e1", "provider_reference": pay["provider_reference"], "status": "FAILED"})
    assert client.get(f"/bookings/{bid}", headers=h).json()["status"] == "FAILED"


def test_webhook_security_and_validation(client):
    payload = {"event_id": "e1", "provider_reference": "sim_x", "status": "SUCCESS"}
    assert send_webhook(client, payload, signature="bad").status_code == 401
    assert client.post("/payments/webhook/", json=payload).status_code == 401  # no signature
    assert send_webhook(client, payload).status_code == 404  # unknown reference
    assert send_webhook(client, {"event_id": "e2", "provider_reference": "sim_x", "status": "WEIRD"}).status_code == 422
    raw = b"not json"
    r = client.post("/payments/webhook/", content=raw, headers={"X-Signature": sign_webhook(raw)})
    assert r.status_code == 422
