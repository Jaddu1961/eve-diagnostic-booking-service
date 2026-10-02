from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Booking, BookingStatus, CentreTest, User
from ..schemas import BookingIn, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _own_booking(db: Session, booking_id: int, user: User, lock: bool = False) -> Booking:
    """Fetch a booking owned by `user`. Others' bookings look identical to missing ones (404),
    so booking IDs can't be probed."""
    stmt = select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    booking = db.scalar(stmt)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(body: BookingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    offering = db.scalar(
        select(CentreTest).where(CentreTest.centre_id == body.centre_id, CentreTest.test_id == body.test_id)
    )
    if not offering:
        raise HTTPException(404, "This centre does not offer the requested test")
    booking = Booking(
        user_id=user.id,
        centre_id=body.centre_id,
        test_id=body.test_id,
        appointment_at=body.appointment_at,
        amount=offering.price,  # server-side price; never trust the client for money
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/", response_model=list[BookingOut])
def list_my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Booking).where(Booking.user_id == user.id).order_by(Booking.id.desc())).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _own_booking(db, booking_id, user)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = _own_booking(db, booking_id, user, lock=True)
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(409, "Booking is already cancelled")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking
