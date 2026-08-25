"""Kimlik dogrulama sozlesmeleri."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Kullanici e-postasi", examples=["mehmet@example.com"])
    password: str = Field(min_length=1, description="Sifre", examples=["demo1234"])


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
    role: str = Field(default="customer", description="customer | advisor")
