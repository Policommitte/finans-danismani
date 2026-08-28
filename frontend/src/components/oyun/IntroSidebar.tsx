"use client";

import Card from "../ui/Card";
import { InfoFlipCard } from "./InfoFlipCard";
import { CONFIG } from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";

type Props = {
  registered: boolean;
  taken: number;
};

const HOW_TO_PLAY = [
  {
    tr: `Her akşam saat 20.00'de tek seans olarak başlar, kayıt 19.55'te kapanır.`,
    en: `It starts as a single session every evening at 8:00 PM, registration closes at 7:55 PM.`,
  },
  {
    tr: `Sırayla ${CONFIG.questionCount} soru gelir, her birine ${CONFIG.questionSeconds} saniye içinde cevap vermen gerekir.`,
    en: `${CONFIG.questionCount} questions come one after another, and you must answer each within ${CONFIG.questionSeconds} seconds.`,
  },
  {
    tr: "Yanlış cevap ya da süre aşımı seni yarışmadan eler; doğru cevap ve açıklaması gösterilir.",
    en: "A wrong answer or timing out eliminates you from the contest; the correct answer and its explanation are shown.",
  },
  {
    tr: "Tüm soruları doğru bilenler kazanır ve ödül havuzunu skorlarına göre paylaşır.",
    en: "Those who answer all questions correctly win and share the prize pool based on their scores.",
  },
];

export function IntroSidebar({ registered, taken }: Props) {
  const { language } = useLanguage();

  return (
    <div className="flex h-full flex-col gap-4">
      <Card>
        <p
          className="text-[11px] font-bold uppercase tracking-[0.16em]"
          style={{ color: "var(--color-cta)" }}
        >
          Şans Yatırımda
        </p>
        <h3 className="app-heading mt-2 text-lg font-semibold leading-snug">
          {language === "tr" ? "Finans bilginle yarış, ödülden pay al" : "Compete with your finance knowledge, claim a share of the prize"}
        </h3>
        <p className="app-muted mt-2 text-[13px] leading-relaxed">
          {language === "tr"
            ? `Her akşam 20.00'de ${CONFIG.questionCount} soruluk canlı yarışma.`
            : `A live contest with ${CONFIG.questionCount} questions every evening at 8:00 PM.`}
        </p>
      </Card>

      <Card>
        <span className="app-muted block text-xs">
          {language === "tr" ? "Ödül havuzu" : "Prize pool"}
        </span>
        <b className="app-heading block text-2xl font-bold tabular-nums">
          {CONFIG.prizePool.toLocaleString(language === "tr" ? "tr-TR" : "en-US")}
        </b>
        <span className="app-muted text-xs">
          {language === "tr" ? "bonus puan" : "bonus points"}
        </span>
      </Card>

      <Card>
        <span className="app-muted block text-xs">
          {language === "tr" ? "Kayıt durumu" : "Registration status"}
        </span>
        <div
          className="mt-2 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[13px] font-semibold"
          style={{
            background: registered ? "var(--color-primary-soft)" : "var(--color-surface-muted)",
            color: registered ? "var(--color-primary-soft-text)" : "var(--color-muted)",
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: registered ? "var(--color-success)" : "var(--color-muted)" }}
          />
          {registered
            ? (language === "tr" ? "Kayıtlısın" : "You're registered")
            : (language === "tr" ? "Henüz kayıtlı değilsin" : "You're not registered yet")}
        </div>
        <p className="app-muted mt-2 text-xs">
          <b className="tabular-nums">{taken}</b> / {CONFIG.capacityTotal}{" "}
          {language === "tr" ? "kişi kayıtlı" : "people registered"}
        </p>
      </Card>

      <div className="flex-1">
        <InfoFlipCard
          icon="❓"
          title={language === "tr" ? "Nasıl oynanır?" : "How to play?"}
          color="var(--color-primary)"
          orientation="vertical"
        >
          <ul className="list-disc space-y-1.5 pl-4">
            {HOW_TO_PLAY.map((line) => (
              <li key={line.tr}>{line[language]}</li>
            ))}
          </ul>
        </InfoFlipCard>
      </div>
    </div>
  );
}
