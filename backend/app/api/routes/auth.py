"""Kimlik dogrulama uclari.

`user_id` hicbir zaman URL veya gövde ile TASINMAZ; token'dan cozulur
(mimari v4 bolum 10.2). Bu yuzden `/me` deseni kullanilir.
"""

from fastapi import APIRouter, status

from app.auth.deps import CurrentUser
from app.auth.security import TOKEN_TYPE, create_access_token, hash_password, verify_password
from app.config import settings
from app.core.errors import AuthenticationError, ConflictError
from app.repositories.deps import get_user_repository
from app.schemas.auth import (
    LoginRequest,
    OnboardingCompleteRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        risk_tolerance=user.get("risk_tolerance"),
        monthly_income=float(user["monthly_income"]) if user.get("monthly_income") else None,
        onboarding_completed=user.get("onboarding_completed", True),
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest) -> TokenResponse:
    """E-posta + sifre ile giris yapar.

    Kullanici bulunamadiginda da sifre yanlis oldugunda da AYNI mesaj doner:
    farkli mesaj vermek hangi e-postalarin kayitli oldugunu sizdirir.
    """
    user = await get_user_repository().get_by_email(payload.email)

    if user is None or not verify_password(payload.password, user.get("password_hash", "")):
        raise AuthenticationError("E-posta veya sifre hatali.")

    return TokenResponse(
        access_token=create_access_token(user["id"]),
        token_type=TOKEN_TYPE,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> TokenResponse:
    """Yeni kullanici olusturur ve dogrudan giris yapar (otomatik login).

    `onboarding_completed=false` ile baslar - AppShell bir sonraki yuklemede
    zorunlu onboarding akisini (anket -> sepet -> tur) acar.
    """
    repo = get_user_repository()
    if await repo.get_by_email(payload.email) is not None:
        raise ConflictError("Bu e-posta zaten kayitli.")

    user = await repo.create(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    return TokenResponse(
        access_token=create_access_token(user["id"]),
        token_type=TOKEN_TYPE,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    """Oturum acmis kullanicinin profili (AppShell)."""
    return _user_response(user)


@router.post("/onboarding/complete", response_model=UserResponse)
async def complete_onboarding(
    payload: OnboardingCompleteRequest, user: CurrentUser
) -> UserResponse:
    """Onboarding akisinin tek persistence noktasi.

    Anket sonucunu `risk_tolerance`'a yazar ve `onboarding_completed`'i tek
    islemde true yapar - boylece akis bir daha hic gosterilmez.
    """
    updated = await get_user_repository().complete_onboarding(user["id"], payload.risk_tolerance)
    return _user_response(updated)
