"use client";

import { useEffect, useState } from "react";
import Card from "../../components/ui/Card";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { useLanguage } from "../../contexts/LanguageContext";
import { RegisterScreen } from "../../components/oyun/RegisterScreen";
import { RulesModal } from "../../components/oyun/RulesModal";
import { WaitingScreen } from "../../components/oyun/WaitingScreen";
import { CheatSheetScreen, WAITING_TOPIC_ICONS, WAITING_TOPIC_COLORS } from "../../components/oyun/CheatSheetScreen";
import { FlipCard } from "../../components/oyun/FlipCard";
import { QuizScreen } from "../../components/oyun/QuizScreen";
import { EliminatedScreen } from "../../components/oyun/EliminatedScreen";
import { WinnerScreen } from "../../components/oyun/WinnerScreen";
import type { Powerups } from "../../hooks/useQuiz";
import { useGameFlow, type GameScreen, type GameTab } from "../../hooks/useGameFlow";
import { CampaignsTab } from "../../components/oyun/CampaignsTab";
import { WAITING_NOTES, CONFIG, type GameResult, type PowerupKind, type DonationItem } from "../../models/oyun";
import { WalletTab } from "../../components/oyun/WalletTab";
import { useSoundEffects } from "../../hooks/useSoundEffects";
import { IntroSidebar } from "../../components/oyun/IntroSidebar";
import { LeaderboardPanel } from "../../components/oyun/LeaderboardPanel";
import { setGameFocus } from "../../components/layout/gameFocusEvents";
import { useContestState } from "../../hooks/useContestState";
import { useContestWallet } from "../../hooks/useContestWallet";
import {
  acceptContestAgreement,
  consumePowerupApi,
  resetContestToday,
  resetShopPurchases,
} from "../../services/contestService";

const TABS: { id: GameTab; label: { tr: string; en: string } }[] = [
  { id: "oyun", label: { tr: "Oyun", en: "Game" } },
  { id: "kampanyalar", label: { tr: "Mağaza", en: "Shop" } },
  { id: "puanlar", label: { tr: "Puanlar", en: "Points" } },
];

const SCREEN_LABELS: Record<GameScreen, { tr: string; en: string }> = {
  register: { tr: "Kayıt", en: "Registration" },
  waiting: { tr: "Bekleme", en: "Waiting" },
  cheatsheet: { tr: "Çalışma notu", en: "Study notes" },
  quiz: { tr: "Yarışma", en: "Contest" },
  eliminated: { tr: "Elendi", en: "Eliminated" },
  victory: { tr: "Kazandı", en: "Won" },
  closed: { tr: "Kayıt kapalı", en: "Registration closed" },
};

const PAGE_TEXT = {
  title: { tr: "Şans Yatırımda", en: "Şans Yatırımda" },
  subtitle: {
    tr: "Finans bilginle yarış, ödül havuzundan pay al.",
    en: "Compete with your finance knowledge, claim a share of the prize pool.",
  },
  activeScreen: { tr: "Aktif ekran", en: "Active screen" },
  score: { tr: "Skor", en: "Score" },
  correct: { tr: "Doğru", en: "Correct" },
  reached: { tr: "Ulaşılan soru", en: "Question reached" },
  questionsSummary: (count: number, seconds: number, pool: string) => ({
    tr: `${count} soru · her biri ${seconds} saniye · ${pool} bonus puan havuzu`,
    en: `${count} questions · ${seconds} seconds each · ${pool} bonus point pool`,
  }),
  devPanelTitle: { tr: "Ekran testi (sadece geliştirme ortamı)", en: "Screen test (development only)" },
  reset: { tr: "Sıfırla", en: "Reset" },
  resetToday: { tr: "Bugünkü katılımı sıfırla", en: "Reset today's entry" },
  resetTodayFailed: {
    tr: "Sıfırlanamadı (bu işlem sadece geliştirme ortamında çalışır).",
    en: "Couldn't reset (this only works in the development environment).",
  },
  resetShop: { tr: "Mağaza satın alımlarını sıfırla", en: "Reset shop purchases" },
  resetShopFailed: {
    tr: "Sıfırlanamadı (bu işlem sadece geliştirme ortamında çalışır).",
    en: "Couldn't reset (this only works in the development environment).",
  },
  muteOn: { tr: "Sesi kapat", en: "Mute sound" },
  muteOff: { tr: "Sesi aç", en: "Unmute sound" },
  leaveContest: { tr: "Yarışmadan ayrıl", en: "Leave contest" },
  leaveConfirm: {
    tr: "Yarışmadan ayrılırsan bu turda elenmiş sayılırsın. Emin misin?",
    en: "Leaving now counts as elimination for this round. Are you sure?",
  },
};

function SoundIcon({ muted }: { muted: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="3 9 3 15 8 15 13 20 13 4 8 9 3 9" fill="currentColor" stroke="none" />
      {muted ? (
        <>
          <line x1="16" y1="9" x2="21" y2="14" />
          <line x1="21" y1="9" x2="16" y2="14" />
        </>
      ) : (
        <path d="M16 8a5 5 0 0 1 0 8" />
      )}
    </svg>
  );
}

export default function YatirimOyunuPage() {
  const { language, toggleLanguage } = useLanguage();
  const { tab, goTab, screen, goScreen, isFocused } = useGameFlow();
  const { play, muted, toggleMute } = useSoundEffects();

  const [agreementSigned, setAgreementSigned] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [registered, setRegistered] = useState(false);

  const [registeredCount, setRegisteredCount] = useState(920);
  const [lastResult, setLastResult] = useState<GameResult | null>(null);

  // Bugünkü yarışma durumu (sözleşme onayı, bugün katıldı mı) — GERÇEK
  // kaynak backend'dir. Cüzdan/mağaza da aynı şekilde gerçek: bakiye, joker
  // envanteri, rozetler ve puan geçmişi TEK kaynaktan (bkz.
  // useContestWallet) gelir; yalnızca "kaç kişi yarışta" gibi rakip
  // simülasyonu (registeredCount) frontend'de sahte kalmaya devam eder.
  const contestState = useContestState();
  const wallet = useContestWallet();
  const powerups: Powerups = {
    doublePoints: wallet.powerups.doublePoints ?? 0,
    fiftyFifty: wallet.powerups.fiftyFifty ?? 0,
  };

  // "Gözüken" ve "gerçek" bakiye artık AYNI sayı: backend, kullanıcıya ilk
  // eriştiğinde "geçmiş günler" hikayesini gerçek katılım+ödül satırları
  // olarak tohumlar (bkz. backend `_gecmis_gunleri_tohumla`) - eskiden
  // yalnızca görüntü için ayrı bir sahte sabit vardı, artık gerçekten
  // harcanabilir tek bir bakiye kaynağı var.
  const displayedBalance = wallet.pointsBalance;

  // Sözleşmeyi zaten kabul etmişse (bugünden önce de olabilir) modalı bir
  // daha gösterme — gerçek durum yüklenince yerel bayrağı buna göre kurar.
  useEffect(() => {
    if (contestState.data?.has_agreement) {
      setAgreementSigned(true);
    }
  }, [contestState.data?.has_agreement]);

  // Yarışma sırasında (isFocused) üst başlık/sekmeler/dev paneli tamamen gizlenir.
  const inContest = isFocused && screen === "quiz";

  // Sadece gerçek yarışma (soru-cevap) ekranındayken AppShell'e haber ver.
  useEffect(() => {
    setGameFocus(screen === "quiz");
    return () => setGameFocus(false);
  }, [screen]);

  function spendPowerup(kind: keyof Powerups) {
    // İyimser: joker anında tükenmiş görünsün diye lokal state yok artık,
    // bir sonraki useContestWallet fetch'i gerçek adedi getirecek. Asıl
    // düşüş backend'de (envanteri gerçekten azaltır) — sayfa yenilense
    // kullanılan joker geri gelmesin diye.
    void consumePowerupApi(kind).then(() => wallet.refresh());
  }

  function buyPowerup(kind: PowerupKind, price: number) {
    if (displayedBalance < price) return;
    void wallet.buyPowerup(kind).then((ok) => {
      if (ok) {
        play("purchase");
      } else if (wallet.actionError) {
        // Iki sekme/istek yarisinca (race) bakiye burada guncel olmayabilir -
        // backend reddederse kullaniciya sessizce degil, mesajla haber verilir.
        window.alert(wallet.actionError);
      }
    });
  }

  function buyDonation(item: DonationItem) {
    if (displayedBalance < item.cost || wallet.badges.includes(item.badge.tr)) return;
    void wallet.buyDonation(item.id).then((ok) => {
      if (ok) {
        play("purchase");
      } else if (wallet.actionError) {
        window.alert(wallet.actionError);
      }
    });
  }

  function handleRegister() {
    if (!agreementSigned) {
      setRulesOpen(true);
      return;
    }
    setRegistered(true);
    play("register");
    goScreen("waiting");
  }

  function handleAcceptRules() {
    setAgreementSigned(true);
    setRulesOpen(false);
    setRegistered(true);
    play("register");
    goScreen("waiting");
    // İyimser: engellenmesi gereken tek yer start_participation (gerçek
    // katılım hakkını tüketen çağrı) — orası zaten sözleşmeyi sunucuda
    // kontrol eder, burada başarısız olsa da akış tıkanmaz.
    void acceptContestAgreement().catch(() => {});
  }

  function handleLeaveContest() {
    const ok = window.confirm(PAGE_TEXT.leaveConfirm[language]);
    if (!ok) return;
    // Yarışmaya kaydolduğun an (startParticipation) günlük hakkın backend'de
    // zaten tükenmiş olur - `contestState` yenilenmezse bu bilgi bayat kalır
    // ve "zaten katıldın" kapısı (çalışma notu kartlarıyla) yerine boş kayıt
    // ekranı görünür (bkz. Issue #65'teki aynı desen).
    void contestState.refresh();
    goScreen("register");
  }

  // DEMO/GELİŞTİRME: backend'deki günlük katılım hakkını siler ki aynı
  // hesapla arka arkaya sunum yapılabilsin. Backend üretimde bunu reddeder.
  async function handleResetToday() {
    try {
      await resetContestToday();
      setRegistered(false);
      setLastResult(null);
      await Promise.all([contestState.refresh(), wallet.refresh()]);
      goScreen("register");
    } catch (exc) {
      window.alert(exc instanceof Error ? exc.message : PAGE_TEXT.resetTodayFailed[language]);
    }
  }

  // DEMO/GELİŞTİRME: tüm mağaza satın almalarını (joker + bağış) siler,
  // harcanan puanlar iade edilmiş gibi bakiyeye geri döner.
  async function handleResetShop() {
    try {
      await resetShopPurchases();
      await wallet.refresh();
    } catch (exc) {
      window.alert(exc instanceof Error ? exc.message : PAGE_TEXT.resetShopFailed[language]);
    }
  }

  return (
    <div className={inContest ? "" : "space-y-6"}>
      <RulesModal open={rulesOpen} onAccept={handleAcceptRules} />

      {!inContest && (
        <div
          className="relative overflow-hidden rounded-2xl px-6 py-5 sm:px-8 sm:py-7"
          style={{
            background:
              "linear-gradient(135deg, var(--color-panel-dark) 0%, color-mix(in srgb, var(--color-panel-dark) 80%, var(--color-primary)) 100%)",
          }}
        >
          <div className="relative flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white sm:text-3xl">{PAGE_TEXT.title[language]}</h1>
              <p className="mt-1 text-sm" style={{ color: "var(--color-market-muted)" }}>
                {PAGE_TEXT.subtitle[language]}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <ThemeToggle className="border-white/10 bg-white/[0.06] text-white/80 hover:bg-white/10" />
              <button
                type="button"
                onClick={toggleLanguage}
                aria-label={language === "tr" ? "Dili İngilizce yap" : "Switch language to Turkish"}
                className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-white/[0.06] text-sm font-black text-white/80 transition hover:bg-white/10"
              >
                {language === "tr" ? "EN" : "TR"}
              </button>
              <button
                type="button"
                onClick={toggleMute}
                aria-label={muted ? PAGE_TEXT.muteOff[language] : PAGE_TEXT.muteOn[language]}
                aria-pressed={muted}
                title={muted ? PAGE_TEXT.muteOff[language] : PAGE_TEXT.muteOn[language]}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white/80 transition hover:bg-white/10 hover:text-white"
              >
                <SoundIcon muted={muted} />
              </button>
            </div>
          </div>
        </div>
      )}

      {!inContest && (
        <div
          className="flex gap-2 border-b pb-3"
          style={{ borderColor: "var(--color-border)" }}
          role="tablist"
        >
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => goTab(t.id)}
                className="rounded-lg px-4 py-2 text-sm font-semibold transition"
                style={
                  active
                    ? { background: "var(--color-primary)", color: "var(--color-on-primary)" }
                    : { color: "var(--color-muted)" }
                }
              >
                {t.label[language]}
              </button>
            );
          })}
        </div>
      )}

      {inContest && (
        <div className="mb-4 flex items-center justify-between">
          <ThemeToggle />
          <button
            type="button"
            onClick={handleLeaveContest}
            className="rounded-lg border px-4 py-2 text-xs font-semibold transition"
            style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)" }}
          >
            {PAGE_TEXT.leaveContest[language]}
          </button>
        </div>
      )}

      {tab === "oyun" && (
        <div className={inContest ? "" : "space-y-4"}>
          <div
            className={
              isFocused
                ? "mx-auto w-full max-w-4xl"
                : "grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_300px]"
            }
          >
            {!isFocused && (
              <div className="hidden lg:block">
                <IntroSidebar
                  registered={registered}
                  taken={registeredCount}
                  alreadyPlayedToday={contestState.data?.already_participated_today ?? false}
                />
              </div>
            )}

            <div className="min-w-0">
              {screen === "register" && contestState.data?.already_participated_today ? (
                <Card>
                  <div className="space-y-1 py-8 text-center">
                    <p className="app-heading text-lg font-semibold">
                      {language === "tr"
                        ? "Bugünkü katılım hakkını kullandın"
                        : "You've already used today's entry"}
                    </p>
                    <p className="app-muted text-sm">
                      {language === "tr"
                        ? "Yarın akşam tekrar yarışabilirsin. O zamana kadar çalışma notuna göz atabilirsin, bir dahaki sefere işine yarayabilir 👇"
                        : "You can compete again tomorrow evening. Until then, feel free to browse the study notes — might come in handy next time 👇"}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 border-t pt-6 sm:grid-cols-3" style={{ borderColor: "var(--color-border)" }}>
                    {WAITING_NOTES.map((t, i) => {
                      const TopicIcon = WAITING_TOPIC_ICONS[i] ?? WAITING_TOPIC_ICONS[0];
                      return (
                        <FlipCard
                          key={t.title.tr}
                          icon={<TopicIcon />}
                          title={t.title[language]}
                          body={t.body[language]}
                          color={WAITING_TOPIC_COLORS[i] ?? "var(--color-primary)"}
                        />
                      );
                    })}
                  </div>
                </Card>
              ) : screen === "register" ? (
                <RegisterScreen
                  registered={registered}
                  taken={registeredCount}
                  onTakenChange={setRegisteredCount}
                  onRegister={handleRegister}
                  onEnterLobby={() => goScreen("cheatsheet")}
                />
              ) : screen === "waiting" ? (
                <WaitingScreen onStart={() => goScreen("cheatsheet")} />
              ) : screen === "cheatsheet" ? (
                <CheatSheetScreen onFinish={() => goScreen("quiz")} />
              ) : screen === "quiz" ? (
                <QuizScreen
                  registeredCount={registeredCount}
                  powerups={powerups}
                  onUsePowerup={spendPowerup}
                  playSound={play}
                  onStartError={(message) => {
                    window.alert(message);
                    // `contestState` yenilenmezse `already_participated_today`
                    // eski (henuz basarisiz denemeden ONCEKI) degerinde kalir -
                    // kayit ekranindaki kapi bunu gormeden "Yarismaya kaydol"
                    // dugmesini GOSTERMEYE devam eder, kullanici ayni hatayi
                    // alip tekrar tekrar denemeye "kilitlenir" (bkz. Issue #65,
                    // "Oyunda Kayit Loop'a Giriyor"). Yenileme bu dongüyü kirar.
                    void contestState.refresh();
                    goScreen("register");
                  }}
                  onWin={(result) => {
                    setLastResult(result);
                    // Skor/ödül zaten backend'de kaydedildi (finishParticipation
                    // içinde) - burada yalnızca cüzdanı tazeliyoruz, ikinci bir
                    // yerel hesap YOK. `contestState` de yenilenir ki "zaten
                    // katıldın" kapısı (bkz. asağıdaki EliminatedScreen.onReview)
                    // bayat bilgiyle açılmasın.
                    void wallet.refresh();
                    void contestState.refresh();
                    play("win");
                    goScreen("victory");
                  }}
                  onLose={(result) => {
                    setLastResult(result);
                    void wallet.refresh();
                    void contestState.refresh();
                    goScreen("eliminated");
                  }}
                />
              ) : screen === "eliminated" && lastResult ? (
                <EliminatedScreen
                  result={lastResult}
                  // Yarışma artık bitti - "cheatsheet" (hazırlık, saatli, yeni
                  // katılım başlatan) ekrana DEĞİL, "register" kapısına gider:
                  // günlük hak zaten tükendiği için orada otomatik olarak
                  // WAITING_NOTES (sonraki günü beklerken) kartları açılır.
                  onReview={() => goScreen("register")}
                  onGoPoints={() => goTab("puanlar")}
                />
              ) : screen === "victory" && lastResult ? (
                <WinnerScreen result={lastResult} onGoPoints={() => goTab("puanlar")} />
              ) : (
                <Card>
                  <div className="space-y-4 py-10 text-center">
                    <p className="app-muted text-xs uppercase tracking-wide">{PAGE_TEXT.activeScreen[language]}</p>
                    <p className="app-heading text-2xl font-semibold">{SCREEN_LABELS[screen][language]}</p>
                    {lastResult ? (
                      <p className="app-muted text-sm">
                        {PAGE_TEXT.score[language]}: {lastResult.score.toLocaleString(language === "tr" ? "tr-TR" : "en-US")} · {PAGE_TEXT.correct[language]}:{" "}
                        {lastResult.correct} / {CONFIG.questionCount} · {PAGE_TEXT.reached[language]}:{" "}
                        {lastResult.reached}
                      </p>
                    ) : (
                      <p className="app-muted text-sm">
                        {
                          PAGE_TEXT.questionsSummary(
                            CONFIG.questionCount,
                            CONFIG.questionSeconds,
                            CONFIG.prizePool.toLocaleString(language === "tr" ? "tr-TR" : "en-US"),
                          )[language]
                        }
                      </p>
                    )}
                  </div>
                </Card>
              )}
            </div>

            {!isFocused && (
              <div className="hidden lg:block">
                <LeaderboardPanel myScore={lastResult?.score ?? null} />
              </div>
            )}
          </div>

          {process.env.NODE_ENV !== "production" && !inContest && (
            <Card title={PAGE_TEXT.devPanelTitle[language]}>
              <div className="flex flex-wrap gap-2">
                                {(Object.keys(SCREEN_LABELS) as GameScreen[]).map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      // "Kazandı"/"Elendi" ekranları lastResult'a ihtiyaç duyar —
                      // demo/test amaçlı sahte bir sonuç üretip direkt atlıyoruz.
                      if ((s === "victory" || s === "eliminated") && !lastResult) {
                        setLastResult({
                          won: s === "victory",
                          score: 950,
                          reached: s === "victory" ? CONFIG.questionCount : 4,
                          correct: s === "victory" ? CONFIG.questionCount : 3,
                          timedOut: false,
                          questionText:
                            language === "tr"
                              ? "Örnek soru: Bileşik faiz nedir?"
                              : "Sample question: What is compound interest?",
                          correctAnswer: language === "tr" ? "B şıkkı" : "Option B",
                          educationNote:
                            language === "tr"
                              ? "Bileşik faizde kazanılan faiz de faiz getirir."
                              : "With compound interest, earned interest also earns interest.",
                          rivalsAtEnd: 4,
                          payout: 950,
                        });
                      }
                      goScreen(s);
                    }}
                    className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                    style={{
                      borderColor: screen === s ? "var(--color-primary)" : "var(--color-border)",
                      color: screen === s ? "var(--color-primary)" : "var(--color-muted)",
                    }}
                  >
                    {SCREEN_LABELS[s][language]}
                  </button>
                ))}
                <button
                  onClick={() => {
                    setRegistered(false);
                    setLastResult(null);
                    void wallet.refresh();
                    goScreen("register");
                  }}
                  className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                  style={{ borderColor: "var(--color-primary)", color: "var(--color-primary)" }}
                >
                  {PAGE_TEXT.reset[language]}
                </button>
                <button
                  onClick={() => void handleResetToday()}
                  className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                  style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)" }}
                  title={
                    language === "tr"
                      ? "Backend'deki günlük katılım hakkını siler (sunum için)"
                      : "Deletes today's real backend entry (for demos)"
                  }
                >
                  {PAGE_TEXT.resetToday[language]}
                </button>
                <button
                  onClick={() => void handleResetShop()}
                  className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                  style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)" }}
                  title={
                    language === "tr"
                      ? "Backend'deki tüm mağaza satın almalarını siler, puanlar iade edilir (sunum için)"
                      : "Deletes all real backend shop purchases and refunds the points (for demos)"
                  }
                >
                  {PAGE_TEXT.resetShop[language]}
                </button>
              </div>
            </Card>
          )}
        </div>
      )}

      {tab === "kampanyalar" && (
        <CampaignsTab
          pointsBalance={displayedBalance}
          powerups={powerups}
          ownedBadges={wallet.badges}
          onBuyPowerup={buyPowerup}
          onBuyDonation={buyDonation}
        />
      )}

      {tab === "puanlar" && (
        <WalletTab
          pointsBalance={displayedBalance}
          history={wallet.history}
          onGoShop={() => goTab("kampanyalar")}
        />
      )}
    </div>
  );
}