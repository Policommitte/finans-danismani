"""Kimlik dogrulama uclari.

`user_id` hicbir zaman URL veya gövde ile TASINMAZ; token'dan cozulur
(mimari v4 bolum 10.2). Bu yuzden `/me` deseni kullanilir.
"""

import re

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


#: TCKN/NVI dogrulamasi kaldirildiktan sonra kayit formu ad/soyad artik
#: TOPLAMAZ (bkz. RegisterRequest) - ama `users.first_name`/`last_name`
#: DB'de NOT NULL. Bu yuzden e-postanin yerel kismindan makul bir isim
#: turetilir; kullanici isterse sonradan Profil ekranindan degistirebilir.
def _isim_turet(email: str) -> tuple[str, str]:
    yerel_kisim = email.split("@", 1)[0]
    parcalar = [p.capitalize() for p in re.split(r"[._-]+", yerel_kisim) if p]
    if not parcalar:
        return "Kullanıcı", ""
    if len(parcalar) == 1:
        return parcalar[0], ""
    return parcalar[0], " ".join(parcalar[1:])


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        risk_tolerance=user.get("risk_tolerance"),
        monthly_income=float(user["monthly_income"]) if user.get("monthly_income") else None,
        onboarding_completed=user.get("onboarding_completed", True),
        has_seen_tour=user.get("has_seen_tour", True),
        role=user.get("role", "customer"),
        tckn_last4=user.get("tckn_last4"),
        birth_date=user.get("birth_date"),
        phone_number=user.get("phone_number"),
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

    TCKN/NVI dogrulamali eski akis KALDIRILDI - kayit artik sadece e-posta +
    sifre ister. Frontend'deki "banka hesabi baglama" ekrani tamamen
    SIMULASYONDUR (gercek bir banka API'sine baglanmaz); orada girilen
    `account_number` dogrulanmadan bilgi amacli saklanir.

    `onboarding_completed=false` ve `has_seen_tour=false` ile baslar -
    AppShell bir sonraki yuklemede zorunlu onboarding akisini (anket ->
    sepet) acar, onboarding bitince de urun turunu (ProductTour) otomatik
    baslatir.
    """
    repo = get_user_repository()
    if await repo.get_by_email(payload.email) is not None:
        raise ConflictError("Bu e-posta zaten kayitli.")

    first_name, last_name = _isim_turet(payload.email)

    user = await repo.create(
        first_name=first_name,
        last_name=last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_number=payload.account_number,
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


@router.post("/tour-seen", response_model=UserResponse)
async def tour_seen(user: CurrentUser) -> UserResponse:
    """Urun turu (ProductTour) kapandiginda cagrilir - bitirilsin ya da
    gecilsin (ya da Escape ile kapatilsin) fark etmez, hepsi ayni `onClose`
    olayina cikar (bkz. frontend AppShell.tsx).

    `has_seen_tour`'u kalici olarak true yapar; bu sayede tur bir sonraki
    girişte bir daha otomatik acilmaz (bkz. UserResponse.has_seen_tour).
    """
    updated = await get_user_repository().mark_tour_seen(user["id"])
    return _user_response(updated)
