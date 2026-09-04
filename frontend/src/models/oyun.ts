
export type Difficulty = "kolay" | "orta" | "zor";

export type Lang = "tr" | "en";

export type LocalizedText = { tr: string; en: string };

export type Question = {
  id: number;
  text: LocalizedText;
  options: LocalizedText[];
  correctIndex: number;
  timerSeconds: number;
  educationNote: LocalizedText;
  difficulty: Difficulty;
};

export type CheatSheetTopic = {
  title: LocalizedText;
  body: LocalizedText;
};

export type Campaign = {
  id: number;
  image: string;
  /** Pexels'te canli bir fotograf aranirken kullanilan sorgu (bkz. CampaignsTab). */
  imageQuery: string;
  tags: LocalizedText;
  title: LocalizedText;
  body: LocalizedText;
  likes: number;
  joined: number;
  left: LocalizedText;
};

export type HistoryRow = {
  date: LocalizedText;
  result: "win" | "out" | "purchase";
  detail: LocalizedText;
  score: number;
  points: number;
};

// ── Ayarlar ────────────────────────────────────────────────
export const CONFIG = {
  questionCount: 5,
  questionSeconds: 10,
  cheatSheetSeconds: 30,
  // Kazanan sayısı artık HER ZAMAN 100-500 arasında (bkz. pickTargetWinners).
  // Düz 1.000.000 seçildi: en kötü senaryoda (500 kazanan) payout hâlâ 2.000
  // (1500-2000 bandının üst sınırı); en iyi senaryoda (100 kazanan) 10.000'e
  // çıkar — bu sadece daha cömert olur, sorun değil.
  prizePool: 1000000,
  capacityTotal: 1000,
  answerRevealMs: 5000, // cevaptan sonra bekleme
  // TEST: doğru şık her soruda B konumuna sabitlenir. Sunumdan önce false.
  forceAnswerB: false,
} as const;

// ── Çalışma notu (yarışmadan ÖNCE, "Hazırlık" ekranında) ────
export const CHEAT_SHEET: CheatSheetTopic[] = [
  {
    title: { tr: "Bileşik faiz", en: "Compound interest" },
    body: {
      tr: "Kazanılan faiz de faiz getirir. Erken başlamak en değerli avantajdır.",
      en: "Interest earns more interest. Starting early is your biggest advantage.",
    },
  },
  {
    title: { tr: "Enflasyon ve alım gücü", en: "Inflation and purchasing power" },
    body: {
      tr: "Fiyatlar yükselince aynı para daha az alır. Getiri enflasyonun altındaysa reel kayıptasın.",
      en: "Prices rise, so money buys less over time. A below-inflation return means a real loss.",
    },
  },
  {
    title: { tr: "Çeşitlendirme", en: "Diversification" },
    body: {
      tr: "Birikimi farklı varlıklara dağıtmak riski azaltır. Tek sepete yatırım yapma.",
      en: "Spreading savings across assets lowers risk. Don't put it all in one basket.",
    },
  },
  {
    title: { tr: "Risk ve getiri", en: "Risk and return" },
    body: {
      tr: "Yüksek getiri genelde yüksek risk demektir. Risksiz + yüksek getiri vaadi şüphelidir.",
      en: "Higher return usually means higher risk. A risk-free, high-return promise is suspicious.",
    },
  },
  {
    title: { tr: "Acil durum fonu", en: "Emergency fund" },
    body: {
      tr: "Beklenmedik giderler için hızla nakde çevrilebilen bir rezervdir.",
      en: "A reserve you can quickly turn into cash for unexpected expenses.",
    },
  },
  {
    title: { tr: "Borç ve kredi yönetimi", en: "Debt and credit management" },
    body: {
      tr: "Asgari ödeme borcu bitirmez, faiz işlemeye devam eder. Ödeme geçmişi kredi notunu belirler.",
      en: "Minimum payments don't clear debt — interest keeps accruing. Payment history drives your credit score.",
    },
  },
];

// ── Sonraki yarışmayı beklerken göz atılacak notlar (çalışma
// notundan BİLEREK farklı konular - tekrar değil, ek bilgi) ──
export const WAITING_NOTES: CheatSheetTopic[] = [
  {
    title: { tr: "Likidite", en: "Liquidity" },
    body: {
      tr: "Bir varlığı hızlı ve değer kaybetmeden nakde çevirebilme yeteneğidir.",
      en: "The ability to turn an asset into cash quickly without losing value.",
    },
  },
  {
    title: { tr: "Vergi ve stopaj", en: "Tax and withholding" },
    body: {
      tr: "Kazancın bir kısmı vergi olarak kesilir. Önemli olan vergi sonrası nettir.",
      en: "Part of your gain goes to tax. What matters is the after-tax net.",
    },
  },
  {
    title: { tr: "Kur riski", en: "Currency risk" },
    body: {
      tr: "Döviz varlıkların TL karşılığı, kurla birlikte büyür ya da erir.",
      en: "Foreign-currency assets' TL value rises or falls with the exchange rate.",
    },
  },
  {
    title: { tr: "Fırsat maliyeti", en: "Opportunity cost" },
    body: {
      tr: "Bir seçim yapınca vazgeçtiğin en iyi alternatifin değeridir.",
      en: "The value of the best alternative you give up when you choose.",
    },
  },
  {
    title: { tr: "Bütçe kuralı", en: "Budgeting rule" },
    body: {
      tr: "Geliri ihtiyaç, istek ve birikime ayırmayı kolaylaştıran basit bir kuraldır.",
      en: "A simple rule that splits income into needs, wants, and savings.",
    },
  },
  {
    title: { tr: "Düzenli yatırım", en: "Dollar-cost averaging" },
    body: {
      tr: "Her ay sabit tutar yatırmak, piyasayı zamanlama riskini azaltır.",
      en: "Investing a fixed amount every month reduces the risk of timing the market.",
    },
  },
  {
    title: { tr: "Portföy dengeleme", en: "Rebalancing" },
    body: {
      tr: "Zamanla bozulan varlık dağılımını başa döndürüp riski hedefte tutar.",
      en: "Restoring your original asset mix over time keeps risk at your target level.",
    },
  },
  {
    title: { tr: "Emeklilik birikimi", en: "Retirement savings" },
    body: {
      tr: "Devlet katkısıyla uzun vadeli birikim sağlayan gönüllü bir sistemdir.",
      en: "A voluntary long-term savings system that includes a government match.",
    },
  },
  {
    title: { tr: "Finansal hedef belirleme", en: "Goal setting" },
    body: {
      tr: "Net bir hedef ve süre, hangi araca yatırım yapacağını netleştirir.",
      en: "A clear goal and time frame make it easier to pick the right tool.",
    },
  },
];

// ── Soru havuzu ────────────────────────────────────────────
export const QUESTIONS: Question[] = [
  {
    id: 1,
    text: {
      tr: "Aynı faiz oranı ve aynı anapara ile 10 yıl yatırım yapan iki kişiden biri basit, diğeri bileşik faiz kullanıyor. Aradaki farkın temel nedeni nedir?",
      en: "Two people invest for 10 years with the same interest rate and the same principal — one uses simple interest, the other compound interest. What mainly causes the difference between them?",
    },
    options: [
      {
        tr: "Bileşik faizde oran her yıl otomatik olarak yükseltilir",
        en: "With compound interest, the rate automatically increases every year",
      },
      {
        tr: "Bileşik faizde kazanılan faiz de faiz getirmeye başlar",
        en: "With compound interest, the interest earned starts earning interest too",
      },
      {
        tr: "Basit faizde vergi kesintisi daha yüksektir",
        en: "With simple interest, the tax deduction is higher",
      },
      {
        tr: "Basit faizde anapara her yıl azaltılır",
        en: "With simple interest, the principal is reduced every year",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Bileşik faizde oran değişmez; değişen şey faiz işleyen tutardır. Kazanç anaparaya eklendikçe taban büyür ve süre uzadıkça fark hızla açılır.",
      en: "With compound interest, the rate doesn't change — what changes is the amount that earns interest. As gains are added to the principal, the base grows, and the gap widens quickly over time.",
    },
    difficulty: "orta",
  },
  {
    id: 2,
    text: {
      tr: "Yıllık getirisi %30 olan bir yatırım, enflasyonun %45 olduğu bir yılda ne anlama gelir?",
      en: "What does a 30% annual return mean for an investment in a year when inflation is 45%?",
    },
    options: [
      { tr: "Reel olarak kazanç sağlanmıştır", en: "A real gain was achieved" },
      { tr: "Reel olarak kayıp yaşanmıştır", en: "A real loss was incurred" },
      { tr: "Reel getiri tam olarak sıfırdır", en: "The real return is exactly zero" },
      { tr: "Enflasyon reel getiriyi etkilemez", en: "Inflation does not affect real return" },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Nominal getiri enflasyonun altında kaldığında paranın miktarı artsa bile alım gücü azalır. Gerçek performans, getiriden enflasyon düşülerek ölçülür.",
      en: "When the nominal return stays below inflation, purchasing power falls even though the amount of money increases. Real performance is measured by subtracting inflation from the return.",
    },
    difficulty: "orta",
  },
  {
    id: 3,
    text: {
      tr: "Bir yatırımcı tüm birikimini aynı sektördeki beş farklı şirkete dağıtıyor. Bu neden tam bir çeşitlendirme sayılmaz?",
      en: "An investor spreads all their savings across five different companies in the same sector. Why doesn't this count as full diversification?",
    },
    options: [
      {
        tr: "Beş varlık çeşitlendirme için yetersiz sayıdadır",
        en: "Five assets are not enough for diversification",
      },
      {
        tr: "Aynı sektördeki varlıklar benzer risklerden birlikte etkilenir",
        en: "Assets in the same sector are affected together by similar risks",
      },
      {
        tr: "Çeşitlendirme yalnızca farklı ülkelerde yapılabilir",
        en: "Diversification can only be done across different countries",
      },
      {
        tr: "Hisse senetleri çeşitlendirmeye uygun değildir",
        en: "Stocks are not suitable for diversification",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Çeşitlendirmenin işe yaraması için varlıkların birlikte hareket etmemesi gerekir. Aynı sektör aynı şoklara maruz kaldığı için sayı artsa da risk yeterince dağılmaz.",
      en: "For diversification to work, assets shouldn't move together. Since the same sector is exposed to the same shocks, risk isn't spread enough even if the number of holdings increases.",
    },
    difficulty: "zor",
  },
  {
    id: 4,
    text: {
      tr: '"Garantili, risksiz, aylık %20 getiri" vaat eden bir yatırım teklifi için aşağıdakilerden hangisi doğrudur?',
      en: 'Which of the following is true for an investment offer promising "guaranteed, risk-free, 20% monthly return"?',
    },
    options: [
      {
        tr: "Getirisi yüksek olduğu için öncelikli tercih edilmelidir",
        en: "It should be preferred first because its return is high",
      },
      {
        tr: "Risk ve getiri ilişkisine aykırıdır, riski gizlenmiş olabilir",
        en: "It contradicts the risk-return relationship; the risk may be hidden",
      },
      {
        tr: "Kısa vadede risksiz, uzun vadede risklidir",
        en: "It's risk-free in the short term but risky in the long term",
      },
      {
        tr: "Faiz oranı sabitse risk otomatik olarak ortadan kalkar",
        en: "If the interest rate is fixed, the risk automatically disappears",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek getiri bir arada vaat ediliyorsa, risk ortadan kalkmamıştır; yalnızca gösterilmemektedir.",
      en: "High returns generally come with high uncertainty. If risk-free and high returns are promised together, the risk hasn't disappeared — it's simply not being shown.",
    },
    difficulty: "kolay",
  },
  {
    id: 5,
    text: {
      tr: "Acil durum fonu için aşağıdaki saklama biçimlerinden hangisi en uygundur?",
      en: "Which of the following storage methods is most suitable for an emergency fund?",
    },
    options: [
      {
        tr: "Beş yıl vadeli, erken çıkışta ceza uygulanan bir üründe",
        en: "A 5-year term product with an early-withdrawal penalty",
      },
      {
        tr: "Kısa sürede nakde çevrilebilen likit bir araçta",
        en: "A liquid instrument that can be converted to cash quickly",
      },
      {
        tr: "Uzun vadede en çok kazandıran yüksek riskli varlıkta",
        en: "A high-risk asset with the best long-term returns",
      },
      {
        tr: "Satışı haftalar sürebilen fiziksel bir varlıkta",
        en: "A physical asset that can take weeks to sell",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Acil durum fonunun amacı kazanç değil erişilebilirliktir. İhtiyaç anında beklemeden ve değer kaybetmeden çekilebilmesi gerekir.",
      en: "The purpose of an emergency fund is accessibility, not return. It should be withdrawable instantly and without losing value when needed.",
    },
    difficulty: "kolay",
  },
  {
    id: 6,
    text: {
      tr: "Kredi kartı ekstresinde yalnızca asgari tutarı ödeyen bir kullanıcı için aşağıdakilerden hangisi doğrudur?",
      en: "Which of the following is true for a user who only pays the minimum amount on their credit card statement?",
    },
    options: [
      {
        tr: "Kalan borç faizsiz olarak bir sonraki aya devreder",
        en: "The remaining debt carries over to next month interest-free",
      },
      {
        tr: "Ödenmeyen tutara faiz işler ve borç büyümeye devam eder",
        en: "Interest accrues on the unpaid amount and the debt keeps growing",
      },
      { tr: "Kart limiti otomatik olarak yükseltilir", en: "The card limit is automatically increased" },
      {
        tr: "O ay yapılan tüm harcamalar iptal edilir",
        en: "All purchases made that month are cancelled",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Asgari ödeme kartın kapanmasını önler ama borcu bitirmez. Kalan tutara akdi faiz işler; her ay tekrarlandığında borç bileşik biçimde büyür.",
      en: "The minimum payment keeps the card from defaulting, but it doesn't clear the debt. Contractual interest accrues on the remaining amount; if repeated every month, the debt grows compound.",
    },
    difficulty: "kolay",
  },
  {
    id: 7,
    text: {
      tr: "50/30/20 bütçe kuralında yüzde 20'lik dilim neyi ifade eder?",
      en: "In the 50/30/20 budget rule, what does the 20% portion represent?",
    },
    options: [
      { tr: "Zorunlu giderleri", en: "Essential expenses" },
      { tr: "Birikim ve borç kapatmayı", en: "Savings and debt repayment" },
      { tr: "Kişisel harcamaları", en: "Personal spending" },
      { tr: "Vergi ve sigorta ödemelerini", en: "Tax and insurance payments" },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Kuralda gelirin yarısı zorunlu ihtiyaçlara, yüzde 30'u isteklere, yüzde 20'si birikime ve borç kapatmaya ayrılır. Birikimi önce ayırmak, kalanla yaşamayı kolaylaştırır.",
      en: "Under the rule, half of income goes to essential needs, 30% to wants, and 20% to savings and debt repayment. Setting savings aside first makes it easier to live on the rest.",
    },
    difficulty: "kolay",
  },
  {
    id: 8,
    text: {
      tr: "Bir kişinin kredi notunu en olumsuz etkileyen davranış aşağıdakilerden hangisidir?",
      en: "Which of the following behaviors most negatively affects a person's credit score?",
    },
    options: [
      { tr: "Kredi kartını hiç kullanmamak", en: "Never using a credit card" },
      { tr: "Ödemeleri düzenli olarak geciktirmek", en: "Regularly making late payments" },
      { tr: "Birden fazla bankada hesabı olmak", en: "Having accounts at multiple banks" },
      { tr: "Otomatik ödeme talimatı vermek", en: "Setting up automatic payment instructions" },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Kredi notunu belirleyen en ağırlıklı unsur ödeme geçmişidir. Gecikmeler kayda geçer ve sonraki kredi başvurularında hem onayı hem faiz oranını olumsuz etkiler.",
      en: "Payment history is the most heavily weighted factor in a credit score. Late payments get recorded and negatively affect both approval and the interest rate on future credit applications.",
    },
    difficulty: "orta",
  },
  {
    id: 9,
    text: {
      tr: 'Vadeli mevduatta "brüt faiz" ile "net faiz" arasındaki fark neyden kaynaklanır?',
      en: 'In a term deposit, what causes the difference between "gross interest" and "net interest"?',
    },
    options: [
      {
        tr: "Bankanın uyguladığı hesap işletim ücretinden",
        en: "The account maintenance fee charged by the bank",
      },
      {
        tr: "Faiz gelirinden yapılan stopaj kesintisinden",
        en: "The withholding tax deducted from interest income",
      },
      { tr: "Enflasyon oranındaki değişimden", en: "Changes in the inflation rate" },
      {
        tr: "Vade sonunda uygulanan kur farkından",
        en: "The exchange-rate difference applied at maturity",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Mevduat faizinden yasal stopaj kesilir. Ürünleri karşılaştırırken brüt oran değil, elinize geçecek net tutar dikkate alınmalıdır.",
      en: "Statutory withholding tax is deducted from deposit interest. When comparing products, you should look at the net amount you'll actually receive, not the gross rate.",
    },
    difficulty: "zor",
  },
  {
    id: 10,
    text: {
      tr: "Portföyünde ağırlıklı olarak hisse senedi bulunan bir yatırımcı, emekliliğine iki yıl kala ne yapmalıdır?",
      en: "What should an investor whose portfolio is mostly stocks do two years before retirement?",
    },
    options: [
      { tr: "Riski artırıp getiriyi hızlandırmalıdır", en: "Increase risk to accelerate returns" },
      {
        tr: "Dalgalanmayı azaltmak için düşük riskli araçların payını artırmalıdır",
        en: "Increase the share of low-risk instruments to reduce volatility",
      },
      { tr: "Tüm birikimi tek bir hisseye toplamalıdır", en: "Put all savings into a single stock" },
      {
        tr: "Portföyü olduğu gibi bırakmalıdır, vade önemsizdir",
        en: "Leave the portfolio as is; the time horizon doesn't matter",
      },
    ],
    correctIndex: 1,
    timerSeconds: 10,
    educationNote: {
      tr: "Yatırım ufku kısaldıkça kayıpları telafi etme süresi de azalır. Hedefe yaklaşırken portföyün risk düzeyini kademeli düşürmek yaygın bir yaklaşımdır.",
      en: "As the investment horizon shortens, there's less time to recover from losses. Gradually lowering the portfolio's risk level as you approach your goal is a common approach.",
    },
    difficulty: "orta",
  },
];

// ── Maskot balon metinleri ─────────────────────────────────
export const MASCOT_IDLE: LocalizedText[] = [
  { tr: "Soruyu bir daha okuyalım.", en: "Let's read the question again." },
  { tr: "Acele etmeyin, süre var.", en: "No rush, there's still time." },
  { tr: "Bu konuyu raporda görmüştük.", en: "We covered this topic in the notes." },
  { tr: "Şıkları karşılaştırın.", en: "Compare the options." },
  { tr: "Cevap çalışma notunda geçiyordu.", en: "The answer was in the study notes." },
];

// ── Kampanyalar ────────────────────────────────────────────
export const CAMPAIGNS: Campaign[] = [
  {
    id: 1,
    image: "/oyun/kampanyalar/market.jpg",
    imageQuery: "grocery shopping supermarket",
    tags: { tr: "#market #bonus", en: "#grocery #bonus" },
    title: { tr: "Market alışverişlerinize 500 TL bonus!", en: "500 TL bonus on your grocery shopping!" },
    body: {
      tr: "Anlaşmalı marketlerde ayda 3.000 TL ve üzeri harcamanıza 500 TL değerinde bonus puan tanımlanır.",
      en: "Get 500 TL worth of bonus points when you spend 3,000 TL or more per month at partner supermarkets.",
    },
    likes: 2798,
    joined: 83583,
    left: { tr: "12 gün kaldı", en: "12 days left" },
  },
  {
    id: 2,
    image: "/oyun/kampanyalar/karekod.jpg",
    imageQuery: "qr code payment phone",
    tags: { tr: "#karekod #bonus", en: "#QRcode #bonus" },
    title: { tr: "Karekod ödemelerinize 500 TL bonus!", en: "500 TL bonus on your QR code payments!" },
    body: {
      tr: "Karekod ile yapacağınız ödemelerde işlem başına ekstra bonus kazanın, kampanya süresince limitsiz.",
      en: "Earn an extra bonus per transaction on QR code payments, unlimited for the duration of the campaign.",
    },
    likes: 2445,
    joined: 34301,
    left: { tr: "8 gün kaldı", en: "8 days left" },
  },
  {
    id: 3,
    image: "/oyun/kampanyalar/yurtdisi.jpg",
    imageQuery: "online shopping delivery box",
    tags: { tr: "#online #yurtdışı #indirim", en: "#online #international #discount" },
    title: {
      tr: "Yurt dışı internet alışverişlerinize 600 TL'ye varan indirim!",
      en: "Up to 600 TL off your international online purchases!",
    },
    body: {
      tr: "Yurt dışı e-ticaret sitelerindeki harcamalarınızda kademeli indirim, tek işlemde 600 TL sınırıyla.",
      en: "Tiered discount on spending at international e-commerce sites, capped at 600 TL per transaction.",
    },
    likes: 1694,
    joined: 40360,
    left: { tr: "21 gün kaldı", en: "21 days left" },
  },
  {
    id: 4,
    image: "/oyun/kampanyalar/sampiyon.jpg",
    imageQuery: "trophy champion winner",
    tags: { tr: "#yarışma #şampiyon", en: "#contest #champion" },
    title: { tr: "Haftanın şampiyonuna 5.000 bonus puan!", en: "5,000 bonus points for the champion of the week!" },
    body: {
      tr: "Şans Yatırımda haftalık skor sıralamasında ilk sırayı alan yarışmacıya ekstra bonus puan verilir.",
      en: "The contestant who ranks first on the weekly Şans Yatırımda leaderboard receives extra bonus points.",
    },
    likes: 3120,
    joined: 12874,
    left: { tr: "4 gün kaldı", en: "4 days left" },
  },
  {
    id: 5,
    image: "/oyun/kampanyalar/davet.jpg",
    imageQuery: "friends invitation gift",
    tags: { tr: "#davet #bonus", en: "#invite #bonus" },
    title: { tr: "Arkadaşını davet et, 500 bonus puan kazan!", en: "Invite a friend, earn 500 bonus points!" },
    body: {
      tr: "Davet ettiğiniz her arkadaşınız ilk yarışmasına katıldığında hesabınıza bonus puan yüklenir.",
      en: "Bonus points are added to your account every time a friend you invited joins their first contest.",
    },
    likes: 1876,
    joined: 26140,
    left: { tr: "Süresiz", en: "Ongoing" },
  },
  {
    id: 6,
    image: "/oyun/kampanyalar/sadakat.jpg",
    imageQuery: "loyalty badge medal",
    tags: { tr: "#sadakat #rozet", en: "#loyalty #badge" },
    title: {
      tr: "10 yarışma katılımına özel rozet ve 3.000 puan!",
      en: "Exclusive badge and 3,000 points for 10 contest entries!",
    },
    body: {
      tr: "Ay içinde 10 yarışmaya katılan kullanıcılara sadakat rozeti ve bonus puan hediye edilir.",
      en: "Users who join 10 contests within a month receive a loyalty badge and bonus points.",
    },
    likes: 942,
    joined: 8452,
    left: { tr: "17 gün kaldı", en: "17 days left" },
  },
];

// ── Yardımcılar ────────────────────────────────────────────

/** Diziyi yerinde karıştırır (Fisher-Yates) */
export function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export type PreparedQuestion = {
  text: string;
  options: string[];
  correctIndex: number;
  educationNote: string;
  timerSeconds: number;
};

/** Soruları ve şıkları karıştırır; test modunda doğru şıkkı B'ye sabitler */
export function prepareQuestions(lang: Lang, count = CONFIG.questionCount): PreparedQuestion[] {
  return shuffle(QUESTIONS)
    .slice(0, count)
    .map((q) => {
      const indexed = shuffle(q.options.map((text, i) => ({ text: text[lang], orig: i })));

      if (CONFIG.forceAnswerB) {
        const cur = indexed.findIndex((o) => o.orig === q.correctIndex);
        [indexed[1], indexed[cur]] = [indexed[cur], indexed[1]];
      }

      return {
        text: q.text[lang],
        options: indexed.map((o) => o.text),
        correctIndex: indexed.findIndex((o) => o.orig === q.correctIndex),
        educationNote: q.educationNote[lang],
        timerSeconds: q.timerSeconds,
      };
    });
}

/** Doğru cevabın puanı: 100 taban + kalan süreye göre 0-100 hız bonusu */
export function scoreFor(elapsedSeconds: number, limitSeconds: number): number {
  const ratio = Math.max(0, (limitSeconds - elapsedSeconds) / limitSeconds);
  return Math.round(100 + 100 * ratio);
}

/**
 * `survivalPercent`: bu soruyu doğru bilenlerin (rivals'ta kalacak kişilerin)
 * GERÇEK oranı — rivalsCurve'den gelir. Ekranda gösterilen "% doğru bildi"
 * ile rakip sayısındaki düşüş burada TEK kaynaktan, birebir tutarlı çıkar.
 * Küçük bir görsel gürültü eklenir ama ortalama değeri asla kaydırmaz.
 */
export function buildShares(correctIndex: number, survivalPercent = 78): number[] {
  const jitter = (Math.random() - 0.5) * 6; // ±3 puan görsel gürültü
  const correctShare = Math.min(97, Math.max(3, survivalPercent + jitter));
  const remaining = 100 - correctShare;

  const w = [0, 1, 2, 3].map((i) => (i === correctIndex ? 0 : 4 + Math.random() * 8));
  const wrongSum = w.reduce((a, b) => a + b, 0);

  const shares = [0, 1, 2, 3].map((i) =>
    i === correctIndex ? Math.round(correctShare) : Math.round((w[i] / wrongSum) * remaining)
  );
  shares[correctIndex] += 100 - shares.reduce((a, b) => a + b, 0);
  return shares;
}

/** Yarışma başında seçilen, o oturum boyunca sabit kalan kazanan sayısı (100-500) */
export function pickTargetWinners(min = 100, max = 500): number {
  return min + Math.floor(Math.random() * (max - min + 1));
}

/** Rakip sayısını `start`'tan `target`'a düzgün bir eğriyle indirir. */
export function computeRivals(
  start: number,
  target: number,
  totalSteps: number,
  step: number
): number {
  if (totalSteps <= 0 || start <= target) return target;
  const clampedStep = Math.min(Math.max(step, 0), totalSteps);
  const ratio = Math.pow(target / start, clampedStep / totalSteps);
  return Math.max(target, Math.round(start * ratio));
}

/**
 * `start`'tan `target`'a inen, oturum başında BİR KEZ hesaplanan tam eğri
 * (index 0 = ilk soru, index totalSteps = son soru). Ara adımlarda görsel
 * çeşitlilik için küçük gürültü eklenir, ama dizinin SONU her zaman
 * `target`'a birebir eşittir — kazanan sayısı asla hedef aralığın (100-500)
 * dışına kaymaz. Bu eğri; "kaç kişi yarışta" gösterimi, şıkların "% doğru
 * bildi" değerleri ve kazanan sayısının TEK ortak kaynağıdır.
 */
export function buildRivalsCurve(start: number, target: number, totalSteps: number): number[] {
  const curve: number[] = [Math.max(target, Math.round(start))];
  for (let step = 1; step <= totalSteps; step++) {
    if (step === totalSteps) {
      curve.push(target);
      continue;
    }
    const baseline = computeRivals(start, target, totalSteps, step);
    const jitter = 1 + (Math.random() * 0.12 - 0.06); // ±%6 görsel gürültü
    const value = Math.max(target, Math.min(curve[step - 1] - 1, Math.round(baseline * jitter)));
    curve.push(Math.max(target, value));
  }
  return curve;
}

export type GameResult = {
  won: boolean;
  score: number;
  /** Ulaşılan soru numarası (1 tabanlı) */
  reached: number;
  /** Doğru bilinen soru sayısı */
  correct: number;
  /** Süre dolduğu için mi elendi */
  timedOut: boolean;
  /** Elenilen sorunun metni ve doğrusu — eğitim amaçlı gösterilir */
  questionText: string;
  correctAnswer: string;
  educationNote: string;
  /** Yarışmanın SON sorusunda ekranda gösterilen "yarışta kalan" sayısı —
   *  WinnerScreen'deki kazanan sayısı bununla TUTARLI olmak zorunda. */
  rivalsAtEnd: number;
  /** Havuzdan bu oyuncuya düşen pay — TEK hesap noktası, her yerde aynı sayı kullanılır */
  payout: number;
};

/** Havuzu kazanan sayısına göre böler — GameResult oluşurken BİR KEZ hesaplanır. */
export function computePayout(rivalsAtEnd: number): number {
  const winners = Math.max(1, rivalsAtEnd);
  return Math.max(1, Math.round(CONFIG.prizePool / winners));
}

export type WinnerStats = {
  winners: number;
  myPayout: number;
  myRank: number;
};

const COMPETITOR_LABEL: LocalizedText = { tr: "Yarışmacı", en: "Competitor" };

/**
 * Kazanma ekranında gösterilecek üç sayıyı üretir. Başka oyuncuları temsil
 * eden uydurma bir liste ARTIK YOK (kafa karıştırıyordu) — sadece kullanıcının
 * kendi payı gösteriliyor. `winners` ve `myPayout` dışarıdan gelen TEK doğru
 * kaynaktır (rivalsAtEnd / computePayout); `myRank`, skorun gerçekçi bir üst
 * sınıra (1200) oranlanmasıyla türetilen, kazanan sayısı içindeki tahmini
 * konumdur.
 */
export function buildWinnerStats(myScore: number, rivalsAtEnd: number, payout: number): WinnerStats {
  const winners = Math.max(1, rivalsAtEnd);

  const scoreRatio = Math.min(1, Math.max(0, myScore / 1200));
  const noise = (Math.random() - 0.5) * 0.08; // ±%4 görsel gürültü
  const percentile = Math.min(1, Math.max(0, 1 - scoreRatio + noise));
  const myRank = Math.max(1, Math.min(winners, Math.round(1 + percentile * (winners - 1))));

  return { winners, myPayout: payout, myRank };
}

/** Davet/referans kodu — karışsaabilen harfler (I, O, 0, 1) çıkarıldı */
export function makeReferralCode(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const body = Array.from(
    { length: 6 },
    () => chars[Math.floor(Math.random() * chars.length)]
  ).join("");
  return `SY-${body}`;
}

/** Bir sonraaki yarışmanın (her akşam 20.00) zamanı */
export function nextContestDate(from: Date = new Date()): Date {
  const target = new Date(from);
  target.setHours(20, 0, 0, 0);
  if (target.getTime() <= from.getTime()) target.setDate(target.getDate() + 1);
  return target;
}

// powerup bagis
export type PowerupKind = "doublePoints" | "fiftyFifty";

export type PowerupShopItem = {
  kind: PowerupKind;
  label: LocalizedText;
  price: number;
  description: LocalizedText;
  image: string;
  /** Pexels'te canli bir fotograf aranirken kullanilan sorgu (bkz. CampaignsTab). */
  imageQuery: string;
};

export const POWERUP_SHOP: PowerupShopItem[] = [
  {
    kind: "doublePoints",
    label: { tr: "Çift puan", en: "Double points" },
    price: 1000,
    description: {
      tr: "Bu soruyu doğru bilirsen kazandığın puanı ikiye katlar, soru başına 1 kez kullanılabilir.",
      en: "Doubles the points you earn if you get this question right, usable once per question.",
    },
    // Not: adanmis bir "cift puan" gorseli yok, mevcut ikon (saat) buradan
    // kalma - Pexels sorgusu daha uygun bir canli fotograf bulmayi dener.
    image: "/oyun/jokerler/zaman-kalkani.jpg",
    imageQuery: "bonus coins doubled prize",
  },
  {
    kind: "fiftyFifty",
    label: { tr: "Çifte şans (50/50)", en: "Double chance (50/50)" },
    price: 2000,
    description: {
      tr: "İki yanlış şıkkı eler, doğru şık her zaman kalır.",
      en: "Eliminates two wrong options; the correct one always remains.",
    },
    image: "/oyun/jokerler/cifte-sans.jpg",
    imageQuery: "dice game luck",
  },
];

export type DonationItem = {
  id: string;
  title: LocalizedText;
  body: LocalizedText;
  cost: number;
  badge: LocalizedText;
  icon: string;
  image: string;
  /** Pexels'te canli bir fotograf aranirken kullanilan sorgu (bkz. CampaignsTab). */
  imageQuery: string;
};

export const DONATIONS: DonationItem[] = [
  {
    id: "fidan",
    title: { tr: "Bir fidan bağışla", en: "Plant a tree" },
    body: {
      tr: "TEMA Vakfı işbirliğiyle adınıza bir fidan dikilir, profilinizde kalıcı rozet kazanırsınız.",
      en: "A tree is planted in your name in partnership with the TEMA Foundation, and you earn a permanent badge on your profile.",
    },
    cost: 1500,
    badge: { tr: "Fidan Dostu", en: "Tree Friend" },
    icon: "🌱",
    image: "/oyun/bagislar/fidan.jpg",
    imageQuery: "tree planting sapling",
  },
  {
    id: "egitim",
    title: { tr: "Eğitim desteği", en: "Education support" },
    body: {
      tr: "Bir öğrencinin finansal okuryazarlık eğitimine katkı sağlarsınız.",
      en: "You contribute to a student's financial literacy education.",
    },
    cost: 3000,
    badge: { tr: "Eğitim Gönüllüsü", en: "Education Volunteer" },
    icon: "📚",
    image: "/oyun/bagislar/egitim.jpg",
    imageQuery: "children studying classroom",
  },
];

const WON_LABEL: LocalizedText = { tr: "Kazandı", en: "Won" };
const ELIMINATED_LABEL: LocalizedText = { tr: "Elendi", en: "Eliminated" };
const QUESTION_LABEL: LocalizedText = { tr: "Soru", en: "Question" };

/**
 * Backend'in `/api/contest/wallet/history` satırını (bkz.
 * `models/contestApi.ts::ContestHistoryRowApi`) ekranda gösterilen
 * `HistoryRow`'a çevirir. Parametre tipi BİLEREK inline (nominal import
 * değil) — `contestApi.ts` zaten `LocalizedText`'i buradan alıyor, tersten
 * bir import döngü yaratırdı; TypeScript'in yapısal tipleme özelliği
 * `ContestHistoryRowApi`'yi buraya sorunsuz geçirmeyi sağlıyor.
 *
 * Satır üç türden biri olabilir (`kind`): yarışma katılımı, joker satın
 * alma veya bağış — mağaza fiyat/etiket bilgisi burada `POWERUP_SHOP` /
 * `DONATIONS`'tan okunur, backend yalnızca kind + miktarı taşır (bkz.
 * services/contest.py::get_history docstring'i).
 */
export function apiHistoryRowToDisplay(row: {
  occurred_at: string;
  kind: "contest" | "powerup_purchase" | "donation_purchase";
  points: number;
  won: boolean | null;
  final_score: number | null;
  eliminated_at_question: number | null;
  powerup_kind: string | null;
  donation_key: string | null;
}): HistoryRow {
  const d = new Date(row.occurred_at);
  const date: LocalizedText = {
    tr: d.toLocaleDateString("tr-TR", { day: "numeric", month: "long" }),
    en: d.toLocaleDateString("en-US", { day: "numeric", month: "long" }),
  };

  if (row.kind === "powerup_purchase") {
    const item = POWERUP_SHOP.find((p) => p.kind === row.powerup_kind);
    const name = item?.label ?? { tr: row.powerup_kind ?? "", en: row.powerup_kind ?? "" };
    return {
      date,
      result: "purchase",
      detail: { tr: `${name.tr} satın alındı`, en: `${name.en} purchased` },
      score: 0,
      points: row.points,
    };
  }

  if (row.kind === "donation_purchase") {
    const item = DONATIONS.find((donation) => donation.id === row.donation_key);
    const name = item?.title ?? { tr: row.donation_key ?? "", en: row.donation_key ?? "" };
    return {
      date,
      result: "purchase",
      detail: name,
      score: 0,
      points: row.points,
    };
  }

  const detail: LocalizedText = row.won
    ? WON_LABEL
    : row.eliminated_at_question != null
      ? {
          tr: `${ELIMINATED_LABEL.tr} · ${QUESTION_LABEL.tr} ${row.eliminated_at_question}`,
          en: `${ELIMINATED_LABEL.en} · ${QUESTION_LABEL.en} ${row.eliminated_at_question}`,
        }
      : ELIMINATED_LABEL;
  return {
    date,
    result: row.won ? "win" : "out",
    detail,
    score: row.final_score ?? 0,
    points: row.points,
  };
}

export type LeaderboardPeriod = "gunluk" | "haftalik" | "tumzamanlar";

export type LeaderboardEntry = {
  rank: number;
  label: string;
  score: number;
};

/** Demo liderlik verisi üretir (sahte, tamamen frontend simülasyonu).
 * Taban puanlar BİLEREK gerçek bir oyuncunun ulaşabileceği tavan puanın
 * (5 soru × soru başına maksimum 200 puan = 1000, bkz. `scoreFor`) belirgin
 * şekilde üzerinde tutulur - listedeki en düşük sıradaki rakip bile en kötü
 * jitter durumunda ~1250 puanın altına inmez. Amaç: demo/gerçek bir oyuncu
 * ne kadar iyi oynarsa oynasın bu sahte sıralamaya asla giremesin. */
export function buildLeaderboard(period: LeaderboardPeriod, lang: Lang): LeaderboardEntry[] {
  const seedByPeriod: Record<LeaderboardPeriod, number> = {
    gunluk: 3400,
    haftalik: 16000,
    tumzamanlar: 70000,
  };

  const base = seedByPeriod[period];
  const count = 6;

  return Array.from({ length: count }, (_, i) => ({
    rank: i + 1,
    label: `${COMPETITOR_LABEL[lang]} #${1000 + Math.floor(Math.random() * 8999)}`,
    score: Math.round(base * (1 - i * 0.12) * (0.92 + Math.random() * 0.16)),
  })).sort((a, b) => b.score - a.score)
    .map((entry, i) => ({ ...entry, rank: i + 1 }));
}

export type WeeklyPrize = {
  place: 1 | 2 | 3;
  title: LocalizedText;
  points: number;
};

export const WEEKLY_PRIZES: WeeklyPrize[] = [
  { place: 1, title: { tr: "AirPods Pro 2", en: "AirPods Pro 2" }, points: 25000 },
  { place: 2, title: { tr: "Akıllı saat", en: "Smart watch" }, points: 15000 },
  { place: 3, title: { tr: "2.500 TL hediye çeki", en: "2,500 TL gift card" }, points: 10000 },
];
