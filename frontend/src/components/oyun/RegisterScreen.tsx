"use client";

import { useEffect, useRef, useState } from "react";
import Card from "../ui/Card";
import { InfoFlipCard } from "./InfoFlipCard";
import { useCountdown, nextContestTime } from "../../hooks/useCountdown";
import { CONFIG } from "../../models/oyun";

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
    title: "Süreye karşı yarış",
    body: `${CONFIG.questionCount} soru, her biri için ${CONFIG.questionSeconds} saniye. Hızlı cevap skoru yükseltir.`,
  },
  {
    title: "Öğreten eğitim kartları",
    body: "Elenirsen doğru cevabı ve konunun açıklamasını görürsün.",
  },
  {
    title: "Skor payına göre ödül",
    body: `${CONFIG.prizePool.toLocaleString("tr-TR")} bonus puan, kazananlar arasında skor payına göre dağıtılır.`,
  },
];

const FAQ = [
  {
    q: "Nasıl katılırım?",
    a: "Giriş yapmış ve vadesiz hesabın olması yeterli. İlk katılımda bir kez sözleşme onayı istenir.",
  },
  {
    q: "Elenirsem ne olur?",
    a: "O anki skorun ve ulaşılan soru kaydedilir, doğru cevap gösterilir. Bir sonraki akşam tekrar katılabilirsin.",
  },
  {
    q: "Jokerleri nasıl kazanırım?",
    a: "Zaman kalkanı ve çifte şans jokerlerini Mağaza sekmesinden bonus puanla satın alabilirsin.",
  },
  {
    q: "Ödül nasıl dağıtılır?",
    a: `${CONFIG.prizePool.toLocaleString("tr-TR")} puanlık havuz, kazananlar arasında skor payına göre bölüşülür.`,
  },
  {
    q: "Günde kaç kez katılabilirim?",
    a: "Katılım kullanıcı başına günde bir kez ile sınırlıdır.",
  },
];

export function RegisterScreen({ registered, taken, onTakenChange, onRegister, onEnterLobby }: Props) {
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
      ? "Lobiye gir →"
      : "Kaydın alındı ✓"
    : isFull
      ? "Kontenjan doldu"
      : isClosed
        ? "Kayıt kapandı"
        : "Yarışmaya kaydol →";

  const disabled = (registered && !started) || (!registered && (isFull || isClosed));

  return (
    <div className="space-y-4">
      <Card>
        <div className="py-6 text-center">
          <p
            className="text-[11px] font-bold uppercase tracking-[0.16em]"
            style={{ color: "var(--color-cta)" }}
          >
            Canlı finansal bilgi yarışması
          </p>
          <h2 className="app-heading mx-auto mt-2 max-w-xl text-3xl font-bold leading-tight">
            Finans bilginle yarış, ödül havuzundan pay al
          </h2>
          <p className="app-muted mx-auto mt-3 max-w-xl text-sm leading-relaxed">
            Günün yarışması saat 20.00&apos;de başlıyor. {CONFIG.questionCount} finans sorusunu
            süresi içinde doğru cevapla, kazananlar arasına gir.
          </p>

          {/* geri sayım + kaydol */}
          <div
            className="mx-auto mt-7 flex max-w-xl flex-wrap items-center justify-center gap-5 rounded-xl border border-dashed p-5"
            style={{
              background: "var(--color-primary-soft)",
              borderColor: "var(--color-primary)",
            }}
          >
            <div className="text-left">
              <span className="app-muted block text-xs">Yarışmaya kalan süre</span>
              <strong
                className="block text-3xl font-bold tabular-nums"
                style={{ color: "var(--color-primary-soft-text)" }}
              >
                {hours}:{minutes}:{seconds}
              </strong>
            </div>

            <button
              onClick={registered ? onEnterLobby : onRegister}
              disabled={disabled}
              className="rounded-lg px-7 py-3.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60"
              style={{
                background: disabled ? "var(--color-border)" : "var(--color-cta)",
                color: disabled ? "var(--color-muted)" : "#fff",
              }}
            >
              {label}
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
              <b className="font-bold tabular-nums">{taken}</b> kişi bu akşamki yarışmaya
              kaydoldu
            </div>

            <div
              className="mt-3 h-1.5 overflow-hidden rounded-full"
              style={{ background: "var(--color-border)" }}
            >
              <span
                className="block h-full rounded-full transition-[width] duration-500"
                style={{
                  width: `${(taken / CONFIG.capacityTotal) * 100}%`,
                  background: isFull ? "var(--color-cta)" : "var(--color-success)",
                }}
              />
            </div>
          </div>

          <p className="app-muted mt-3 text-xs">
            Kayıt 19.55&apos;te kapanır · ilk katılımda sözleşme onayı gerekir
          </p>
        </div>
      </Card>

      {/* üç bilgi kartı */}
      <div className="grid gap-4 md:grid-cols-3">
        {INFO.map((c) => (
          <Card key={c.title}>
            <h3 className="app-heading text-[15px] font-semibold">{c.title}</h3>
            <p className="app-muted mt-1.5 text-[13px] leading-relaxed">{c.body}</p>
          </Card>
        ))}
      </div>

      {/* durum satırı */}
      <Card>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <span className="app-muted block text-xs">Ödül havuzu</span>
            <b className="app-heading text-lg font-semibold tabular-nums">
              {CONFIG.prizePool.toLocaleString("tr-TR")}
            </b>
            <span className="app-muted ml-1 text-xs">bonus puan</span>
          </div>
          <div>
            <span className="app-muted block text-xs">Kontenjan</span>
            <b className="app-heading text-lg font-semibold tabular-nums">
              {taken} / {CONFIG.capacityTotal}
            </b>
          </div>
          <div>
            <span className="app-muted block text-xs">Soru</span>
            <b className="app-heading text-lg font-semibold">
              {CONFIG.questionCount} × {CONFIG.questionSeconds} sn
            </b>
          </div>
        </div>
      </Card>

      {/* SSS — geniş, yatay flip kart */}
      <InfoFlipCard
        icon="💬"
        title="Sıkça sorulan sorular"
        color="var(--color-cta)"
        orientation="horizontal"
      >
        {FAQ.map((item) => (
          <div key={item.q}>
            <p className="app-heading font-semibold">{item.q}</p>
            <p className="mt-0.5">{item.a}</p>
          </div>
        ))}
      </InfoFlipCard>
    </div>
  );
}