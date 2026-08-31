"use client";

import { useState } from "react";
import Card from "../../components/ui/Card";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { useLanguage } from "../../contexts/LanguageContext";
import { RegisterScreen } from "../../components/oyun/RegisterScreen";
import { RulesModal } from "../../components/oyun/RulesModal";
import { WaitingScreen } from "../../components/oyun/WaitingScreen";
import { CheatSheetScreen } from "../../components/oyun/CheatSheetScreen";
import { QuizScreen } from "../../components/oyun/QuizScreen";
import { EliminatedScreen } from "../../components/oyun/EliminatedScreen";
import { WinnerScreen } from "../../components/oyun/WinnerScreen";
import type { Powerups } from "../../hooks/useQuiz";
import { useGameFlow, type GameScreen, type GameTab } from "../../hooks/useGameFlow";
import { CampaignsTab } from "../../components/oyun/CampaignsTab";
import {
  CONFIG,
  HISTORY,
  buildHistoryRow,
  type GameResult,
  type PowerupKind,
  type DonationItem,
  type HistoryRow,
} from "../../models/oyun";
import { WalletTab } from "../../components/oyun/WalletTab";
import { useSoundEffects } from "../../hooks/useSoundEffects";
import { IntroSidebar } from "../../components/oyun/IntroSidebar";
import { LeaderboardPanel } from "../../components/oyun/LeaderboardPanel";

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
  muteOn: { tr: "Sesi kapat", en: "Mute sound" },
  muteOff: { tr: "Sesi aç", en: "Unmute sound" },
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

  // Sözleşme kullanıcı başına bir kez onaylanır
  const [agreementSigned, setAgreementSigned] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [registered, setRegistered] = useState(false);

  // Jokerler — mağaza eklenene kadar test için başlangıç değeri veriliyor
  const [powerups, setPowerups] = useState<Powerups>({
    timeShield: 1,
    fiftyFifty: 1,
  });

  // Kayıt sayısı: hem kayıt ekranında hem yarışmadaki rakip sayacında kullanılır
  const [registeredCount, setRegisteredCount] = useState(640);

  // Son yarışmanın sonucu, sonuç ekranlarında kullanılacak
  const [lastResult, setLastResult] = useState<GameResult | null>(null);

  const [pointsBalance, setPointsBalance] = useState(4200);
  const [ownedBadges, setOwnedBadges] = useState<string[]>([]);
  const [history, setHistory] = useState<HistoryRow[]>(HISTORY);

  function spendPowerup(kind: keyof Powerups) {
    setPowerups((p) => ({ ...p, [kind]: Math.max(0, p[kind] - 1) }));
  }

  function buyPowerup(kind: PowerupKind, price: number) {
    if (pointsBalance < price) return;
    setPointsBalance((b) => b - price);
    setPowerups((p) => ({ ...p, [kind]: p[kind] + 1 }));
    play("purchase");
  }

  function buyDonation(item: DonationItem) {
    if (pointsBalance < item.cost || ownedBadges.includes(item.badge.tr)) return;
    setPointsBalance((b) => b - item.cost);
    setOwnedBadges((b) => [...b, item.badge.tr]);
    play("purchase");
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
  }

  return (
    <div className="space-y-6">
      <RulesModal open={rulesOpen} onAccept={handleAcceptRules} />

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

      {tab === "oyun" && (
        <div className="space-y-4">
          <div
            className={
              isFocused
                ? "mx-auto max-w-3xl"
                : "grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_300px]"
            }
          >
            {!isFocused && (
              <div className="hidden lg:block">
                <IntroSidebar registered={registered} taken={registeredCount} />
              </div>
            )}

            <div className="min-w-0">
              {screen === "register" ? (
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
                  onWin={(result) => {
                    setLastResult(result);
                    const earned = Math.round(CONFIG.prizePool * 0.05);
                    setPointsBalance((b) => b + earned);
                    setHistory((h) => [buildHistoryRow(result, earned, language), ...h]);
                    play("win");
                    goScreen("victory");
                  }}
                  onLose={(result) => {
                    setLastResult(result);
                    setHistory((h) => [buildHistoryRow(result, 0, language), ...h]);
                    goScreen("eliminated");
                  }}
                />
              ) : screen === "eliminated" && lastResult ? (
                <EliminatedScreen
                  result={lastResult}
                  onReview={() => goScreen("cheatsheet")}
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

          {/* Gelistirme/QA araci: ekranlar arasi manuel gecis ve state sifirlama.
              Gercek kullanicilar oyunu hile yapmadan, sirayla oynamali - bu
              yuzden SADECE local `next dev` build'inde gorunur, production'a
              hicbir zaman gitmez. */}
          {process.env.NODE_ENV !== "production" && (
            <Card title={PAGE_TEXT.devPanelTitle[language]}>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(SCREEN_LABELS) as GameScreen[]).map((s) => (
                  <button
                    key={s}
                    onClick={() => goScreen(s)}
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
                    setAgreementSigned(false);
                    setRegistered(false);
                    setPowerups({ timeShield: 1, fiftyFifty: 1 });
                    setLastResult(null);
                    setPointsBalance(4200);
                    setOwnedBadges([]);
                    setHistory(HISTORY);
                    goScreen("register");
                  }}
                  className="rounded-lg border px-3 py-1.5 text-xs font-semibold transition"
                  style={{ borderColor: "var(--color-primary)", color: "var(--color-primary)" }}
                >
                  {PAGE_TEXT.reset[language]}
                </button>
              </div>
            </Card>
          )}
        </div>
      )}

      {tab === "kampanyalar" && (
        <CampaignsTab
          pointsBalance={pointsBalance}
          powerups={powerups}
          ownedBadges={ownedBadges}
          onBuyPowerup={buyPowerup}
          onBuyDonation={buyDonation}
        />
      )}

      {tab === "puanlar" && (
        <WalletTab
          pointsBalance={pointsBalance}
          history={history}
          onGoShop={() => goTab("kampanyalar")}
        />
      )}
    </div>
  );
}
