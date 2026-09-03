"""Sans Yatirimda oyunu uclari."""

from fastapi import APIRouter, Query

from app.auth.deps import CurrentUser
from app.schemas.contest import (
    AnswerRequest,
    AnswerResult,
    ContestHistoryRow,
    ContestState,
    ContestTopic,
    DonationPurchaseRequest,
    FiftyFiftyResult,
    FinishRequest,
    FinishResult,
    LeaderboardEntry,
    ParticipationStart,
    PowerupPurchaseRequest,
    WalletSummary,
)
from app.services import contest as service

router = APIRouter(prefix="/api/contest", tags=["contest"])


@router.get("/today", response_model=ContestState)
async def today(user: CurrentUser) -> ContestState:
    """Bugunku yarisma durumu - ekran hangi asamayi (kayit/kural/yarisma
    yapildi) gosterecegine buna gore karar verir."""
    return await service.get_contest_state(user["id"])


@router.post("/agreement", status_code=204)
async def accept_agreement(user: CurrentUser) -> None:
    await service.accept_agreement(user["id"])


@router.post("/reset", status_code=204)
async def reset_today(user: CurrentUser) -> None:
    """DEMO/GELISTIRME icin: bugunku katilimi siler, kullanici tekrar
    kaydolabilir. Uretimde 422 doner (bkz. services/contest.py)."""
    await service.reset_todays_participation(user["id"])


@router.post("/shop/reset", status_code=204)
async def reset_shop(user: CurrentUser) -> None:
    """DEMO/GELISTIRME icin: tum magaza satin almalarini (joker + bagis)
    siler, harcanan puanlar iade edilmis gibi bakiyeye geri doner. Uretimde
    422 doner (bkz. services/contest.py)."""
    await service.reset_shop_purchases(user["id"])


@router.get("/{contest_id}/topics", response_model=list[ContestTopic])
async def contest_topics(contest_id: int, user: CurrentUser) -> list[ContestTopic]:
    """Calisma notu ekrani icin o yarismaya bagli konular."""
    return await service.get_contest_topics(contest_id)


@router.post("/participations", response_model=ParticipationStart, status_code=201)
async def start_participation(user: CurrentUser) -> ParticipationStart:
    """Bugunku yarismaya kayit olur, soru listesini (dogru cevap OLMADAN)
    doner. Gunde bir kez cagrilabilir - ikinci denemede 422 doner."""
    return await service.start_participation(user["id"])


@router.post("/participations/{participation_id}/answers", response_model=AnswerResult)
async def submit_answer(
    participation_id: int, payload: AnswerRequest, user: CurrentUser
) -> AnswerResult:
    """Bir soruya cevap gonderir; dogruluk ve puan SUNUCUDA hesaplanir,
    istemciden gelen hicbir deger guvenilmez."""
    return await service.submit_answer(user["id"], participation_id, payload)


@router.post(
    "/participations/{participation_id}/questions/{contest_question_id}/fifty-fifty",
    response_model=FiftyFiftyResult,
)
async def fifty_fifty(
    participation_id: int, contest_question_id: int, user: CurrentUser
) -> FiftyFiftyResult:
    """İki yanlış şıkkın index'lerini döner - hangisinin doğru olduğu
    söylenmez, sadece elenecek 2 tanesi (bkz. `services/contest.py::fifty_fifty`)."""
    return await service.fifty_fifty(user["id"], participation_id, contest_question_id)


@router.post("/participations/{participation_id}/finish", response_model=FinishResult)
async def finish_participation(
    participation_id: int, payload: FinishRequest, user: CurrentUser
) -> FinishResult:
    """Yarismayi kapatir; final skor kayitli cevaplardan toplanir (istemciye
    guvenilmez), kazanildiysa odul BURADA yazilir. `payload.rivals_at_end`
    havuzu bolen sayidir - bkz. FinishRequest docstring'i (BILEREK gercek
    katilimci sayisi degil, frontend'in simule ettigi deger)."""
    return await service.finish_participation(user["id"], participation_id, payload.rivals_at_end)


@router.get("/wallet", response_model=WalletSummary)
async def wallet(user: CurrentUser) -> WalletSummary:
    return await service.get_wallet(user["id"])


@router.get("/wallet/history", response_model=list[ContestHistoryRow])
async def wallet_history(
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ContestHistoryRow]:
    return await service.get_history(user["id"], limit=limit)


@router.post("/shop/powerup", response_model=WalletSummary)
async def buy_powerup(payload: PowerupPurchaseRequest, user: CurrentUser) -> WalletSummary:
    """Fiyat istemciden ALINMAZ - `services/contest.py::POWERUP_CATALOG`
    tek dogru kaynaktir."""
    return await service.buy_powerup(user["id"], payload.kind)


@router.post("/powerups/{kind}/consume", response_model=WalletSummary)
async def consume_powerup(kind: str, user: CurrentUser) -> WalletSummary:
    """Bir joker yarisma icinde KULLANILDIGINDA cagrilir - envanteri
    gercekten dusurur, satin alma ucuyla KARISTIRILMAMALI."""
    return await service.use_powerup(user["id"], kind)


@router.post("/shop/donation", response_model=WalletSummary)
async def buy_donation(payload: DonationPurchaseRequest, user: CurrentUser) -> WalletSummary:
    return await service.buy_donation(user["id"], payload.donation_key)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    user: CurrentUser,
    period: str = Query(default="tumzamanlar", pattern="^(gunluk|haftalik|tumzamanlar)$"),
) -> list[LeaderboardEntry]:
    return await service.get_leaderboard(period)
