"""Sans Yatirimda oyunu API sozlesmeleri.

Rakip oyuncu simulasyonu (isim/skor/yuzde) icin hicbir alan YOK - "kac kisi
yariste" / "%X dogru bildi" gibi gorunumler frontend'de KALMAYA DEVAM EDER,
bu sema yalnizca kullanicinin KENDI katilimini/cuzdanini tasir (bkz.
app/repositories/base.py::ContestRepository).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LocalizedText(BaseModel):
    tr: str
    en: str


class ContestState(BaseModel):
    """`GET /api/contest/today` - ekranin hangi asamayi gosterecegine karar
    vermesi icin gereken her sey (kayit / sozlesme / zaten katildi mi)."""

    contest_id: int
    contest_date: str
    starts_at: str
    capacity_total: int
    prize_pool_points: int
    question_count: int
    participant_count: int
    has_agreement: bool
    already_participated_today: bool


class ContestTopic(BaseModel):
    id: int
    title: LocalizedText
    body: LocalizedText


class ContestQuestion(BaseModel):
    """Yarisma SIRASINDA istemciye gonderilen soru - dogru sik / aciklama
    BILEREK YOK (bkz. `submit_answer`'in donduregu `AnswerResult`)."""

    contest_question_id: int
    sort_order: int
    text: LocalizedText
    options: list[LocalizedText]
    timer_seconds: int
    difficulty: str


class ParticipationStart(BaseModel):
    participation_id: int
    questions: list[ContestQuestion]


class AnswerRequest(BaseModel):
    contest_question_id: int
    selected_index: int | None = Field(default=None, ge=0, le=3)
    elapsed_seconds: float = Field(ge=0)
    #: "Cift puan" jokeri bu soru icin aktif miydi - fiyati zaten satin alma
    #: aninda dusuldu (bkz. POWERUP_CATALOG), burada yalnizca puan ETKISI
    #: uygulanir. Istemci "aktif" der ama gercekten sahip mi kontrolu YOK -
    #: joker sahipligi zaten satin alma anindan itibaren gercek, kotuye
    #: kullanimin ust siniri bir soruda en fazla puanin 2 katiydi.
    double_points_active: bool = False


class FiftyFiftyResult(BaseModel):
    """İki YANLIŞ şıkkın index'leri - hangisinin dogru oldugu hala
    soylenmiyor, sadece elenecek 2 tanesi (bkz. `services/contest.py::fifty_fifty`)."""

    removed_indices: list[int]


class AnswerResult(BaseModel):
    """Cevap kaydedildikten SONRA aciklanir - dogru sik ve egitim notu artik
    guvenle donebilir (soru zaten cevaplandi)."""

    is_correct: bool
    points_earned: int
    correct_index: int
    education_note: LocalizedText


class FinishRequest(BaseModel):
    """`rivals_at_end`: frontend'in o oturumda BİR KEZ ürettiği simüle
    rakip/kazanan sayısı (bkz. frontend `pickTargetWinners`, 100-500 arası).

    Odul havuzunu BOLEN sayi burasidir - gercek katilimci sayisi DEGIL.
    Boyle olmasi BILINCLI: "kac kisi yariste/kazandi" zaten frontend'de
    tamamen simule edilen, gercek rakip verisi tasimayan bir gorunum
    (bkz. ContestRepository docstring'i); az sayida gercek test kullanicisi
    varken gercek sayiyi bolen yapmak odulu (havuz/1 gibi) gercekci olmayan
    bicimde sisirirdi. Sinir (100-500) client'in bunu 1'e cekip havuzun
    TAMAMINI kendine yazdirmasini engeller.
    """

    rivals_at_end: int = Field(ge=100, le=500)


class FinishResult(BaseModel):
    won: bool
    final_score: int
    correct_count: int
    reached_question: int
    eliminated_at_question: int | None
    payout_points: int
    #: Payout hesabinda bolen olarak KULLANILAN sayi - istemcinin gonderdigi
    #: simule deger, aynen geri doner (TEK kaynak budur, bkz. FinishRequest).
    rivals_at_end: int


class WalletSummary(BaseModel):
    points_balance: int
    powerups: dict[str, int]
    badges: list[str]


class ContestHistoryRow(BaseModel):
    contest_date: str
    won: bool
    final_score: int
    eliminated_at_question: int | None
    points_earned: int


class PowerupPurchaseRequest(BaseModel):
    kind: str


class DonationPurchaseRequest(BaseModel):
    donation_key: str


class LeaderboardEntry(BaseModel):
    rank: int
    label: str
    score: int
