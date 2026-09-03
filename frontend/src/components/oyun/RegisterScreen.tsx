"use client";

import { useEffect, useRef, useState } from "react";
import Card from "../ui/Card";
import { InfoFlipCard } from "./InfoFlipCard";
import { useCountdown, nextContestTime } from "../../hooks/useCountdown";
import { CONFIG } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  registered: boolean;
  /** Kayıt sayısı üst bileşende tutulur; yarışmadaki rakip sayacı da bunu kullanır */
  taken: number;
  onTakenChange: (n: number) => void;
  onRegister: () => void;
  onEnterLobby: () => void;
};

const INFO = [
  {
    title: { tr: "Süreye karşı yarış", en: "Race against the clock" },
    body: {
      tr: `${CONFIG.questionCount} soru, her biri için ${CONFIG.questionSeconds} saniye. Hızlı cevap skoru yükseltir.`,
      en: `${CONFIG.questionCount} questions, ${CONFIG.questionSeconds} seconds each. Answering fast boosts your score.`,
    },
  },
  {
    title: { tr: "Öğreten eğitim kartları", en: "Educational feedback" },
    body: {
      tr: "Elenirsen doğru cevabı ve konunun açıklamasını görürsün.",
      en: "If you're eliminated, you'll see the correct answer and an explanation of the topic.",
    },
  },
  {
    title: { tr: "Skor payına göre ödül", en: "Reward by score share" },
    body: {
      tr: `${CONFIG.prizePool.toLocaleString("tr-TR")} bonus puan, kazananlar arasında skor payına göre dağıtılır.`,
      en: `${CONFIG.prizePool.toLocaleString("en-US")} bonus points, split among winners according to their score share.`,
    },
  },
];

const FAQ = [
  {
    q: { tr: "Nasıl katılırım?", en: "How do I join?" },
    a: {
      tr: "Giriş yapmış ve vadesiz hesabın olması yeterli. İlk katılımda bir kez sözleşme onayı istenir.",
      en: "Being logged in with a demand deposit account is enough. A one-time agreement confirmation is required on your first entry.",
    },
  },
  {
    q: { tr: "Elenirsem ne olur?", en: "What happens if I'm eliminated?" },
    a: {
      tr: "O anki skorun ve ulaşılan soru kaydedilir, doğru cevap gösterilir. Bir sonraki akşam tekrar katılabilirsin.",
      en: "Your current score and the question you reached are recorded, and the correct answer is shown. You can join again the following evening.",
    },
  },
  {
    q: { tr: "Jokerleri nasıl kazanırım?", en: "How do I get power-ups?" },
    a: {
      tr: "Çift puan ve çifte şans jokerlerini Mağaza sekmesinden bonus puanla satın alabilirsin.",
      en: "You can buy the double points and double chance power-ups with bonus points from the Shop tab.",
    },
  },
  {
    q: { tr: "Ödül nasıl dağıtılır?", en: "How are prizes distributed?" },
    a: {
      tr: `${CONFIG.prizePool.toLocaleString("tr-TR")} puanlık havuz, kazananlar arasında skor payına göre bölüşülür.`,
      en: `The ${CONFIG.prizePool.toLocaleString("en-US")}-point pool is split among winners according to their score share.`,
    },
  },
  {
    q: { tr: "Günde kaç kez katılabilirim?", en: "How many times a day can I join?" },
    a: {
      tr: "Katılım kullanıcı başına günde bir kez ile sınırlıdır.",
      en: "Participation is limited to once per day per user.",
    },
  },
];

function MessageCircleIcon({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

//: Kalan sureye gore sayac rengi - bol vakit varken yesil, son 1 saatte
//: sari/altina, son birkac dakikada kirmiziya doner. Turuncu (--color-cta)
//: hic kullanilmaz: yesil<->sari gecisi guvenli (asla turuncuya kacmaz),
//: sari<->kirmizi gecisi ise SADECE son 2 dakikaya sikistirilir - kisa
//: surdugu icin ara karede goze carpan bir "turuncu an" degil, hizli bir
//: kirmiziya donus gibi algilanir.
const COUNTDOWN_HOUR = 3600;
const COUNTDOWN_WARNING = 900; // 15 dk
const COUNTDOWN_URGENT = 120; // 2 dk

function countdownColor(totalSeconds: number): string {
  if (totalSeconds > COUNTDOWN_HOUR) {
    return "var(--color-success)";
  }
  if (totalSeconds > COUNTDOWN_WARNING) {
    const ratio = (totalSeconds - COUNTDOWN_WARNING) / (COUNTDOWN_HOUR - COUNTDOWN_WARNING);
    return `color-mix(in srgb, var(--color-success) ${Math.round(ratio * 100)}%, var(--color-chart-yellow) ${Math.round((1 - ratio) * 100)}%)`;
  }
  if (totalSeconds > COUNTDOWN_URGENT) {
    return "var(--color-chart-yellow)";
  }
  const ratio = totalSeconds / COUNTDOWN_URGENT;
  return `color-mix(in srgb, var(--color-chart-yellow) ${Math.round(ratio * 100)}%, var(--color-danger) ${Math.round((1 - ratio) * 100)}%)`;
}

export function RegisterScreen({ registered, taken, onTakenChange, onRegister, onEnterLobby }: Props) {
  const { language } = useLanguage();
  const [target] = useState(() => nextContestTime());
  const { hours, minutes, seconds, total } = useCountdown(target);

  // Aralık içinden güncel değere erişmek için: efekt yeniden kurulmasın
  const takenRef = useRef(taken);
  takenRef.current = taken;

   // Diğer katılımcılar kayıt oldukça sayı artar; kontenjan dolunca duracak
  useEffect(() => {
    const id = setInterval(() => {
      if (takenRef.current >= CONFIG.capacityTotal) {
        clearInterval(id);
        return;
      }
      if (Math.random() < 0.25) {
        onTakenChange(Math.min(CONFIG.capacityTotal, takenRef.current + 1));
      }
    }, 5000);
    return () => clearInterval(id);
  }, [onTakenChange]);

  const isFull = taken >= CONFIG.capacityTotal;
  const isClosed = total === 0;
  const started = total === 0;

  const label = registered
    ? started
      ? (language === "tr" ? "Lobiye gir →" : "Enter lobby →")
      : (language === "tr" ? "Kaydın alındı ✓" : "You're registered ✓")
    : isFull
      ? (language === "tr" ? "Kontenjan doldu" : "Registration full")
      : isClosed
        ? (language === "tr" ? "Kayıt kapandı" : "Registration closed")
        : (language === "tr" ? "Yarışmaya kaydol →" : "Register for the contest →");

  const disabled = (registered && !started) || (!registered && (isFull || isClosed));

  return (
    <div className="space-y-4">
      <Card>
        <div className="py-6 text-center">
          {/* geri sayım + kaydol */}
          <div
            className="mx-auto flex max-w-xl flex-wrap items-center justify-center gap-5 rounded-xl border p-5"
            style={{
              background: "var(--color-primary-soft)",
              borderColor: "color-mix(in srgb, var(--color-primary) 35%, transparent)",
            }}
          >
            <div className="text-left">
              <span className="app-muted block text-xs">
                {language === "tr" ? "Yarışmaya kalan süre" : "Time until the contest"}
              </span>
              <strong
                className="block text-3xl font-bold tabular-nums"
                style={{ color: countdownColor(total), transition: "color 600ms ease" }}
              >
                {hours}:{minutes}:{seconds}
              </strong>
            </div>

            <button
              onClick={registered ? onEnterLobby : onRegister}
              disabled={disabled}
              className={`rounded-full px-7 py-3.5 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${
                disabled ? "" : "hover:scale-[1.03] hover:shadow-xl active:scale-[0.98]"
              }`}
              style={
                disabled
                  ? { background: "var(--color-border)", color: "var(--color-muted)" }
                  : {
                      background:
                        "linear-gradient(135deg, var(--color-primary) 0%, color-mix(in srgb, var(--color-primary) 70%, #7c3aed) 100%)",
                      boxShadow: "0 8px 24px color-mix(in srgb, var(--color-primary) 45%, transparent)",
                    }
              }
            >
              <span className="inline-flex items-center justify-center gap-2">
                {!disabled && (
                  <span className="text-base" aria-hidden="true">
                    {registered ? "🎮" : "🏆"}
                  </span>
                )}
                {label}
              </span>
            </button>
          </div>

          {/* kontenjan doluluğu */}
          <div className="mx-auto mt-4 max-w-xl">
            <div
              className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-[13px]"
              style={{
                background: "var(--color-primary-soft)",
                color: "var(--color-primary-soft-text)",
              }}
            >
              <span
                className="h-1.5 w-1.5 animate-pulse rounded-full"
                style={{ background: "var(--color-success)" }}
              />
              {language === "tr" ? (
                <>
                  <b className="font-bold tabular-nums">{taken}</b> kişi bu akşamki yarışmaya
                  kaydoldu
                </>
              ) : (
                <>
                  <b className="font-bold tabular-nums">{taken}</b> people registered for tonight&apos;s
                  contest
                </>
              )}
            </div>

            <div
              className="mt-3 h-1.5 overflow-hidden rounded-full"
              style={{ background: "var(--color-border)" }}
            >
              <span
                className="block h-full rounded-full transition-[width] duration-500"
                style={{
                  width: `${(taken / CONFIG.capacityTotal) * 100}%`,
                  background: isFull ? "var(--color-primary)" : "var(--color-success)",
                }}
              />
            </div>
          </div>

          <p className="app-muted mt-3 text-xs">
            {language === "tr"
              ? "Kayıt 19.55'te kapanır · ilk katılımda sözleşme onayı gerekir"
              : "Registration closes at 7:55 PM · agreement confirmation is required on your first entry"}
          </p>
        </div>
      </Card>

      {/* üç bilgi kartı */}
      <div className="grid gap-4 md:grid-cols-3">
        {INFO.map((c) => (
          <Card key={c.title.tr}>
            <h3 className="app-heading text-[15px] font-semibold">{c.title[language]}</h3>
            <p className="app-muted mt-1.5 text-[13px] leading-relaxed">{c.body[language]}</p>
          </Card>
        ))}
      </div>

      {/* durum satırı */}
      <Card>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <span className="app-muted block text-xs">
              {language === "tr" ? "Ödül havuzu" : "Prize pool"}
            </span>
            <b className="app-heading text-lg font-semibold tabular-nums">
              {CONFIG.prizePool.toLocaleString(language === "tr" ? "tr-TR" : "en-US")}
            </b>
            <span className="app-muted ml-1 text-xs">
              {language === "tr" ? "bonus puan" : "bonus points"}
            </span>
          </div>
          <div>
            <span className="app-muted block text-xs">
              {language === "tr" ? "Kontenjan" : "Capacity"}
            </span>
            <b className="app-heading text-lg font-semibold tabular-nums">
              {taken} / {CONFIG.capacityTotal}
            </b>
          </div>
          <div>
            <span className="app-muted block text-xs">
              {language === "tr" ? "Soru" : "Questions"}
            </span>
            <b className="app-heading text-lg font-semibold">
              {CONFIG.questionCount} × {CONFIG.questionSeconds} {language === "tr" ? "sn" : "sec"}
            </b>
          </div>
        </div>
      </Card>

      {/* SSS — geniş, yatay flip kart */}
      <InfoFlipCard
        icon={<MessageCircleIcon />}
        title={language === "tr" ? "Sıkça sorulan sorular" : "Frequently asked questions"}
        color="var(--color-primary)"
        orientation="horizontal"
      >
        {FAQ.map((item) => (
          <div key={item.q.tr}>
            <p className="app-heading font-semibold">{item.q[language]}</p>
            <p className="mt-0.5">{item.a[language]}</p>
          </div>
        ))}
      </InfoFlipCard>
    </div>
  );
}
