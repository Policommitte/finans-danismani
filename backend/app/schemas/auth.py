"""Kimlik dogrulama sozlesmeleri."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Kullanici e-postasi", examples=["mehmet@example.com"])
    password: str = Field(min_length=1, description="Sifre", examples=["demo1234"])


class RegisterRequest(BaseModel):
    """TCKN/NVI dogrulamali eski akis kaldirildi - kayit artik sadece
    e-posta + sifre ister. `account_number`, "banka hesabi baglama"
    ekranindaki SIMULASYON adiminda girilir - gercek bir banka API'sine
    baglanilmaz, DOGRULANMAZ, yalnizca bilgi amacli saklanir."""

    email: EmailStr = Field(description="Kullanici e-postasi")
    password: str = Field(min_length=8, description="Sifre (en az 8 karakter)")
    account_number: str | None = Field(
        default=None,
        max_length=9,
        description="Banka hesabi baglama simulasyonunda girilen hesap numarasi "
        "(dogrulanmaz, bilgi amaclidir)",
        examples=["123456789"],
    )


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
        description="False ise AppShell zorunlu onboarding akisini (anket -> sepet) acar."
    )
    has_seen_tour: bool = Field(
        description="False ise AppShell urun turunu (ProductTour) otomatik acar - "
        "yalnizca onboarding tamamlandiktan sonra, ilk kayitta bir kez."
    )
    role: str = Field(default="customer", description="customer | advisor")
    tckn_last4: str | None = Field(
        default=None, description="TC Kimlik No'nun son 4 hanesi - tam numara HICBIR yanitta donmez"
    )
    birth_date: date | None = Field(default=None)
    phone_number: str | None = Field(default=None)
