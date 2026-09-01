"""Sans Yatirimda oyunu is mantigi.

`repositories/base.py::ContestRepository` yalnizca okur/yazar; puanlama
formulu, odul dagilimi ve magaza fiyat katalogu BURADADIR (Lead motorundaki
"kural degerlendirmesi servis katmaninda" ilkesiyle ayni).

Rakip oyuncu simulasyonu (isim/skor/yuzde) burada da YOK - "kac kisi
yariste" gibi gorunumler frontend'de kalmaya devam eder. Tek istisna:
`FinishResult.rivals_at_end` - odul hesabinda bolen olarak kullanilan
GERCEK katilimci sayisi, boylece frontend ileride bunu gosterirse
odul miktariyla ÇELIŞMEZ (bkz. GOREV-kazanan-tutarliligi.md).
"""

from __future__ import annotations

import random

from app.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.repositories.deps import get_contest_repository
from app.schemas.contest import (
    AnswerRequest,
    AnswerResult,
    ContestHistoryRow,
    ContestQuestion,
    ContestState,
    ContestTopic,
    FiftyFiftyResult,
    FinishResult,
    LeaderboardEntry,
    LocalizedText,
    ParticipationStart,
    WalletSummary,
)

#: Frontend'deki POWERUP_SHOP ile AYNI fiyatlar (frontend/src/models/oyun.ts).
#: Fiyat istemciden ASLA alinmaz - burasi tek dogru kaynak.
POWERUP_CATALOG: dict[str, int] = {
    "doublePoints": 1000,
    "fiftyFifty": 2000,
}

#: Frontend'deki DONATIONS ile AYNI (fiyat + rozet etiketi).
DONATION_CATALOG: dict[str, dict] = {
    "fidan": {"price": 1500, "badge": "Fidan Dostu"},
    "egitim": {"price": 3000, "badge": "Eğitim Gönüllüsü"},
}


def _score_for(elapsed_seconds: float, limit_seconds: int) -> int:
    """Frontend'deki `scoreFor` ile BIREBIR AYNI formul - iki taraf da ayni
    dogru cevaba ayni puani vermeli."""
    ratio = max(0.0, (limit_seconds - elapsed_seconds) / limit_seconds)
    return round(100 + 100 * ratio)


def _localized(row: dict, prefix: str) -> LocalizedText:
    return LocalizedText(tr=row[f"{prefix}_tr"], en=row[f"{prefix}_en"])


async def _active_contest_or_404() -> dict:
    contest = await get_contest_repository().get_active_contest()
    if contest is None:
        raise NotFoundError("Bugun icin acik bir yarisma yok.")
    return contest


async def _own_participation_or_403(user_id: int, participation_id: int) -> dict:
    participation = await get_contest_repository().get_participation(participation_id)
    if participation is None:
        raise NotFoundError("Katilim bulunamadi.")
    if participation["user_id"] != user_id:
        raise BusinessRuleError("Bu katilim sana ait degil.")
    return participation


async def get_contest_state(user_id: int) -> ContestState:
    repo = get_contest_repository()
    contest = await _active_contest_or_404()
    participant_count = await repo.count_participants(contest["id"])
    has_agreement = await repo.has_agreement(user_id)

    bugun = str(contest["contest_date"])
    already = any(
        str(p["contest_date"]) == bugun
        for p in await repo.list_participations(user_id, limit=5)
    )

    return ContestState(
        contest_id=contest["id"],
        contest_date=bugun,
        starts_at=str(contest["starts_at"]),
        capacity_total=contest["capacity_total"],
        prize_pool_points=contest["prize_pool_points"],
        question_count=contest["question_count"],
        participant_count=participant_count,
        has_agreement=has_agreement,
        already_participated_today=already,
    )


async def accept_agreement(user_id: int) -> None:
    await get_contest_repository().create_agreement(user_id)


async def reset_todays_participation(user_id: int) -> None:
    """DEMO/GELISTIRME icin: bugunku katilim hakkini geri verir.

    Uretimde KAPALI - `app_env == "production"` iken 422 doner. Bu tek
    kontrol repository katmaninda DEGIL burada, servis is kurali oldugu icin
    (bkz. dosya basindaki "kural degerlendirmesi servis katmaninda" ilkesi).
    """
    if settings.app_env == "production":
        raise BusinessRuleError("Bu islem yalnizca gelistirme ortaminda kullanilabilir.")
    await get_contest_repository().reset_todays_participation(user_id)


async def get_contest_topics(contest_id: int) -> list[ContestTopic]:
    rows = await get_contest_repository().get_contest_topics(contest_id)
    return [
        ContestTopic(id=r["id"], title=_localized(r, "title"), body=_localized(r, "body"))
        for r in rows
    ]


async def start_participation(user_id: int) -> ParticipationStart:
    repo = get_contest_repository()
    contest = await _active_contest_or_404()

    if not await repo.has_agreement(user_id):
        raise BusinessRuleError("Once yarisma kurallarini kabul etmelisin.")

    participant_count = await repo.count_participants(contest["id"])
    if participant_count >= contest["capacity_total"]:
        raise BusinessRuleError("Bu aksamki yarisma kontenjani doldu.")

    # `register_participation` gunde-bir-katilim kuralini KENDI icinde
    # (UNIQUE kisiti / bellek ici esdegeri) uygular - burada tekrar
    # kontrol edilmez, tek dogru kaynak orasi.
    participation = await repo.register_participation(contest["id"], user_id)

    questions_raw = await repo.get_contest_questions(contest["id"])
    questions = [
        ContestQuestion(
            contest_question_id=q["contest_question_id"],
            sort_order=q["sort_order"],
            text=_localized(q, "text"),
            options=[LocalizedText(**opt) for opt in q["options"]],
            timer_seconds=q["timer_seconds"],
            difficulty=q["difficulty"],
        )
        for q in questions_raw
    ]
    return ParticipationStart(participation_id=participation["id"], questions=questions)


async def _question_in_contest_or_404(contest_id: int, contest_question_id: int) -> dict:
    questions = await get_contest_repository().get_contest_questions(contest_id)
    question = next((q for q in questions if q["contest_question_id"] == contest_question_id), None)
    if question is None:
        raise NotFoundError("Soru bu yarismaya ait degil.")
    return question


async def submit_answer(user_id: int, participation_id: int, payload: AnswerRequest) -> AnswerResult:
    repo = get_contest_repository()
    participation = await _own_participation_or_403(user_id, participation_id)
    question = await _question_in_contest_or_404(participation["contest_id"], payload.contest_question_id)

    is_correct = payload.selected_index is not None and payload.selected_index == question["correct_index"]
    base_points = _score_for(payload.elapsed_seconds, question["timer_seconds"]) if is_correct else 0
    points_earned = base_points * 2 if (is_correct and payload.double_points_active) else base_points

    await repo.submit_answer(
        participation_id=participation_id,
        contest_question_id=payload.contest_question_id,
        selected_index=payload.selected_index,
        is_correct=is_correct,
        points_earned=points_earned,
        elapsed_seconds=payload.elapsed_seconds,
    )

    return AnswerResult(
        is_correct=is_correct,
        points_earned=points_earned,
        correct_index=question["correct_index"],
        education_note=_localized(question, "education_note"),
    )


async def fifty_fifty(user_id: int, participation_id: int, contest_question_id: int) -> FiftyFiftyResult:
    """İki YANLIŞ şıkkın index'lerini doner - dogru şık ASLA elenmez, ama
    HANGİSİNİN doğru olduğu da söylenmez (kalan 2 şık arasında belirsizlik
    korunur, `submit_answer` cevaplanana kadar)."""
    participation = await _own_participation_or_403(user_id, participation_id)
    question = await _question_in_contest_or_404(participation["contest_id"], contest_question_id)

    wrong_indices = [i for i in range(4) if i != question["correct_index"]]
    removed = random.sample(wrong_indices, 2)
    return FiftyFiftyResult(removed_indices=removed)


async def finish_participation(
    user_id: int, participation_id: int, simulated_rivals_at_end: int
) -> FinishResult:
    repo = get_contest_repository()
    participation = await _own_participation_or_403(user_id, participation_id)

    contest = await _active_contest_or_404()
    total_questions = contest["question_count"]

    answers = await repo.list_answers(participation_id)
    final_score = sum(a["points_earned"] for a in answers)
    correct_count = sum(1 for a in answers if a["is_correct"])
    reached_question = len(answers)

    first_wrong = next((i for i, a in enumerate(answers, start=1) if not a["is_correct"]), None)
    won = first_wrong is None and reached_question == total_questions
    eliminated_at_question = None if won else first_wrong

    await repo.finalize_participation(
        participation_id=participation_id,
        won=won,
        final_score=final_score,
        eliminated_at_question=eliminated_at_question,
    )

    # Havuzu bolen sayi BILEREK GERCEK katilimci sayisi degil, istemcinin
    # gonderdigi simule deger (bkz. schemas/contest.py::FinishRequest) - az
    # sayida gercek test kullanicisi varken gercek sayi odulu (havuz/1 gibi)
    # gercekci olmayan bicimde sisirirdi. Odul yine de GERCEK cuzdana yazilir.
    rivals_at_end = simulated_rivals_at_end
    payout_points = 0
    if won:
        payout_points = max(1, round(contest["prize_pool_points"] / max(1, rivals_at_end)))
        await repo.create_payout(participation_id, payout_points)

    return FinishResult(
        won=won,
        final_score=final_score,
        correct_count=correct_count,
        reached_question=reached_question,
        eliminated_at_question=eliminated_at_question,
        payout_points=payout_points,
        rivals_at_end=rivals_at_end,
    )


async def get_wallet(user_id: int) -> WalletSummary:
    repo = get_contest_repository()
    balance = await repo.get_points_balance(user_id)
    powerups = await repo.get_user_powerups(user_id)
    badges = await repo.get_user_badges(user_id)
    return WalletSummary(points_balance=balance, powerups=powerups, badges=badges)


async def get_history(user_id: int, limit: int = 20) -> list[ContestHistoryRow]:
    rows = await get_contest_repository().list_participations(user_id, limit=limit)
    return [
        ContestHistoryRow(
            contest_date=str(r["contest_date"]),
            won=r["won"],
            final_score=r["final_score"],
            eliminated_at_question=r["eliminated_at_question"],
            points_earned=r["points_awarded"],
        )
        for r in rows
    ]


async def buy_powerup(user_id: int, kind: str) -> WalletSummary:
    price = POWERUP_CATALOG.get(kind)
    if price is None:
        raise NotFoundError(f"'{kind}' adinda bir joker yok.")

    repo = get_contest_repository()
    balance = await repo.get_points_balance(user_id)
    if balance < price:
        raise BusinessRuleError("Bakiyen bu jokeri almaya yetmiyor.")

    await repo.record_powerup_purchase(user_id, kind, price)
    return await get_wallet(user_id)


async def use_powerup(user_id: int, kind: str) -> WalletSummary:
    """Bir joker yarisma icinde KULLANILDIGINDA cagrilir (satin alma DEGIL).

    Envanteri gercekten dusurur ki sayfa yenilense ya da baska bir cihazdan
    girilse bile kullanilan joker geri gelmesin.
    """
    if kind not in POWERUP_CATALOG:
        raise NotFoundError(f"'{kind}' adinda bir joker yok.")

    repo = get_contest_repository()
    ok = await repo.consume_powerup(user_id, kind)
    if not ok:
        raise BusinessRuleError("Bu jokerden elinde yok.")
    return await get_wallet(user_id)


async def buy_donation(user_id: int, donation_key: str) -> WalletSummary:
    entry = DONATION_CATALOG.get(donation_key)
    if entry is None:
        raise NotFoundError(f"'{donation_key}' adinda bir bagis yok.")

    repo = get_contest_repository()
    existing_badges = await repo.get_user_badges(user_id)
    if entry["badge"] in existing_badges:
        raise BusinessRuleError("Bu rozeti zaten kazandin.")

    balance = await repo.get_points_balance(user_id)
    if balance < entry["price"]:
        raise BusinessRuleError("Bakiyen bu bagisi yapmaya yetmiyor.")

    await repo.record_donation_purchase(user_id, donation_key, entry["badge"], entry["price"])
    return await get_wallet(user_id)


async def get_leaderboard(period: str) -> list[LeaderboardEntry]:
    rows = await get_contest_repository().get_leaderboard(period)
    return [LeaderboardEntry(**row) for row in rows]
