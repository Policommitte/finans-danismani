"use client";

import { useState } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import type { TradeProposal } from "../../models/chat";
import { createPaperOrder, previewPaperOrder } from "../../services/tradingService";
import { invalidQuantityMessage, isValidQuantity, quantityStep } from "../../utils/assetQuantity";

const COPY = {
  tr: {
    buy: "AL",
    sell: "SAT",
    quantity: "Adet",
    unitPrice: "Birim fiyat",
    commission: "Komisyon",
    total: "Toplam",
    afterTrade: "İşlem sonrası nakit",
    holding: "Portföydeki adet",
    confirm: "Onayla",
    edit: "Düzenle",
    cancel: "İptal",
    apply: "Güncelle",
    back: "Vazgeç",
    submitting: "Emir gönderiliyor…",
    previewing: "Yeniden hesaplanıyor…",
    done: (side: string) => `${side} emri oluşturuldu`,
    cancelled: "Emir iptal edildi",
    failed: "Emir oluşturulamadı.",
    previewFailed: "Yeni adet için hesap yapılamadı.",
    quantityLabel: "Yeni adet",
    disclaimer: "Bu bir yatırım tavsiyesi değildir; emir sanal portföyünde gerçekleşir.",
  },
  en: {
    buy: "BUY",
    sell: "SELL",
    quantity: "Quantity",
    unitPrice: "Unit price",
    commission: "Commission",
    total: "Total",
    afterTrade: "Cash after trade",
    holding: "Units held",
    confirm: "Confirm",
    edit: "Edit",
    cancel: "Cancel",
    apply: "Update",
    back: "Discard",
    submitting: "Placing order…",
    previewing: "Recalculating…",
    done: (side: string) => `${side} order created`,
    cancelled: "Order cancelled",
    failed: "The order could not be created.",
    previewFailed: "Could not recalculate for the new quantity.",
    quantityLabel: "New quantity",
    disclaimer: "This is not investment advice; the order runs in your virtual portfolio.",
  },
} as const;

function formatTry(value: number, locale: "tr-TR" | "en-US"): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatQuantity(value: number, locale: "tr-TR" | "en-US"): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 8 }).format(value);
}

/**
 * Sohbet balonu icinde gosterilen emir onay karti (TC-020 / US14).
 *
 * ⚠️ RAKAMLARI KENDI HESAPLAMAZ. Fiyat, komisyon, toplam ve kullanilabilir
 * bakiye backend onizlemesinden gelir; "Duzenle" ile adet degistirildiginde
 * de YENIDEN ONIZLEME alinir. Boylece kullanicinin onayladigi tutar ile
 * emrin gercek maliyeti ayrisamaz.
 *
 * Onay TEK TIKTIR ama emir yine de iki asamalidir: kart zaten onizlenmis
 * (dogrulanmis) bir emri gosterir, "Onayla" yalnizca onu isler.
 */
export function TradeProposalCard({
  proposal,
  onUpdate,
}: {
  proposal: TradeProposal;
  /** Adet degistiginde guncel oneriyi mesaja geri yazar (kalicilik icin). */
  onUpdate?: (next: TradeProposal) => void;
}) {
  const { language } = useLanguage();
  const copy = COPY[language] ?? COPY.tr;
  const locale = language === "tr" ? "tr-TR" : "en-US";

  const [state, setState] = useState<"idle" | "editing" | "previewing" | "submitting" | "done" | "cancelled">("idle");
  const [error, setError] = useState<string | null>(null);
  const [draftQuantity, setDraftQuantity] = useState(String(proposal.preview.quantity));

  const { preview, assetClass } = proposal;
  const sideLabel = preview.side === "BUY" ? copy.buy : copy.sell;
  const isBuy = preview.side === "BUY";
  const afterTrade = isBuy
    ? preview.available_balance - preview.estimated_total
    : preview.available_balance + preview.estimated_total;

  async function applyQuantity() {
    const parsed = Number(draftQuantity.replace(",", "."));
    if (!isValidQuantity(parsed, assetClass)) {
      setError(invalidQuantityMessage(assetClass, language));
      return;
    }

    setState("previewing");
    setError(null);
    try {
      const next = await previewPaperOrder(
        preview.symbol,
        preview.side,
        parsed,
        "MARKET",
        null,
        "GTC",
        null,
      );
      onUpdate?.({ preview: next, assetClass });
      setState("idle");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : copy.previewFailed);
      setState("editing");
    }
  }

  async function confirm() {
    setState("submitting");
    setError(null);
    try {
      await createPaperOrder(
        preview.symbol,
        preview.side,
        preview.quantity,
        crypto.randomUUID(),
        "MARKET",
        null,
        "GTC",
        null,
      );
      setState("done");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : copy.failed);
      setState("idle");
    }
  }

  const rows: Array<[string, string]> = [
    [copy.quantity, formatQuantity(preview.quantity, locale)],
    [copy.unitPrice, formatTry(preview.quoted_price, locale)],
    [copy.commission, formatTry(preview.estimated_commission, locale)],
    [copy.total, formatTry(preview.estimated_total, locale)],
    [copy.afterTrade, formatTry(afterTrade, locale)],
  ];
  if (!isBuy) {
    rows.splice(1, 0, [copy.holding, formatQuantity(preview.holding_quantity, locale)]);
  }

  return (
    <div className="mt-2 rounded-xl border app-border app-surface p-3 text-xs">
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
            isBuy ? "bg-emerald-500/15 text-emerald-600" : "bg-rose-500/15 text-rose-600"
          }`}
        >
          {sideLabel}
        </span>
        <span className="font-semibold app-heading">{preview.asset_name}</span>
        <span className="app-muted">{preview.symbol}</span>
      </div>

      <dl className="space-y-1">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3">
            <dt className="app-muted">{label}</dt>
            <dd className="font-medium app-heading">{value}</dd>
          </div>
        ))}
      </dl>

      {state === "editing" && (
        <div className="mt-2 flex items-center gap-2">
          <label className="sr-only" htmlFor={`adet-${preview.symbol}`}>
            {copy.quantityLabel}
          </label>
          <input
            id={`adet-${preview.symbol}`}
            type="number"
            min="0"
            step={quantityStep(assetClass) === "any" ? "any" : quantityStep(assetClass)}
            value={draftQuantity}
            onChange={(event) => setDraftQuantity(event.target.value)}
            className="w-24 rounded-lg border app-border app-card px-2 py-1 text-xs app-heading"
          />
          <button
            type="button"
            onClick={() => void applyQuantity()}
            className="rounded-lg app-primary px-3 py-1 text-xs font-semibold"
          >
            {copy.apply}
          </button>
          <button
            type="button"
            onClick={() => {
              setDraftQuantity(String(preview.quantity));
              setError(null);
              setState("idle");
            }}
            className="rounded-lg border app-border px-3 py-1 text-xs font-semibold app-muted"
          >
            {copy.back}
          </button>
        </div>
      )}

      {error && <p className="mt-2 text-[11px] app-danger">{error}</p>}

      {state === "done" ? (
        <p className="mt-2 text-[11px] font-semibold app-success">{copy.done(sideLabel)}</p>
      ) : state === "cancelled" ? (
        <p className="mt-2 text-[11px] app-muted">{copy.cancelled}</p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={state === "submitting" || state === "previewing" || state === "editing"}
              onClick={() => void confirm()}
              className="rounded-lg app-primary px-3 py-1.5 text-xs font-semibold disabled:opacity-60"
            >
              {state === "submitting" ? copy.submitting : copy.confirm}
            </button>
            <button
              type="button"
              disabled={state === "submitting" || state === "previewing"}
              onClick={() => setState(state === "editing" ? "idle" : "editing")}
              className="rounded-lg border app-border px-3 py-1.5 text-xs font-semibold app-muted disabled:opacity-60"
            >
              {state === "previewing" ? copy.previewing : copy.edit}
            </button>
            <button
              type="button"
              disabled={state === "submitting" || state === "previewing"}
              onClick={() => setState("cancelled")}
              className="rounded-lg border app-border px-3 py-1.5 text-xs font-semibold app-muted disabled:opacity-60"
            >
              {copy.cancel}
            </button>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed app-muted">{copy.disclaimer}</p>
        </>
      )}
    </div>
  );
}
