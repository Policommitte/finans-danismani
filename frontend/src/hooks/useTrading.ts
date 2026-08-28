"use client";

import { useCallback, useEffect, useState } from "react";
import type { EntryOrderType, OrderPreview, OrderSide, OrderValidity } from "../models/trading";
import {
  cancelPaperOrder,
  createPaperOrder,
  getPaperOrders,
  getTradingAccount,
  previewPaperOrder,
} from "../services/tradingService";
import { getPortfolioHoldings } from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";
import { useLanguage } from "../contexts/LanguageContext";
import { localizeTradingMessage } from "../utils/tradingMessages";

export function useTrading() {
  const { language } = useLanguage();
  // Portfoy de AYNI turda cekilir: bir alim gerceklestikten sonra satis
  // listesinin yeni pozisyonu gormesi icin ayri bir tazeleme beklenmemeli.
  const loader = useCallback(async () => {
    const [account, orders, holdings] = await Promise.all([
      getTradingAccount(),
      getPaperOrders(),
      getPortfolioHoldings(),
    ]);
    return { account, orders, holdings };
  }, []);
  const state = useAsyncData(loader, [loader]);
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => void state.refresh(), 15_000);
    return () => window.clearInterval(timer);
  }, [state.refresh]);

  const requestPreview = useCallback(async (
    symbol: string,
    side: OrderSide,
    quantity: number,
    orderType: EntryOrderType,
    limitPrice: number | null,
    validity: OrderValidity,
    stopLossPrice: number | null,
  ) => {
    setSubmitting(true);
    setActionError(null);
    setNotice(null);
    try {
      const result = await previewPaperOrder(symbol, side, quantity, orderType, limitPrice, validity, stopLossPrice);
      setPreview(result);
      return result;
    } catch (error) {
      setPreview(null);
      setActionError(error instanceof Error ? error.message : "Emir önizlenemedi.");
      return null;
    } finally {
      setSubmitting(false);
    }
  }, []);

  const confirmOrder = useCallback(async () => {
    if (!preview) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await createPaperOrder(
        preview.symbol,
        preview.side,
        preview.quantity,
        crypto.randomUUID(),
        preview.order_type,
        preview.limit_price,
        preview.validity,
        preview.stop_loss_price,
      );
      setNotice(preview.order_type === "LIMIT"
        ? language === "tr"
          ? "Limit emir alındı; fiyat koşulu sağlandığında değerlendirilecek."
          : "Limit order received; it will be evaluated when the price condition is met."
        : language === "tr"
          ? "Emir alındı; bir sonraki doğrulanmış fiyat güncellemesinde değerlendirilecek."
          : "Order received; it will be evaluated at the next verified price update.");
      setPreview(null);
      await state.refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Emir oluşturulamadı.");
    } finally {
      setSubmitting(false);
    }
  }, [language, preview, state.refresh]);

  const cancelOrder = useCallback(async (orderId: number) => {
    setSubmitting(true);
    setActionError(null);
    setNotice(null);
    try {
      await cancelPaperOrder(orderId);
      setNotice(language === "tr" ? "Bekleyen emir iptal edildi." : "The pending order was cancelled.");
      await state.refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Emir iptal edilemedi.");
    } finally {
      setSubmitting(false);
    }
  }, [language, state.refresh]);

  const clearPreview = useCallback(() => setPreview(null), []);

  return {
    ...state,
    preview,
    submitting,
    error: state.error ? localizeTradingMessage(state.error, language) : null,
    actionError: actionError ? localizeTradingMessage(actionError, language) : null,
    notice,
    requestPreview,
    confirmOrder,
    cancelOrder,
    clearPreview,
  };
}
