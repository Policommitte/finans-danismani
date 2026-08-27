"use client";

import { useEffect, useMemo, useState } from "react";
import type { Asset } from "../../models/market";
import type {
  OrderPreview,
  OrderSide,
  EntryOrderType,
  OrderValidity,
  TradingAccount,
} from "../../models/trading";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";

const ASSET_CLASS_LABELS: Record<string, { tr: string; en: string }> = {
  STOCK: { tr: "Hisse", en: "Stock" },
  USA_STOCK: { tr: "ABD hissesi", en: "US stock" },
  EU_STOCK: { tr: "Avrupa hissesi", en: "European stock" },
  CRYPTO: { tr: "Kripto", en: "Crypto" },
  FOREX: { tr: "Döviz", en: "Forex" },
  GOLD: { tr: "Altın", en: "Gold" },
  INDEX: { tr: "Endeks", en: "Index" },
};

function formatAssetPrice(asset: Asset, locale: string) {
  const precision = asset.asset_class === "FOREX" ? 4 : 2;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: asset.currency,
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(asset.current_price);
}

type Props = {
  asset: Asset;
  assets: Asset[];
  account: TradingAccount | null;
  preview: OrderPreview | null;
  submitting: boolean;
  error: string | null;
  notice: string | null;
  onSelectAsset: (symbol: string) => void;
  onPreview: (
    symbol: string,
    side: OrderSide,
    quantity: number,
    orderType: EntryOrderType,
    limitPrice: number | null,
    validity: OrderValidity,
    stopLossPrice: number | null,
  ) => void;
  onConfirm: () => void;
  onClearPreview: () => void;
};

export function TradeTicket({
  asset,
  assets,
  account,
  preview,
  submitting,
  error,
  notice,
  onSelectAsset,
  onPreview,
  onConfirm,
  onClearPreview,
}: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const money = new Intl.NumberFormat(locale, { style: "currency", currency: "TRY" });
  const [assetClass, setAssetClass] = useState(asset.asset_class);
  const [side, setSide] = useState<OrderSide>("BUY");
  const [quantity, setQuantity] = useState("1");
  const [orderType, setOrderType] = useState<EntryOrderType>("MARKET");
  const [limitPrice, setLimitPrice] = useState("");
  const [stopLossEnabled, setStopLossEnabled] = useState(false);
  const [stopLossPrice, setStopLossPrice] = useState("");
  const [validity, setValidity] = useState<OrderValidity>("DAY");
  const classes = useMemo(
    () => Array.from(new Set(assets.map((item) => item.asset_class))),
    [assets],
  );
  const classAssets = useMemo(
    () => assets.filter((item) => item.asset_class === assetClass),
    [assetClass, assets],
  );
  const supported = asset.asset_class !== "INDEX";

  useEffect(() => {
    setAssetClass(asset.asset_class);
    onClearPreview();
    setQuantity("1");
    setLimitPrice("");
    setStopLossEnabled(false);
    setStopLossPrice("");
  }, [asset.asset_class, asset.symbol, onClearPreview]);

  function selectClass(nextClass: string) {
    setAssetClass(nextClass);
    onClearPreview();
    const firstAsset = assets.find((item) => item.asset_class === nextClass);
    if (firstAsset) {
      onSelectAsset(firstAsset.symbol);
    }
  }

  function selectSide(next: OrderSide) {
    setSide(next);
    onClearPreview();
    if (next === "SELL") setStopLossEnabled(false);
  }

  function changeQuantity(value: string) {
    setQuantity(value);
    onClearPreview();
  }

  function selectOrderType(next: EntryOrderType) {
    setOrderType(next);
    onClearPreview();
  }

  function changeLimitPrice(value: string) {
    setLimitPrice(value);
    onClearPreview();
  }

  function selectValidity(value: OrderValidity) {
    setValidity(value);
    onClearPreview();
  }

  const parsedQuantity = Number(quantity);
  const parsedLimitPrice = Number(limitPrice);
  const parsedStopLossPrice = Number(stopLossPrice);
  const validLimitPrice = orderType === "MARKET"
    || (Number.isFinite(parsedLimitPrice) && parsedLimitPrice > 0);
  const validStopLoss = !stopLossEnabled || (
    Number.isFinite(parsedStopLossPrice)
    && parsedStopLossPrice > 0
    && (orderType !== "LIMIT" || parsedStopLossPrice < parsedLimitPrice)
  );

  return (
    <Card title={language === "tr" ? "Manuel Sanal İşlem Emri" : "Manual Virtual Trade Order"} className="!border-0 !p-0 !shadow-none">
      <p className="-mt-3 mb-5 text-sm app-muted">
        {language === "tr"
          ? "Varlık sınıfını ve ürünü seç, emri TRY likit hesabından oluştur."
          : "Select an asset class and product, then create the order from the TRY cash account."}
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-xs font-semibold uppercase tracking-wide app-muted">
          {language === "tr" ? "Varlık sınıfı" : "Asset class"}
          <select
            className="mt-2 h-12 w-full rounded-xl border app-input px-4 text-sm font-medium outline-none focus:border-emerald-500"
            value={assetClass}
            onChange={(event) => selectClass(event.target.value)}
          >
            {classes.map((item) => (
              <option key={item} value={item}>{ASSET_CLASS_LABELS[item]?.[language] ?? item.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>

        <label className="block text-xs font-semibold uppercase tracking-wide app-muted">
          {language === "tr" ? "Varlık" : "Asset"}
          <select
            className="mt-2 h-12 w-full rounded-xl border app-input px-4 text-sm font-medium outline-none focus:border-emerald-500"
            value={asset.symbol}
            onChange={(event) => onSelectAsset(event.target.value)}
          >
            {classAssets.map((item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol + " — " + formatAssetPrice(item, locale)}
              </option>
            ))}
          </select>
          <span className="mt-2 block text-xs font-normal normal-case tracking-normal app-muted">
            {language === "tr" ? "✓ Son doğrulanmış piyasa fiyatı" : "✓ Latest verified market price"}
          </span>
        </label>
      </div>

      <div className="mt-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-lg font-semibold app-heading">{asset.symbol}</p>
          <p className="text-sm app-muted">{asset.name}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold app-heading">{formatAssetPrice(asset, locale)}</p>
          <p className="text-xs app-muted">{language === "tr" ? "Son doğrulanmış fiyat" : "Latest verified price"}</p>
        </div>
      </div>

      <div className="mt-4 rounded-lg app-card-muted p-3 text-sm">
        {account && account.reserved_balance > 0 ? (
          <>
            <div className="flex justify-between gap-4 border-b app-border pb-2">
              <span className="app-muted">{language === "tr" ? "Toplam likit para (TRY)" : "Total liquid cash (TRY)"}</span>
              <strong>{money.format(account.available_balance + account.reserved_balance)}</strong>
            </div>
            <div className="mt-2 flex justify-between gap-4">
              <span className="app-muted">{language === "tr" ? "Kullanılabilir" : "Available"}</span>
              <strong>{money.format(account.available_balance)}</strong>
            </div>
            <div className="mt-1 flex justify-between gap-4">
              <span className="app-muted">{language === "tr" ? "Emirlerde bloke" : "Reserved for orders"}</span>
              <strong>{money.format(account.reserved_balance)}</strong>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="app-muted">{language === "tr" ? "Kullanılabilir sanal bakiye" : "Available virtual balance"}</p>
              <p className="mt-1 text-xs app-muted">{language === "tr" ? "Aktif emirlerde bloke edilmiş tutar yok." : "No funds are reserved for active orders."}</p>
            </div>
            <strong className="text-base">{account ? money.format(account.available_balance) : "—"}</strong>
          </div>
        )}
        <p className="mt-2 text-xs app-muted">
          {language === "tr"
            ? "Bu tutarlar sanal işlem nakit hesabından alınır; gerçek banka bakiyesi değildir."
            : "These amounts come from the virtual trading cash account; they are not a real bank balance."}
        </p>
      </div>

      {!supported ? (
        <p className="mt-4 rounded-lg app-card-muted p-3 text-sm app-muted">
          {language === "tr" ? "Endeksler doğrudan alınıp satılamaz; izleme amacıyla listelenir." : "Indices cannot be traded directly and are listed for tracking only."}
        </p>
      ) : (
        <>
          <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl app-card-muted p-1">
            <button
              type="button"
              className={`rounded-md px-3 py-2 text-sm font-semibold transition ${side === "BUY" ? "bg-emerald-600 text-white" : "app-muted"}`}
              onClick={() => selectSide("BUY")}
            >
              {language === "tr" ? "AL" : "BUY"}
            </button>
            <button
              type="button"
              className={`rounded-md px-3 py-2 text-sm font-semibold transition ${side === "SELL" ? "bg-rose-600 text-white" : "app-muted"}`}
              onClick={() => selectSide("SELL")}
            >
              {language === "tr" ? "SAT" : "SELL"}
            </button>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="block text-xs font-semibold uppercase tracking-wide app-muted">
            {language === "tr" ? "Miktar / Adet" : "Quantity / Units"}
            <input
              className="mt-2 w-full rounded-md border app-input px-3 py-2.5 text-sm outline-none"
              type="number"
              min="0.000001"
              step="1"
              value={quantity}
              onChange={(event) => changeQuantity(event.target.value)}
            />
          </label>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide app-muted">{language === "tr" ? "Emir tipi" : "Order type"}</p>
            <div className="mt-2 grid h-12 grid-cols-2 gap-1 rounded-xl app-card-muted p-1">
              <button
                type="button"
                onClick={() => selectOrderType("MARKET")}
                className={`rounded-lg text-sm font-semibold ${orderType === "MARKET" ? "bg-[#454466] text-white" : "app-muted"}`}
              >
                {language === "tr" ? "Piyasa" : "Market"}
              </button>
              <button
                type="button"
                onClick={() => selectOrderType("LIMIT")}
                className={`rounded-lg text-sm font-semibold ${orderType === "LIMIT" ? "bg-[#454466] text-white" : "app-muted"}`}
              >
                {language === "tr" ? "Limit" : "Limit"}
              </button>
            </div>
          </div>
          </div>

          {orderType === "LIMIT" && (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="block text-xs font-semibold uppercase tracking-wide app-muted">
                {language === "tr" ? "Limit fiyatı (TRY)" : "Limit price (TRY)"}
                <input
                  className="mt-2 w-full rounded-md border app-input px-3 py-2.5 text-sm outline-none"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={limitPrice}
                  onChange={(event) => changeLimitPrice(event.target.value)}
                  placeholder={language === "tr" ? "Örn. 295,00" : "e.g. 295.00"}
                />
                <span className="mt-1.5 block text-xs font-normal normal-case tracking-normal app-muted">
                  {side === "BUY"
                    ? (language === "tr" ? "Bu fiyat veya daha düşük bir fiyat beklenir." : "Waits for this price or lower.")
                    : (language === "tr" ? "Bu fiyat veya daha yüksek bir fiyat beklenir." : "Waits for this price or higher.")}
                </span>
              </label>

              <label className="block text-xs font-semibold uppercase tracking-wide app-muted">
                {language === "tr" ? "Geçerlilik" : "Validity"}
                <select
                  className="mt-2 h-11 w-full rounded-md border app-input px-3 text-sm outline-none"
                  value={validity}
                  onChange={(event) => selectValidity(event.target.value as OrderValidity)}
                >
                  <option value="DAY">{language === "tr" ? "Gün sonu" : "Day"}</option>
                  <option value="GTC">{language === "tr" ? "İptale kadar" : "Good till cancelled"}</option>
                </select>
              </label>
            </div>
          )}

          {side === "BUY" && (
            <div className="mt-4 rounded-xl border app-border p-4">
              <label className="flex cursor-pointer items-center gap-3 text-sm font-semibold app-heading">
                <input
                  type="checkbox"
                  checked={stopLossEnabled}
                  onChange={(event) => {
                    setStopLossEnabled(event.target.checked);
                    onClearPreview();
                  }}
                  className="h-4 w-4 accent-emerald-600"
                />
                {language === "tr" ? "Koruyucu stop-loss ekle" : "Add protective stop-loss"}
              </label>
              {stopLossEnabled && (
                <label className="mt-3 block text-xs font-semibold uppercase tracking-wide app-muted">
                  {language === "tr" ? "Stop fiyatı (TRY)" : "Stop price (TRY)"}
                  <input
                    className="mt-2 w-full rounded-md border app-input px-3 py-2.5 text-sm outline-none"
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={stopLossPrice}
                    onChange={(event) => {
                      setStopLossPrice(event.target.value);
                      onClearPreview();
                    }}
                    placeholder={language === "tr" ? "Alım fiyatının altında" : "Below the entry price"}
                  />
                  <span className="mt-1.5 block text-xs font-normal normal-case tracking-normal app-muted">
                    {language === "tr"
                      ? "Alış gerçekleştikten sonra etkinleşir; doğrulanmış fiyat bu seviyeye indiğinde piyasa satışı oluşturur."
                      : "Activates after the buy fills and submits a market sell when the verified price reaches this level."}
                  </span>
                </label>
              )}
            </div>
          )}

          {preview && (
            <div className="mt-4 space-y-2 rounded-lg border app-border p-3 text-sm">
              <div className="flex justify-between"><span className="app-muted">{language === "tr" ? "Brüt tutar" : "Gross amount"}</span><span>{money.format(preview.gross_amount)}</span></div>
              <div className="flex justify-between"><span className="app-muted">{language === "tr" ? "Tahmini komisyon" : "Estimated commission"}</span><span>{money.format(preview.estimated_commission)}</span></div>
              <div className="flex justify-between border-t app-border pt-2 font-semibold"><span>{side === "BUY" ? (language === "tr" ? "Tahmini toplam" : "Estimated total") : (language === "tr" ? "Tahmini net gelir" : "Estimated net proceeds")}</span><span>{money.format(preview.estimated_total)}</span></div>
              {side === "BUY" && (
                <div className="flex justify-between text-xs"><span className="app-muted">{preview.order_type === "LIMIT" ? (language === "tr" ? "Limit tutarıyla bloke" : "Reserved at limit value") : (language === "tr" ? "%2 fiyat tamponuyla bloke" : "Reserved with a 2% price buffer")}</span><span>{money.format(preview.estimated_reserve)}</span></div>
              )}
              <p className="pt-1 text-xs app-muted">{language === "tr" ? preview.execution_note : preview.order_type === "LIMIT" ? "The order fills at the verified current price when the limit condition is met." : "The order fills at the next verified price update."}</p>
              {preview.stop_loss_price != null && (
                <div className="flex justify-between border-t app-border pt-2 text-xs">
                  <span className="app-muted">{language === "tr" ? "Bağlı stop-loss" : "Attached stop-loss"}</span>
                  <strong>{money.format(preview.stop_loss_price)}</strong>
                </div>
              )}
            </div>
          )}

          {error && <p className="mt-3 text-sm app-danger">{error}</p>}
          {notice && <p className="mt-3 text-sm app-success">{notice}</p>}

          <div className="mt-4">
            {preview ? (
              <Button
                className={`h-12 w-full !rounded-xl text-base shadow-lg ${side === "BUY" ? "!bg-emerald-600 hover:!bg-emerald-700" : "!bg-rose-600 hover:!bg-rose-700"}`}
                disabled={submitting}
                onClick={onConfirm}
              >
                {submitting ? (language === "tr" ? "Gönderiliyor…" : "Submitting…") : (language === "tr" ? "Emri Onayla" : "Confirm Order")}
              </Button>
            ) : (
              <Button
                className={`h-12 w-full !rounded-xl text-base shadow-lg ${side === "BUY" ? "!bg-emerald-600 hover:!bg-emerald-700" : "!bg-rose-600 hover:!bg-rose-700"}`}
                disabled={submitting || !Number.isFinite(parsedQuantity) || parsedQuantity <= 0 || !validLimitPrice || !validStopLoss}
                onClick={() => onPreview(
                  asset.symbol,
                  side,
                  parsedQuantity,
                  orderType,
                  orderType === "LIMIT" ? parsedLimitPrice : null,
                  orderType === "LIMIT" ? validity : "GTC",
                  stopLossEnabled ? parsedStopLossPrice : null,
                )}
              >
                {submitting ? (language === "tr" ? "Hesaplanıyor…" : "Calculating…") : (language === "tr" ? "Emri Önizle" : "Preview Order")}
              </Button>
            )}
          </div>
        </>
      )}
    </Card>
  );
}
