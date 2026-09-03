import type { AppLanguage } from "../../contexts/LanguageContext";
import type {
  ChatQuickReply,
  InvestmentGoal,
  InvestmentHorizon,
  InvestmentRiskProfile,
} from "../../models/chat";

/**
 * All user-facing text of the guided "I want to invest" flow, in both app
 * languages. Kept out of the hook so the conversation logic stays readable.
 */

export const START_INVESTMENT_FLOW_ID = "start-investment-flow";
export const CANCEL_FLOW_ID = "cancel-investment-flow";
export const RESTART_FLOW_ID = "restart-investment-flow";

type HorizonOption = { value: InvestmentHorizon; label: string; hint: string };
type RiskOption = { value: InvestmentRiskProfile; label: string; hint: string };
type GoalOption = { value: InvestmentGoal; label: string; hint: string };

export type InvestmentFlowCopy = {
  suggestionTitle: string;
  suggestions: ChatQuickReply[];
  startMessage: string;
  askBudget: string;
  budgetPresets: number[];
  budgetPlaceholder: string;
  budgetNotUnderstood: string;
  askHorizon: (budget: string) => string;
  horizonOptions: HorizonOption[];
  askRisk: string;
  riskOptions: RiskOption[];
  askGoal: string;
  goalOptions: GoalOption[];
  optionNotUnderstood: string;
  building: string;
  ready: (title: string) => string;
  failed: (reason: string) => string;
  cancelled: string;
  cancelLabel: string;
  restartLabel: string;
  purchased: (orderCount: number) => string;
  cancelKeywords: string[];
  inputPlaceholder: string;
};

const COPY: Record<AppLanguage, InvestmentFlowCopy> = {
  tr: {
    suggestionTitle: "Nasıl yardımcı olabilirim?",
    suggestions: [
      {
        id: START_INVESTMENT_FLOW_ID,
        label: "Yatırım yapmak istiyorum",
        hint: "Bütçenize uygun hazır paket",
        message: "Yatırım yapmak istiyorum",
      },
      {
        id: "ask-portfolio",
        label: "Portföyümü değerlendir",
        message: "Portföyümü değerlendirir misin?",
      },
      {
        id: "ask-market",
        label: "Piyasada neler oluyor?",
        message: "Bugün piyasada neler oluyor?",
      },
    ],
    startMessage:
      "Harika, birlikte size uygun bir yatırım paketi hazırlayalım! Birkaç kısa soruyla başlayalım.",
    askBudget:
      "Öncelikle ne kadarlık bir bütçeyle yatırım yapmayı düşünüyorsunuz? Aşağıdaki tutarlardan birini seçebilir ya da TL cinsinden yazabilirsiniz.",
    budgetPresets: [10_000, 50_000, 100_000],
    budgetPlaceholder: "Bütçenizi TL olarak yazın (örn. 25.000)",
    budgetNotUnderstood:
      "Tutarı tam anlayamadım. Lütfen bütçenizi TL olarak yazar mısınız? Örneğin 25.000 ya da 40 bin.",
    askHorizon: (budget) =>
      `Teşekkürler, ${budget} bütçe ile ilerliyoruz. Ne kadar süreli bir yatırım düşünüyorsunuz?`,
    horizonOptions: [
      { value: "SHORT", label: "Kısa vade", hint: "1 yıla kadar" },
      { value: "MEDIUM", label: "Orta vade", hint: "1 – 3 yıl" },
      { value: "LONG", label: "Uzun vade", hint: "3 yıl ve üzeri" },
    ],
    askRisk: "Anlaşıldı. Peki ne kadar risk almak istersiniz?",
    riskOptions: [
      { value: "LOW", label: "Düşük risk", hint: "Sermayeyi korumak öncelikli" },
      { value: "MEDIUM", label: "Orta risk", hint: "Dengeli dalgalanma" },
      { value: "HIGH", label: "Yüksek risk", hint: "Daha yüksek getiri için dalgalanmaya açığım" },
    ],
    askGoal: "Son olarak, bu yatırımdaki ana amacınız nedir?",
    goalOptions: [
      { value: "LONG_TERM", label: "Birikim", hint: "Uzun vadede düzenli büyüyen bir birikim" },
      { value: "GROWTH", label: "Büyüme", hint: "Getiri potansiyeli yüksek varlıklar" },
      { value: "LOW_VOLATILITY", label: "Koruma", hint: "Düşük dalgalanma, istikrarlı seyir" },
    ],
    optionNotUnderstood:
      "Bunu tam eşleştiremedim. Aşağıdaki seçeneklerden birine dokunabilir ya da benzer şekilde yazabilirsiniz.",
    building: "Teşekkürler! Piyasaları inceliyor ve tercihlerinize uygun paketi hazırlıyorum…",
    ready: (title) =>
      `Tercihlerinize göre hazırladığım paket: ${title}. Aşağıdan içeriğini inceleyebilir, dilerseniz tek dokunuşla satın alabilirsiniz.`,
    failed: (reason) =>
      `Üzgünüm, bu tercihlerle bir paket oluşturamadım: ${reason} Farklı bir bütçe veya tercihle tekrar deneyebiliriz.`,
    cancelled: "Elbette, istediğiniz zaman tekrar başlayabiliriz. Başka nasıl yardımcı olabilirim?",
    cancelLabel: "Vazgeç",
    restartLabel: "Farklı bir paket oluştur",
    purchased: (orderCount) =>
      `Paketiniz için ${orderCount} adet piyasa emri oluşturuldu. Emirlerinizi İşlemler sayfasından takip edebilirsiniz. Hayırlı olsun!`,
    cancelKeywords: ["iptal", "vazgeç", "vazgec", "boşver", "bosver", "istemiyorum"],
    inputPlaceholder: "Seçeneklerden birini seçin ya da yazın",
  },
  en: {
    suggestionTitle: "How can I help you?",
    suggestions: [
      {
        id: START_INVESTMENT_FLOW_ID,
        label: "I want to invest",
        hint: "A ready-made package for your budget",
        message: "I want to invest",
      },
      { id: "ask-portfolio", label: "Review my portfolio", message: "Can you review my portfolio?" },
      { id: "ask-market", label: "What's happening in the markets?", message: "What's happening in the markets today?" },
    ],
    startMessage:
      "Great, let's put together an investment package that fits you! Just a few quick questions first.",
    askBudget:
      "First, how much would you like to invest? Pick one of the amounts below or type an amount in TRY.",
    budgetPresets: [10_000, 50_000, 100_000],
    budgetPlaceholder: "Type your budget in TRY (e.g. 25000)",
    budgetNotUnderstood:
      "I couldn't quite read that amount. Could you type your budget in TRY? For example 25000 or 40k.",
    askHorizon: (budget) =>
      `Thanks, we'll work with a ${budget} budget. How long do you plan to stay invested?`,
    horizonOptions: [
      { value: "SHORT", label: "Short term", hint: "Up to 1 year" },
      { value: "MEDIUM", label: "Medium term", hint: "1 – 3 years" },
      { value: "LONG", label: "Long term", hint: "3+ years" },
    ],
    askRisk: "Got it. How much risk are you comfortable with?",
    riskOptions: [
      { value: "LOW", label: "Low risk", hint: "Protecting capital comes first" },
      { value: "MEDIUM", label: "Medium risk", hint: "Balanced ups and downs" },
      { value: "HIGH", label: "High risk", hint: "I accept swings for higher returns" },
    ],
    askGoal: "Lastly, what is the main goal of this investment?",
    goalOptions: [
      { value: "LONG_TERM", label: "Savings", hint: "Steady long-term accumulation" },
      { value: "GROWTH", label: "Growth", hint: "Assets with high return potential" },
      { value: "LOW_VOLATILITY", label: "Protection", hint: "Low volatility, stable path" },
    ],
    optionNotUnderstood:
      "I couldn't match that. Tap one of the options below or describe it in a similar way.",
    building: "Thank you! I'm scanning the markets and preparing a package for your preferences…",
    ready: (title) =>
      `Here is the package I prepared for you: ${title}. Review its contents below and buy it with a single tap if you like.`,
    failed: (reason) =>
      `Sorry, I couldn't build a package with these preferences: ${reason} We can try again with a different budget or preferences.`,
    cancelled: "Of course, we can start again any time. How else can I help?",
    cancelLabel: "Cancel",
    restartLabel: "Build a different package",
    purchased: (orderCount) =>
      `${orderCount} market orders were created for your package. You can track them on the Transactions page. Congratulations!`,
    cancelKeywords: ["cancel", "stop", "never mind", "nevermind", "quit"],
    inputPlaceholder: "Pick an option or type your answer",
  },
};

export function getInvestmentFlowCopy(language: AppLanguage): InvestmentFlowCopy {
  return COPY[language] ?? COPY.tr;
}

/** Free-text synonyms so typed answers still resolve to an option. */
export const HORIZON_KEYWORDS: Record<InvestmentHorizon, string[]> = {
  SHORT: ["kısa", "kisa", "short", "1 yıl", "1 yil", "bir yıl", "ay", "month"],
  MEDIUM: ["orta", "medium", "mid", "2 yıl", "3 yıl", "2 yil", "3 yil"],
  LONG: ["uzun", "long", "5 yıl", "10 yıl", "5 yil", "10 yil", "emeklilik", "retire"],
};

export const RISK_KEYWORDS: Record<InvestmentRiskProfile, string[]> = {
  LOW: ["düşük", "dusuk", "az", "low", "temkinli", "güvenli", "guvenli", "safe"],
  MEDIUM: ["orta", "medium", "dengeli", "balanced", "moderate"],
  HIGH: ["yüksek", "yuksek", "high", "agresif", "aggressive", "çok", "cok"],
};

export const GOAL_KEYWORDS: Record<InvestmentGoal, string[]> = {
  LONG_TERM: ["birikim", "saving", "tasarruf", "uzun", "emekli"],
  GROWTH: ["büyüme", "buyume", "growth", "getiri", "kazanç", "kazanc", "return"],
  LOW_VOLATILITY: ["koruma", "korun", "protect", "istikrar", "stable", "düşük", "dusuk", "oynaklık"],
  MOMENTUM: ["momentum", "trend"],
};
