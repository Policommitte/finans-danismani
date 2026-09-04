import { describe, expect, it } from "vitest";
import type { Asset } from "../models/market";
import { parseTradeIntent, resolveAssetFromText } from "./tradeIntent";

const KATALOG: Asset[] = [
  {
    symbol: "THYAO", name: "Türk Hava Yolları", asset_class: "STOCK", currency: "TRY",
    current_price: 302.25, daily_change_pct: 1, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "ASELS", name: "Aselsan", asset_class: "STOCK", currency: "TRY",
    current_price: 390.25, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "EREGL", name: "Erdemir", asset_class: "STOCK", currency: "TRY",
    current_price: 36.44, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "NVDA", name: "Nvidia", asset_class: "USA_STOCK", currency: "USD",
    current_price: 228.91, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "BTC", name: "Bitcoin", asset_class: "CRYPTO", currency: "USD",
    current_price: 78242, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "USD/TRY", name: "Amerikan Doları", asset_class: "FOREX", currency: "TRY",
    current_price: 48.24, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
  {
    symbol: "KO", name: "Coca-Cola Company", asset_class: "USA_STOCK", currency: "USD",
    current_price: 62.1, daily_change_pct: null, weekly_change_pct: null, yearly_change_pct: null,
  },
];

describe("parseTradeIntent - yon tespiti", () => {
  it.each([
    "THYAO al",
    "aselsan alalım",
    "5 lot ereğli alacağım",
    "bitcoin alıyorum",
    // ⚠️ EN KRITIK TUZAK: "satın al" icinde "sat" gecer ama SATIM DEGILDIR.
    "THYAO satın al",
    "aselsan satın alalım",
  ])("%s -> BUY", (metin) => {
    expect(parseTradeIntent(metin)?.side).toBe("BUY");
  });

  it.each(["THYAO sat", "aselsan satalım", "3 lot ereğli satacağım", "bitcoin satıyorum"])(
    "%s -> SELL",
    (metin) => {
      expect(parseTradeIntent(metin)?.side).toBe("SELL");
    },
  );
});

describe("parseTradeIntent - emir OLMAYAN cumleler", () => {
  it.each([
    // Tavsiye sorulari: kart cikarmak kullaniciyi isleme itmek olurdu.
    "THYAO alsam mı",
    "aselsan alınır mı",
    "bitcoin almalı mıyım",
    "şimdi satmalı mıyım",
    // Fiil hic yok
    "THYAO fiyatı ne kadar",
    "portföyüm nasıl gidiyor",
    "piyasada neler oluyor",
    // Ikisi birden: "al sat" bir emir degil, genel bir ifade
    "al sat sinyalleri nedir",
    // Soru kalibi: bilgi talebi, emir degil - normal sohbete gitmeli.
    "hisse alım maliyetim ne",
    "kaç lot THYAO alabilirim",
    "hangi hisseyi almalıyım",
    "nasıl altın alınır",
    "THYAO al?",
    "",
  ])("%s -> null", (metin) => {
    expect(parseTradeIntent(metin)).toBeNull();
  });

  it("gunluk kelimeler yanlislikla fiil sanilmaz", () => {
    // "altin", "analiz", "alan" kelimeleri "al" ile BASLAR ama fiil degildir.
    expect(parseTradeIntent("altın analizi yap")).toBeNull();
    expect(parseTradeIntent("bu alan ne anlama geliyor")).toBeNull();
  });
});

describe("parseTradeIntent - adet ve tutar", () => {
  it("acik adet okunur", () => {
    expect(parseTradeIntent("5 lot THYAO al")).toMatchObject({ quantity: 5, amountTry: null });
    expect(parseTradeIntent("3 adet aselsan al")).toMatchObject({ quantity: 3 });
    expect(parseTradeIntent("2,5 gram altın al")).toMatchObject({ quantity: 2.5 });
  });

  it("TL tutari okunur", () => {
    expect(parseTradeIntent("10 bin TL'lik THYAO al")).toMatchObject({
      quantity: null,
      amountTry: 10_000,
    });
    expect(parseTradeIntent("5000 TL değerinde bitcoin al")).toMatchObject({ amountTry: 5_000 });
  });

  it("adet varken sayi TUTAR sanilmaz", () => {
    // ⚠️ "5 lot" -> adet 5; 5 TL butce DEGIL.
    expect(parseTradeIntent("5 lot THYAO al")?.amountTry).toBeNull();
  });

  it("para birimi yoksa tutar okunmaz", () => {
    // Ciplak sayi bir butce degildir - kullanicinin ne demek istedigi belirsiz,
    // bu durumda nakde gore hesaplanan varsayilan adet kullanilir.
    expect(parseTradeIntent("THYAO 1000 al")?.amountTry).toBeNull();
  });
});

describe("resolveAssetFromText", () => {
  it.each([
    ["THYAO al", "THYAO"],
    ["thyao al", "THYAO"],
    ["aselsan al", "ASELS"],
    ["nvidia al", "NVDA"],
    ["bitcoin al", "BTC"],
    // Kod + Turkce ek: katalogdaki ad "Erdemir" ama kullanici "ereğli" der.
    ["ereğli al", "EREGL"],
    ["ereğliden 5 lot al", "EREGL"],
    // Ayirac karakterli kod, sikisik yazim
    ["usdtry al", "USD/TRY"],
    ["dolar al", "USD/TRY"],
  ])("%s -> %s", (metin, beklenen) => {
    expect(resolveAssetFromText(metin, KATALOG)?.symbol).toBe(beklenen);
  });

  it("katalogda olmayan varlik icin null doner", () => {
    expect(resolveAssetFromText("tesla al", KATALOG)).toBeNull();
    expect(resolveAssetFromText("bir seyler al", KATALOG)).toBeNull();
  });

  it("kisa kodlar yalnizca BUYUK HARFLE yazildiginda eslesir", () => {
    // "ko" gunluk bir hece; kucuk harfle sembol sayilmamali.
    expect(resolveAssetFromText("ko al", KATALOG)).toBeNull();
    expect(resolveAssetFromText("KO al", KATALOG)?.symbol).toBe("KO");
  });

  it("esit guclu iki eslesmede cumlede ONCE gecen kazanir", () => {
    // Ikisi de TAM kod eslesmesi (ayni puan) - siralamayi konum belirler.
    expect(resolveAssetFromText("thyao ve asels al", KATALOG)?.symbol).toBe("THYAO");
    expect(resolveAssetFromText("asels ve thyao al", KATALOG)?.symbol).toBe("ASELS");
  });

  it("TAM kod eslesmesi, ekli ad eslesmesini yener", () => {
    // "aselsan" ASELS'e EKLI eslesir (puan 2), "thyao" TAM eslesir (puan 3);
    // konumu sonra olsa bile tam eslesme kazanmali.
    expect(resolveAssetFromText("aselsan ve thyao al", KATALOG)?.symbol).toBe("THYAO");
  });
});
