"use client";

import Card from "../ui/Card";
import { InfoFlipCard } from "./InfoFlipCard";
import { CONFIG } from "../../models/oyun";

type Props = {
  registered: boolean;
  taken: number;
};

const HOW_TO_PLAY = [
  `Her akşam saat 20.00'de tek seans olarak başlar, kayıt 19.55'te kapanır.`,
  `Sırayla ${CONFIG.questionCount} soru gelir, her birine ${CONFIG.questionSeconds} saniye içinde cevap vermen gerekir.`,
  "Yanlış cevap ya da süre aşımı seni yarışmadan eler; doğru cevap ve açıklaması gösterilir.",
  "Tüm soruları doğru bilenler kazanır ve ödül havuzunu skorlarına göre paylaşır.",
];

export function IntroSidebar({ registered, taken }: Props) {
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
          Finans bilginle yarış, ödülden pay al
        </h3>
        <p className="app-muted mt-2 text-[13px] leading-relaxed">
          Her akşam 20.00&apos;de {CONFIG.questionCount} soruluk canlı yarışma.
        </p>
      </Card>

      <Card>
        <span className="app-muted block text-xs">Ödül havuzu</span>
        <b className="app-heading block text-2xl font-bold tabular-nums">
          {CONFIG.prizePool.toLocaleString("tr-TR")}
        </b>
        <span className="app-muted text-xs">bonus puan</span>
      </Card>

      <Card>
        <span className="app-muted block text-xs">Kayıt durumu</span>
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
          {registered ? "Kayıtlısın" : "Henüz kayıtlı değilsin"}
        </div>
        <p className="app-muted mt-2 text-xs">
          <b className="tabular-nums">{taken}</b> / {CONFIG.capacityTotal} kişi kayıtlı
        </p>
      </Card>

      <div className="flex-1">
        <InfoFlipCard icon="❓" title="Nasıl oynanır?" color="var(--color-primary)" orientation="vertical">
          <ul className="list-disc space-y-1.5 pl-4">
            {HOW_TO_PLAY.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </InfoFlipCard>
      </div>
    </div>
  );
}