import type { AppLanguage } from "../contexts/LanguageContext";

type MessagePair = { tr: string; en: string };

const TRADING_ERRORS: Array<{ includes: string; message: MessagePair }> = [
  {
    includes: "bekleyen emirler dusuldugunde satilabilir hisse adedi yetersiz",
    message: {
      tr: "Bekleyen emirler düşüldüğünde satılabilir hisse adedi yetersiz.",
      en: "There are not enough shares available to sell after pending orders are deducted.",
    },
  },
  {
    includes: "fiyat tamponu dahil bu alim emri icin kullanilabilir sanal bakiye yetersiz",
    message: {
      tr: "Fiyat tamponu dâhil bu alım emri için kullanılabilir sanal bakiye yetersiz.",
      en: "The available virtual balance is insufficient for this buy order, including the price buffer.",
    },
  },
  {
    includes: "fiyat tamponu dahil bu alim emri icin sanal bakiye yetersiz",
    message: {
      tr: "Fiyat tamponu dâhil bu alım emri için sanal bakiye yetersiz.",
      en: "The virtual balance is insufficient for this buy order, including the price buffer.",
    },
  },
  {
    includes: "yeni fiyatta kullanilabilir bakiye yetersiz",
    message: {
      tr: "Yeni gerçekleşme fiyatında kullanılabilir bakiye yetersiz.",
      en: "The available balance is insufficient at the new fill price.",
    },
  },
  {
    includes: "gerceklesme aninda satilabilir adet yetersiz",
    message: {
      tr: "Gerçekleşme anında satılabilir varlık adedi yetersiz.",
      en: "There are not enough units available to sell at execution time.",
    },
  },
  {
    includes: "endeksler dogrudan alinip satilamaz",
    message: {
      tr: "Endeksler doğrudan alınıp satılamaz.",
      en: "Indices cannot be traded directly.",
    },
  },
  {
    includes: "hisse ve etf emirleri tam adet olmalidir",
    message: {
      tr: "Hisse ve ETF emirleri tam adet olmalıdır.",
      en: "Stock and ETF orders must be whole units.",
    },
  },
  {
    includes: "emir adedi sifirdan buyuk olmalidir",
    message: {
      tr: "Emir adedi sıfırdan büyük olmalıdır.",
      en: "Order quantity must be greater than zero.",
    },
  },
  {
    includes: "islem yonu buy veya sell olmalidir",
    message: {
      tr: "İşlem yönü AL veya SAT olmalıdır.",
      en: "Order side must be BUY or SELL.",
    },
  },
  {
    includes: "gecerli bir fiyat bulunamadi",
    message: {
      tr: "Varlık için geçerli bir fiyat bulunamadı.",
      en: "No valid price was found for the asset.",
    },
  },
  {
    includes: "paper trading hesabi bulunamadi",
    message: {
      tr: "Sanal işlem hesabı bulunamadı.",
      en: "The virtual trading account could not be found.",
    },
  },
  {
    includes: "hissesi bulunamadi",
    message: {
      tr: "Seçilen varlık bulunamadı.",
      en: "The selected asset could not be found.",
    },
  },
  {
    includes: "api istegi basarisiz oldu",
    message: {
      tr: "İşlem isteği tamamlanamadı.",
      en: "The trading request could not be completed.",
    },
  },
  {
    includes: "emir onizlenemedi",
    message: {
      tr: "Emir önizlenemedi.",
      en: "The order could not be previewed.",
    },
  },
  {
    includes: "emir olusturulamadi",
    message: {
      tr: "Emir oluşturulamadı.",
      en: "The order could not be created.",
    },
  },
  {
    includes: "limit fiyati sifirdan buyuk olmalidir",
    message: {
      tr: "Limit fiyatı sıfırdan büyük olmalıdır.",
      en: "The limit price must be greater than zero.",
    },
  },
  {
    includes: "stop-loss fiyati alim referans fiyatindan dusuk olmalidir",
    message: {
      tr: "Stop-loss fiyatı alım referans fiyatından düşük olmalıdır.",
      en: "The stop-loss price must be below the buy reference price.",
    },
  },
  {
    includes: "stop-loss yalnizca alim emrine eklenebilir",
    message: {
      tr: "Stop-loss yalnızca alım emrine eklenebilir.",
      en: "A stop-loss can only be attached to a buy order.",
    },
  },
  {
    includes: "yalnizca bekleyen emirler iptal edilebilir",
    message: {
      tr: "Yalnızca bekleyen emirler iptal edilebilir.",
      en: "Only pending orders can be cancelled.",
    },
  },
  {
    includes: "emir bulunamadi",
    message: {
      tr: "Emir bulunamadı.",
      en: "The order could not be found.",
    },
  },
  {
    includes: "emir iptal edilemedi",
    message: {
      tr: "Emir iptal edilemedi.",
      en: "The order could not be cancelled.",
    },
  },
];

function normalizeMessage(message: string): string {
  return message
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("ı", "i")
    .toLocaleLowerCase("en-US");
}

export function localizeTradingMessage(message: string, language: AppLanguage): string {
  const normalized = normalizeMessage(message);
  const match = TRADING_ERRORS.find((item) => normalized.includes(item.includes));
  return match?.message[language] ?? message;
}
