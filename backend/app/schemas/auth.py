"""Kimlik dogrulama sozlesmeleri."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Kullanici e-postasi", examples=["mehmet@example.com"])
    password: str = Field(min_length=1, description="Sifre", examples=["demo1234"])


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Kullanici e-postasi")
    password: str = Field(min_length=8, description="Sifre (en az 8 karakter)")
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    tckn: str = Field(
        pattern=r"^\d{11}$",
        description="TC Kimlik Numarasi (11 haneli) - NVI ile dogrulanir, DUZ METIN saklanmaz",
        examples=["10000000146"],
    )
    birth_date: date = Field(
        description="Dogum tarihi - NVI dogrulamasinda yalnizca yili kullanilir"
    )
    phone_number: str = Field(min_length=10, max_length=20, examples=["05551234567"])


class OnboardingCompleteRequest(BaseModel):
    """Onboarding akisinin son adimi: risk anketi sonucunu kalici hale getirir."""

    risk_tolerance: Literal["LOW", "MEDIUM", "HIGH"]


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT erisim token'i")
    token_type: str = Field(default="bearer", description="Authorization header seması")
    expires_in: int = Field(description="Token'in gecerlilik suresi (saniye)")


class UserResponse(BaseModel):
    """`GET /api/auth/me` - AppShell'in kullandigi profil."""

    id: int
    first_name: str
    last_name: str
    email: str
    risk_tolerance: str | None = Field(default=None, description="LOW | MEDIUM | HIGH")
    monthly_income: float | None = Field(default=None, description="Aylik gelir (TRY)")
    onboarding_completed: bool = Field(
        description="False ise AppShell zorunlu onboarding akisini (anket -> sepet -> tur) acar."
    )
    role: str = Field(default="customer", description="customer | advisor")
    tckn_last4: str | None = Field(
        default=None, description="TC Kimlik No'nun son 4 hanesi - tam numara HICBIR yanitta donmez"
    )
    birth_date: date | None = Field(default=None)
    phone_number: str | None = Field(default=None)
