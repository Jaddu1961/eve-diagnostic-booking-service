import json
import random
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Booking, BookingStatus, Payment, PaymentStatus, User, WebhookEvent
from ..schemas import PaymentIn, PaymentOut, WebhookIn
from ..security import verify_webhook_signature
from ..services import apply_payment_result

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(body: PaymentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Simulated payment. Resolves immediately to SUCCESS/FAILED, or stays PENDING
    (outcome="PENDING") until the provider calls the webhook."""
    # Row lock serialises concurrent payment attempts for the same booking.
    booking = db.scalar(
        select(Booking).where(Booking.id == body.booking_id, Booking.user_id == user.id).with_for_update()
    )
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status == BookingStatus.CONFIRMED:
        raise HTTPException(409, "Booking is already paid")
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(409, "Cannot pay for a cancelled booking")
    if any(p.status == PaymentStatus.PENDING for p in booking.payments):
        raise HTTPException(409, "A payment for this booking is already in progress")

    outcome = body.outcome or ("SUCCESS" if random.random() < settings.payment_success_rate else "FAILED")

    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=PaymentStatus.PENDING,
        provider_reference=f"sim_{uuid.uuid4().hex}",
    )
    db.add(payment)
    if booking.status == BookingStatus.FAILED:
        booking.status = BookingStatus.PENDING  # retry after a failed attempt
    if outcome != "PENDING":
        apply_payment_result(booking, payment, PaymentStatus(outcome))
    try:
        db.commit()
    except IntegrityError:  # partial unique indexes caught a race
        db.rollback()
        raise HTTPException(409, "A payment for this booking is already in progress or completed")
    db.refresh(payment)
    return payment


async def raw_body(request: Request) -> bytes:
    return await request.body()


@router.post("/webhook/")
def payment_webhook(
    body: bytes = Depends(raw_body),
    x_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Provider callback. Authenticated by HMAC-SHA256 of the raw body (X-Signature header).

    Idempotency: every event carries a unique `event_id`, stored under a UNIQUE constraint.
    The insert and the state change commit in ONE transaction, so:
      * a replay hits the constraint -> 200 "duplicate", nothing is touched
      * two concurrent deliveries: one wins the insert, the other gets the constraint error
      * if processing crashes, the event row rolls back too, so the provider's retry is processed
    """
    if not verify_webhook_signature(body, x_signature):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        event = WebhookIn.model_validate(json.loads(body))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, f"Invalid webhook payload: {exc}")

    db.add(
        WebhookEvent(
            event_id=event.event_id,
            provider_reference=event.provider_reference,
            status=event.status,
            payload=event.model_dump(),
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "event_id": event.event_id}

    payment = db.scalar(
        select(Payment).where(Payment.provider_reference == event.provider_reference).with_for_update()
    )
    if not payment:
        db.rollback()  # don't record the event; the provider may retry once the payment exists
        raise HTTPException(404, "Unknown provider_reference")
    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())

    changed = apply_payment_result(booking, payment, PaymentStatus(event.status))
    db.commit()
    return {
        "status": "processed" if changed else "ignored",
        "event_id": event.event_id,
        "payment_status": payment.status.value,
        "booking_status": booking.status.value,
    }
