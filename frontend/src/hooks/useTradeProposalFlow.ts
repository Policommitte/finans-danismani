"use client";

import { useCallback } from "react";
import type { AppLanguage } from "../contexts/LanguageContext";
import type { ChatMessage, TradeProposal } from "../models/chat";
import type { Asset } from "../models/market";
import type { OrderPreview } from "../models/trading";
import { getMarketAssets } from "../services/marketService";
import { getPortfolioHoldings } from "../services/portfolioService";
import { previewPaperOrder } from "../services/tradingService";
import { CEYREK_ADIM, isQuarterStep, isValidQuantity, quantityStep } from "../utils/assetQuantity";
import type { TradeSide } from "../utils/tradeIntent";
import { parseTradeIntent, resolveAssetFromText } from "../utils/tradeIntent";

const COPY = {
  tr: {
    thinking: "Emri hazırlıyorum…",
    assetNotFound: (side: string) =>
      `Hangi varlığı ${side} istediğini anlayamadım. Örnek: "5 lot THYAO ${side}".`,
    noCash: "Bu işlem için kullanılabilir nakit bakiyen yeterli değil.",
    noHolding: (symbol: string) => `Portföyünde satılacak ${symbol} pozisyonu bulunmuyor.`,
    tooMuch: (symbol: string, held: string) =>
      `Portföyünde yalnızca ${held} adet ${symbol} var; daha fazlasını satamazsın.`,
    invalidQuantity: "Bu varlık için geçersiz bir adet istedin.",
    failed: "Emir önerisi hazırlanamadı, lütfen tekrar dene.",
    buy: "al",
    sell: "sat",
    proposal: (side: string, quantity: string, symbol: string) =>
      `${quantity} adet ${symbol} ${side} emrini hazırladım. Onaylarsan işleme alırım.`,
  },
  en: {
    thinking: "Preparing the order…",
    assetNotFound: (side: string) =>
      `I could not tell which asset you want to ${side}. Example: "${side} 5 THYAO".`,
    noCash: "Your available cash balance is not enough for this trade.",
    noHolding: (symbol: string) => `You have no ${symbol} position to sell.`,
    tooMuch: (symbol: string, held: string) =>
      `You only hold ${held} units of ${symbol}; you cannot sell more.`,
    invalidQuantity: "That quantity is not valid for this asset.",
    failed: "The order proposal could not be prepared, please try again.",
    buy: "buy",
    sell: "sell",
    proposal: (side: string, quantity: string, symbol: string) =>
      `I prepared a ${side} order for ${quantity} ${symbol}. Confirm and I will place it.`,
  },
} as const;

/** Varlik sinifina gore adet asagi yuvarlanir (fazlasi bakiyeyi asardi). */
function floorToStep(quantity: number, assetClass: string): number {
  if (isQuarterStep(assetClass)) {
    return Math.floor(quantity / CEYREK_ADIM) * CEYREK_ADIM;
  }
  if (quantityStep(assetClass) === "any") {
    // Serbest ondalikli sinif (kripto): 6 basamak yeterli hassasiyet.
    return Math.floor(quantity * 1e6) / 1e6;
  }
  return Math.floor(quantity);
}

/**
 * Sohbetten AL/SAT emri onerme akisi (TC-020 / US14).
 *
 * ⚠️ HICBIR EMIR KENDILIGINDEN GONDERILMEZ. Bu akis yalnizca bir ONERI
 * KARTI uretir; emir ancak kullanici kartta "Onayla"ya bastiginda
 * (`TradeProposalCard`) olusur. Kart da rakamlari kendi hesaplamaz,
 * backend onizlemesini gosterir.
 *
 * Adet nasil belirlenir:
 *   1. Kullanici acikca yazdiysa ("5 lot")            -> o adet
 *   2. TL tutari yazdiysa ("10 bin TL'lik")           -> tutar / birim maliyet
 *   3. Hicbiri yoksa, ALIM  -> kullanilabilir nakdin tamami
 *                      SATIM -> portfoydeki tum pozisyon
 *
 * Birim maliyet SUNUCUDAN gelir (1 adetlik onizleme): boylece doviz kuru,
 * komisyon ve fiyat tamponu istemcide TEKRAR HESAPLANMAZ - varliklarin
 * `current_price` alani kendi para biriminde (USD gibi), nakit ise TL'dir.
 */
export function useTradeProposalFlow({
  language,
  appendLocalMessage,
  updateMessage,
}: {
  language: AppLanguage;
  appendLocalMessage: (message: Omit<ChatMessage, "id" | "local">) => string;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
}) {
  const copy = COPY[language] ?? COPY.tr;
  const locale = language === "tr" ? "tr-TR" : "en-US";

  /** Adet hesabi; hata durumunda kullaniciya gosterilecek METNI doner. */
  const adetBelirle = useCallback(
    async (
      intent: { side: TradeSide; quantity: number | null; amountTry: number | null },
      asset: Asset,
    ): Promise<number | string> => {
      if (intent.side === "SELL") {
        const holdings = await getPortfolioHoldings();
        const holding = holdings.items.find(
          (item) => item.symbol.toUpperCase() === asset.symbol.toUpperCase(),
        );
        if (!holding || holding.quantity <= 0) return copy.noHolding(asset.symbol);

        const istenen = intent.quantity ?? holding.quantity;
        if (istenen > holding.quantity) {
          return copy.tooMuch(
            asset.symbol,
            new Intl.NumberFormat(locale, { maximumFractionDigits: 8 }).format(holding.quantity),
          );
        }
        return isValidQuantity(istenen, asset.asset_class) ? istenen : copy.invalidQuantity;
      }

      if (intent.quantity !== null) {
        return isValidQuantity(intent.quantity, asset.asset_class)
          ? intent.quantity
          : copy.invalidQuantity;
      }

      // Adet verilmedi: kucuk bir SONDAJ onizlemesiyle birim maliyeti
      // sunucudan ogren, sonra butceye (ya da tum nakde) bol.
      //
      // ⚠️ SONDAJ ADEDI VARLIK SINIFINA GORE DEGISIR. Bolunebilen
      // varliklarda (kripto) 1 adetle sormak YANLIS "yetersiz bakiye"
      // uretirdi: 15.000 TL ile 1 BTC alinamaz ama 0,004 BTC alinabilir.
      // Tam adet alinan siniflarda ise 1 dogru sondajdir - 1 adedi
      // alamiyorsa gercekten alamaz.
      const sondajAdedi = quantityStep(asset.asset_class) === "any" ? 0.001 : 1;
      let birim: OrderPreview;
      try {
        birim = await previewPaperOrder(
          asset.symbol,
          "BUY",
          sondajAdedi,
          "MARKET",
          null,
          "GTC",
          null,
        );
      } catch {
        // Sondaj adedi bile alinamiyorsa backend "yetersiz bakiye" der.
        return copy.noCash;
      }

      const butce = intent.amountTry ?? birim.available_balance;
      // `estimated_reserve` fiyat tamponu + komisyonu ICERIR; emrin
      // gercekten gecmesi icin ayrilmasi gereken tutar budur. Sondaj
      // adedine bolunerek BIR adetin maliyetine cevrilir.
      const birimMaliyet = (birim.estimated_reserve || birim.estimated_total) / sondajAdedi;
      if (birimMaliyet <= 0) return copy.failed;

      const adet = floorToStep(butce / birimMaliyet, asset.asset_class);
      if (adet <= 0) return copy.noCash;
      return adet;
    },
    [copy, locale],
  );

  const hazirla = useCallback(
    async (text: string, messageId: string) => {
      const intent = parseTradeIntent(text);
      if (!intent) return;
      const sideWord = intent.side === "BUY" ? copy.buy : copy.sell;

      try {
        const assets = await getMarketAssets();
        const asset = resolveAssetFromText(text, assets.items);
        if (!asset) {
          updateMessage(messageId, { content: copy.assetNotFound(sideWord) });
          return;
        }

        const quantity = await adetBelirle(intent, asset);
        if (typeof quantity === "string") {
          updateMessage(messageId, { content: quantity });
          return;
        }

        const preview = await previewPaperOrder(
          asset.symbol,
          intent.side,
          quantity,
          "MARKET",
          null,
          "GTC",
          null,
        );
        const proposal: TradeProposal = { preview, assetClass: asset.asset_class };
        updateMessage(messageId, {
          content: copy.proposal(
            sideWord,
            new Intl.NumberFormat(locale, { maximumFractionDigits: 8 }).format(preview.quantity),
            asset.symbol,
          ),
          tradeProposal: proposal,
        });
      } catch (exc) {
        // Backend is kurali hatalari (yetersiz bakiye vb.) net Turkce mesaj
        // tasir - oldugu gibi gosterilir; digerleri genel mesaja duser.
        updateMessage(messageId, {
          content: exc instanceof Error && exc.message ? exc.message : copy.failed,
        });
      }
    },
    [adetBelirle, copy, locale, updateMessage],
  );

  /**
   * Mesaji yerel olarak isler. `true` donerse mesaj sohbet backend'ine
   * GONDERILMEZ (bkz. ChatWidget.sendMessage).
   */
  const handleUserMessage = useCallback(
    (text: string): boolean => {
      if (!parseTradeIntent(text)) return false;

      appendLocalMessage({ role: "user", content: text });
      const messageId = appendLocalMessage({ role: "assistant", content: copy.thinking });
      void hazirla(text, messageId);
      return true;
    },
    [appendLocalMessage, copy, hazirla],
  );

  /** Kartta adet degistiginde guncel oneriyi mesaja geri yazar. */
  const updateProposal = useCallback(
    (messageId: string, proposal: TradeProposal) => {
      updateMessage(messageId, { tradeProposal: proposal });
    },
    [updateMessage],
  );

  return { handleUserMessage, updateProposal };
}
