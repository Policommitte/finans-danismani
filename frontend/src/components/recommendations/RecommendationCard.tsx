"use client";

import { useEffect, useState } from "react";
import type { Recommendation, RejectionReason } from "../../models/recommendation";
import Button from "../ui/Button";
import { useLanguage } from "../../contexts/LanguageContext";

/** FR-AUT-023: gerekce kumesi sunucudakiyle BIREBIR aynidir. */
const RET_GEREKCELERI: Array<{ value: RejectionReason; tr: string; en: string }> = [
  { value: "NOT_INTERESTED", tr: "İlgilenmiyorum", en: "Not interested" },
  { value: "TOO_RISKY", tr: "Riskli buluyorum", en: "Too risky" },
  { value: "NO_CASH", tr: "Nakit yok", en: "No cash available" },
  { value: "BAD_TIMING", tr: "Zamanlaması yanlış", en: "Bad timing" },
  { value: "NOT_UNDERSTOOD", tr: "Anlamadım", en: "I didn't understand it" },
];

function kalanSure(expiresAt: string, language: string): string {
  const kalan = new Date(expiresAt).getTime() - Date.now();
  if (kalan <= 0) return language === "tr" ? "süresi doldu" : "expired";
  const dakika = Math.floor(kalan / 60000);
  if (dakika < 60) return language === "tr" ? `${dakika} dk kaldı` : `${dakika} min left`;
  const saat = Math.floor(dakika / 60);
  return language === "tr" ? `${saat} sa ${dakika % 60} dk kaldı` : `${saat}h ${dakika % 60}m left`;
}

type Props = {
  recommendation: Recommendation;
  submitting: boolean;
  onApprove: (id: number, quantity: number | null) => void;
  onReject: (id: number, reason: RejectionReason) => void;
};

export function RecommendationCard({ recommendation, submitting, onApprove, onReject }: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY" });
  const [quantity, setQuantity] = useState(String(recommendation.quantity));
  const [rejecting, setRejecting] = useState(false);
  const [nedenAcik, setNedenAcik] = useState(false);
  const [kalan, setKalan] = useState(() => kalanSure(recommendation.expires_at, language));

  // TTL geri sayimi: kart acikken sure dolabilir, kullanici bunu gormeli.
  useEffect(() => {
    const timer = window.setInterval(
      () => setKalan(kalanSure(recommendation.expires_at, language)),
      30_000,
    );
    return () => window.clearInterval(timer);
  }, [recommendation.expires_at, language]);

  const alim = recommendation.side === "BUY";
  const acik = recommendation.status === "PUBLISHED" || recommendation.status === "VIEWED";
  const suresiDoldu = new Date(recommendation.expires_at).getTime() <= Date.now();
  const parsed = Number(quantity);
  const gecerliAdet = Number.isFinite(parsed) && parsed > 0;

  return (
    <article className="rounded-xl border app-border p-4">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-md px-2 py-0.5 text-xs font-bold text-white ${
                alim ? "bg-emerald-600" : "bg-rose-600"
              }`}
            >
              {alim ? (language === "tr" ? "AL" : "BUY") : language === "tr" ? "SAT" : "SELL"}
            </span>
            <p className="truncate font-semibold app-heading">{recommendation.asset_symbol}</p>
          </div>
          <p className="mt-0.5 truncate text-sm app-muted">{recommendation.asset_name}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xs app-muted">{language === "tr" ? "Güven" : "Confidence"}</p>
          <p className="font-semibold app-heading">
            %{Math.round(recommendation.confidence * 100)}
          </p>
        </div>
      </header>

      <dl className="mt-3 grid grid-cols-3 gap-2 rounded-lg app-card-muted p-3 text-sm">
        <div>
          <dt className="text-xs app-muted">{language === "tr" ? "Adet" : "Quantity"}</dt>
          <dd className="font-semibold">{recommendation.quantity}</dd>
        </div>
        <div>
          <dt className="text-xs app-muted">{language === "tr" ? "Referans fiyat" : "Reference"}</dt>
          <dd className="font-semibold">{money.format(recommendation.reference_price)}</dd>
        </div>
        <div>
          <dt className="text-xs app-muted">{language === "tr" ? "Tahmini tutar" : "Estimated"}</dt>
          <dd className="font-semibold">{money.format(recommendation.estimated_amount)}</dd>
        </div>
      </dl>

      <ul className="mt-3 space-y-1 text-sm app-muted">
        {recommendation.rationale.map((madde) => (
          <li key={madde} className="flex gap-2">
            <span aria-hidden="true">•</span>
            <span>{madde}</span>
          </li>
        ))}
      </ul>

      <p className="mt-3 text-xs app-muted">{recommendation.risk_note}</p>

      <details className="mt-3">
        <summary
          className="cursor-pointer text-xs font-semibold text-emerald-700 dark:text-emerald-400"
          onClick={() => setNedenAcik((v) => !v)}
        >
          {language === "tr" ? "Neden bana geldi?" : "Why did I get this?"}
        </summary>
        <div className="mt-2 space-y-1 text-xs app-muted">
          {Object.entries(recommendation.personalization).map(([anahtar, deger]) => (
            <p key={anahtar}>
              <span className="font-medium">{anahtar}:</span> {String(deger)}
            </p>
          ))}
          <p className="pt-1 font-medium">{language === "tr" ? "Kaynaklar" : "Sources"}</p>
          {recommendation.sources.map((kaynak) => (
            <p key={kaynak.label}>— {kaynak.label}</p>
          ))}
        </div>
      </details>

      <p className="mt-3 rounded-md app-card-muted p-2 text-xs app-muted">
        {recommendation.disclaimer}
      </p>

      <footer className="mt-3 flex items-center justify-between gap-3">
        <span className="text-xs app-muted">
          {acik ? kalan : recommendation.status}
          {recommendation.order_id ? ` · #${recommendation.order_id}` : ""}
        </span>
        {acik && !suresiDoldu && (
          <div className="flex items-center gap-2">
            <input
              className="h-9 w-24 rounded-md border app-input px-2 text-sm outline-none"
              type="number"
              min="0.000001"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              aria-label={language === "tr" ? "Adet" : "Quantity"}
            />
            <Button
              className="!h-9 !bg-rose-600 hover:!bg-rose-700"
              disabled={submitting}
              onClick={() => setRejecting((v) => !v)}
            >
              {language === "tr" ? "Reddet" : "Reject"}
            </Button>
            <Button
              className="!h-9 !bg-emerald-600 hover:!bg-emerald-700"
              disabled={submitting || !gecerliAdet}
              onClick={() => onApprove(recommendation.id, parsed)}
            >
              {language === "tr" ? "Onayla" : "Approve"}
            </Button>
          </div>
        )}
      </footer>

      {rejecting && (
        <div className="mt-3 rounded-lg border app-border p-3">
          <p className="text-xs font-semibold app-heading">
            {language === "tr" ? "Ret gerekçesi" : "Rejection reason"}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {RET_GEREKCELERI.map((gerekce) => (
              <button
                key={gerekce.value}
                type="button"
                disabled={submitting}
                className="rounded-full border app-border px-3 py-1 text-xs disabled:opacity-50"
                onClick={() => {
                  setRejecting(false);
                  onReject(recommendation.id, gerekce.value);
                }}
              >
                {language === "tr" ? gerekce.tr : gerekce.en}
              </button>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}
