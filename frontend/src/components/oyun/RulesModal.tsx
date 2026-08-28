"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  open: boolean;
  onAccept: () => void;
};

const RULES: { title: string; body: string; list?: string[]; warn?: boolean }[] = [
  {
    title: "Katılım koşulu",
    body: "Yarışmaya giriş yapmış ve vadesiz hesabı bulunan kullanıcılar katılabilir. Kayıt kontenjanla sınırlıdır ve yarışma saatinden 5 dakika önce kapanır. Bir kullanıcı aynı yarışmaya yalnızca bir kez kayıt olabilir.",
  },
  {
    title: "Hazırlık",
    body: "Yarışma saatinde 5 dakikalık çalışma notu açılır. Sorular yalnızca bu konulardan gelir. Not konuyu anlatır, cevap anahtarı vermez.",
  },
  {
    title: "Sorular ve süre",
    body: "10 soru sorulur, her soru için 15 saniye verilir. Sorular tüm katılımcılara aynı anda gösterilir. Cevap onaylandıktan sonra değiştirilemez.",
  },
  {
    title: "Eleme",
    body: "Yanlış cevap ve süre aşımı elenme nedenidir. Elenen katılımcı kalan soruları göremez; yalnızca elendiği sorunun doğru cevabını ve açıklamasını görür. Yarışmadan çıkmak da elenme sayılır.",
  },
  {
    title: "Skor ve ödül",
    body: "Her doğru cevap 100 taban puan kazandırır, kalan süreye göre en fazla 100 puan hız bonusu eklenir. Tüm soruları doğru bilenler ödül havuzunu paylaşır; pay, skorunuzun kazananların toplam skoru içindeki oranına göre hesaplanır ve bonus puan olarak yüklenir.",
  },
  {
    title: "Hile ve kötüye kullanım",
    warn: true,
    body: "Aşağıdaki davranışlar tespit edildiğinde katılım iptal edilir, kazanılan puanlar geri alınır ve hesap yarışmalardan süresiz men edilebilir:",
    list: [
      "Aynı kişiye ait birden fazla hesapla katılım",
      "Otomasyon, bot veya betik kullanarak cevap gönderme",
      "Yarışma sırasında soru veya cevapların üçüncü kişilerle paylaşılması",
      "Uygulama arayüzünü veya ağ isteklerini değiştirmeye yönelik girişimler",
      "Davet mekanizmasının sahte hesaplarla suistimali",
    ],
  },
];

export function RulesModal({ open, onAccept }: Props) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [readToEnd, setReadToEnd] = useState(false);
  const [progress, setProgress] = useState(0);

  const check = useCallback(() => {
    const el = bodyRef.current;
    if (!el) return;

    const max = el.scrollHeight - el.clientHeight;

    // Metin tek ekrana sığıyorsa kaydırma beklenmez
    if (max <= 4) {
      setReadToEnd(true);
      setProgress(100);
      return;
    }

    setProgress(Math.min(100, (el.scrollTop / max) * 100));
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 24) {
      setReadToEnd(true);
      setProgress(100);
    }
  }, []);

  // Açılışta bir kez ölç: kısa ekranlarda metin sığmayabilir
  useEffect(() => {
    if (!open) return;
    const id = setTimeout(check, 80);
    return () => clearTimeout(id);
  }, [open, check]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[80] grid place-items-center p-5"
      style={{ background: "rgba(2, 6, 23, 0.55)", backdropFilter: "blur(3px)" }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="rules-title"
    >
      <div
        className="flex max-h-[86vh] w-full max-w-2xl flex-col rounded-xl shadow-2xl"
        style={{ background: "var(--color-surface)" }}
      >
        <div className="border-b p-6 pb-4" style={{ borderColor: "var(--color-border)" }}>
          <p
            className="text-[11px] font-bold uppercase tracking-[0.16em]"
            style={{ color: "var(--color-cta)" }}
          >
            Şans Yatırımda
          </p>
          <h3 id="rules-title" className="app-heading mt-1 text-xl font-semibold">
            Yarışma kuralları
          </h3>
          <p className="app-muted mt-0.5 text-sm">Katılmadan önce okuman gerekenler</p>
        </div>

        <div ref={bodyRef} onScroll={check} className="flex-1 overflow-y-auto px-6 py-5">
          {RULES.map((r, i) => (
            <div
              key={r.title}
              className={`mb-4 flex gap-3.5 ${r.warn ? "rounded-lg border p-4" : ""}`}
              style={
                r.warn
                  ? {
                      background: "var(--color-danger-bg)",
                      borderColor: "var(--color-danger-border)",
                    }
                  : undefined
              }
            >
              <span
                className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-xs font-bold"
                style={{
                  background: r.warn ? "var(--color-danger)" : "var(--color-panel-dark)",
                  color: "#fff",
                }}
              >
                {r.warn ? "!" : i + 1}
              </span>
              <div>
                <b
                  className="mb-1 block text-sm font-semibold"
                  style={{ color: r.warn ? "var(--color-danger-text)" : "var(--color-heading)" }}
                >
                  {r.title}
                </b>
                <p className="app-muted text-[13px] leading-relaxed">{r.body}</p>
                {r.list && (
                  <ul className="app-muted mt-2 list-disc pl-5 text-[13px] leading-relaxed">
                    {r.list.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}

          <p
            className="app-muted border-t pt-3 text-[11.5px] leading-relaxed"
            style={{ borderColor: "var(--color-border-soft)" }}
          >
            Cevapların doğruluğu ve süre ölçümü sunucu tarafında yapılır; istemci üzerinden
            yapılan müdahaleler sonucu değiştirmez. Bu bir demo ortamıdır; gösterilen tutar,
            kampanya ve ödüller temsilîdir.
          </p>
        </div>

        <div
          className="flex flex-wrap items-center justify-between gap-4 border-t p-6 pt-4"
          style={{ borderColor: "var(--color-border)" }}
        >
          <div className="min-w-[190px] flex-1">
            <div
              className="mb-1.5 h-1 overflow-hidden rounded-full"
              style={{ background: "var(--color-border)" }}
            >
              <span
                className="block h-full rounded-full transition-[width] duration-150"
                style={{ width: `${progress}%`, background: "var(--color-success)" }}
              />
            </div>
            <span
              className="text-[11.5px] font-medium"
              style={{ color: readToEnd ? "var(--color-success)" : "var(--color-muted)" }}
            >
              {readToEnd ? "✓ Metnin tamamını okudunuz" : "Onaylamak için metnin sonuna kadar okuyun"}
            </span>
          </div>

          <button
            onClick={onAccept}
            disabled={!readToEnd}
            className="rounded-lg px-7 py-3 text-sm font-semibold transition disabled:cursor-not-allowed"
            style={{
              background: readToEnd ? "var(--color-success)" : "var(--color-border)",
              color: readToEnd ? "#fff" : "var(--color-muted)",
            }}
          >
            Anladım, devam et
          </button>
        </div>
      </div>
    </div>
  );
}
