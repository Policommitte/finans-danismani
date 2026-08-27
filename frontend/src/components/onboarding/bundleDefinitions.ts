import type { RiskTier } from "../../models/auth";

/**
 * v1: statik risk-seviyesi -> sembol eslemesi. Gercek varliklar tablosundan
 * secilmis GERCEK semboller (uydurma ticker yok), ancak eslesme kendisi
 * statiktir - gelecekte portfoy/piyasa verisine gore dinamik bir oneri
 * motoruyla degistirilmesi planlaniyor.
 *
 * TR10Y bilincli olarak DISLANDI: paylasilan veritabanindan zaten silindi
 * (canli Yahoo fiyati yok, bkz. db/v5_schema_and_data.sql yorumu). Burada
 * secilen her sembol backend/app/market/yahoo.py -> YAHOO_TICKERS'da var,
 * yani her zaman canli fiyati olur.
 */
export const BUNDLE_DEFINITIONS: Record<
  RiskTier,
  { title: string; description: string; symbols: string[] }
> = {
  LOW: {
    title: "Temkinli Başlangıç",
    description: "Değerli metal ve döviz ağırlıklı, düşük oynaklıklı bir sepet.",
    symbols: ["GRAM_ALTIN", "GUMUS", "USD/TRY", "EUR/TRY"],
  },
  MEDIUM: {
    title: "Dengeli Büyüme",
    description: "BIST'in köklü isimleri ile bir ABD hissesini dengeleyen orta riskli bir sepet.",
    symbols: ["THYAO", "GARAN", "TCELL", "EREGL", "AAPL"],
  },
  HIGH: {
    title: "Atılımcı Portföy",
    description: "Kripto ve yüksek oynaklıklı hisselerden oluşan büyüme odaklı bir sepet.",
    symbols: ["BTC", "ETH", "SOL", "TSLA", "NVDA", "SASA", "ASELS"],
  },
};
