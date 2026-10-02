import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


# ---------- auth ----------
class SignupIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("password must contain letters and digits")
        return v

    @field_validator("email")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.lower()


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    is_admin: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- catalogue ----------
class DiagnosticTestIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class DiagnosticTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


class CentreTestIn(BaseModel):
    test_id: int
    price: Money


class CentreTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    test: DiagnosticTestOut
    price: Decimal


class CentreIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=255)
    tests: list[CentreTestIn] = []


class CentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str
    offerings: list[CentreTestOut]


# ---------- bookings ----------
class BookingIn(BaseModel):
    centre_id: int
    test_id: int
    appointment_at: datetime

    @field_validator("appointment_at")
    @classmethod
    def must_be_future_and_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("appointment_at must include a timezone offset, e.g. 2030-01-01T10:00:00+05:30")
        if v <= datetime.now(timezone.utc):
            raise ValueError("appointment_at must be in the future")
        return v


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    booking_id: int
    amount: Decimal
    status: str
    provider_reference: str
    created_at: datetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    centre_id: int
    test_id: int
    appointment_at: datetime
    amount: Decimal
    status: str
    created_at: datetime
    payments: list[PaymentOut] = []


# ---------- payments ----------
class PaymentIn(BaseModel):
    booking_id: int
    # Test hook so reviewers can force an outcome. PENDING mimics an async provider
    # that will report the result later through the webhook.
    outcome: Literal["SUCCESS", "FAILED", "PENDING"] | None = None


class WebhookIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    provider_reference: str = Field(min_length=1, max_length=64)
    status: Literal["SUCCESS", "FAILED"]
