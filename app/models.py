import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON, text, Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Centre(Base):
    __tablename__ = "centres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(255), index=True)

    offerings: Mapped[list["CentreTest"]] = relationship(
        back_populates="centre", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (UniqueConstraint("name", "location", name="uq_centre_name_location"),)


class DiagnosticTest(Base):
    """Catalogue entry (e.g. 'CBC'). Price lives on CentreTest because it varies per centre."""

    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CentreTest(Base):
    __tablename__ = "centre_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    centre_id: Mapped[int] = mapped_column(ForeignKey("centres.id", ondelete="CASCADE"))
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    centre: Mapped[Centre] = relationship(back_populates="offerings")
    test: Mapped[DiagnosticTest] = relationship(lazy="joined")

    __table_args__ = (UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    centre_id: Mapped[int] = mapped_column(ForeignKey("centres.id"))
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Price snapshot: later price changes must not alter existing bookings.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, native_enum=False, length=20), default=BookingStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    centre: Mapped[Centre] = relationship(lazy="joined")
    test: Mapped[DiagnosticTest] = relationship(lazy="joined")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="booking", order_by="Payment.id", lazy="selectin"
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20), default=PaymentStatus.PENDING
    )
    # Identifier the "provider" knows this payment by; webhooks reference it.
    provider_reference: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    booking: Mapped[Booking] = relationship(back_populates="payments")


class WebhookEvent(Base):
    """One row per provider event. The UNIQUE event_id is the idempotency guard."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True)
    provider_reference: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# At most one in-flight payment per booking, enforced by the database itself.
Index(
    "uq_one_pending_payment_per_booking",
    Payment.booking_id,
    unique=True,
    postgresql_where=text("status = 'PENDING'"),
    sqlite_where=text("status = 'PENDING'"),
)
# At most one successful payment per booking (no double charge).
Index(
    "uq_one_success_payment_per_booking",
    Payment.booking_id,
    unique=True,
    postgresql_where=text("status = 'SUCCESS'"),
    sqlite_where=text("status = 'SUCCESS'"),
)
