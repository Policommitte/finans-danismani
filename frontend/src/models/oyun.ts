
export type Difficulty = "kolay" | "orta" | "zor";

export type Question = {
  id: number;
  text: string;
  options: string[];
  correctIndex: number;
  timerSeconds: number;
  educationNote: string;
  difficulty: Difficulty;
};

export type CheatSheetTopic = {
  title: string;
  body: string;
};

export type Campaign = {
  id: number;
  image: string;
  tags: string;
  title: string;
  body: string;
  likes: number;
  joined: number;
  left: string;
};

export type HistoryRow = {
  date: string;
  result: "win" | "out";
  detail: string;
  score: number;
  points: number;
};

// ── Ayarlar ────────────────────────────────────────────────
export const CONFIG = {
  questionCount: 10,
  questionSeconds: 15,
  cheatSheetSeconds: 300, // 5 dk
  prizePool: 10000,
  capacityTotal: 1000,
  answerRevealMs: 5000, // cevaptan sonra bekleme
  // TEST: doğru şık her soruda B konumuna sabitlenir. Sunumdan önce false.
  forceAnswerB: true,
} as const;

// ── Çalışma notu ───────────────────────────────────────────
export const CHEAT_SHEET: CheatSheetTopic[] = [
  {
    title: "Bileşik faiz",
    body: "Kazanılan faiz anaparaya eklenir ve yeniden faiz getirir. Erken başlamak süreyi en değerli girdi hâline getirir.",
  },
  {
    title: "Enflasyon ve alım gücü",
    body: "Fiyatlar sürekli yükselir, aynı para zamanla daha az şey alır. Getiri enflasyonun altında kalırsa reel olarak kayıp vardır.",
  },
  {
    title: "Çeşitlendirme",
    body: "Birikimi farklı varlıklara dağıtmak tek bir varlığın kötü gitmesinin etkisini azaltır. Aynı sektördeki varlıklar aynı şoklara birlikte maruz kalır.",
  },
  {
    title: "Risk ve getiri",
    body: "Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek getiri bir arada vaat ediliyorsa risk muhtemelen gizlenmiştir.",
  },
  {
    title: "Acil durum fonu",
    body: "Beklenmedik giderlerde borçlanmadan dayanmayı sağlayan rezervdir. İhtiyaç anında hızla ve değer kaybetmeden nakde çevrilebilmelidir.",
  },
  {
    title: "Borç ve kredi yönetimi",
    body: "Asgari ödeme borcu bitirmez, kalan tutara faiz işlemeye devam eder. Ödeme geçmişi kredi notunu en çok etkileyen unsurdur.",
  },
];

// ── Soru havuzu ────────────────────────────────────────────
export const QUESTIONS: Question[] = [
  {
    id: 1,
    text: "Aynı faiz oranı ve aynı anapara ile 10 yıl yatırım yapan iki kişiden biri basit, diğeri bileşik faiz kullanıyor. Aradaki farkın temel nedeni nedir?",
    options: [
      "Bileşik faizde oran her yıl otomatik olarak yükseltilir",
      "Bileşik faizde kazanılan faiz de faiz getirmeye başlar",
      "Basit faizde vergi kesintisi daha yüksektir",
      "Basit faizde anapara her yıl azaltılır",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Bileşik faizde oran değişmez; değişen şey faiz işleyen tutardır. Kazanç anaparaya eklendikçe taban büyür ve süre uzadıkça fark hızla açılır.",
    difficulty: "orta",
  },
  {
    id: 2,
    text: "Yıllık getirisi %30 olan bir yatırım, enflasyonun %45 olduğu bir yılda ne anlama gelir?",
    options: [
      "Reel olarak kazanç sağlanmıştır",
      "Reel olarak kayıp yaşanmıştır",
      "Reel getiri tam olarak sıfırdır",
      "Enflasyon reel getiriyi etkilemez",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Nominal getiri enflasyonun altında kaldığında paranın miktarı artsa bile alım gücü azalır. Gerçek performans, getiriden enflasyon düşülerek ölçülür.",
    difficulty: "orta",
  },
  {
    id: 3,
    text: "Bir yatırımcı tüm birikimini aynı sektördeki beş farklı şirkete dağıtıyor. Bu neden tam bir çeşitlendirme sayılmaz?",
    options: [
      "Beş varlık çeşitlendirme için yetersiz sayıdadır",
      "Aynı sektördeki varlıklar benzer risklerden birlikte etkilenir",
      "Çeşitlendirme yalnızca farklı ülkelerde yapılabilir",
      "Hisse senetleri çeşitlendirmeye uygun değildir",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Çeşitlendirmenin işe yaraması için varlıkların birlikte hareket etmemesi gerekir. Aynı sektör aynı şoklara maruz kaldığı için sayı artsa da risk yeterince dağılmaz.",
    difficulty: "zor",
  },
  {
    id: 4,
    text: '"Garantili, risksiz, aylık %20 getiri" vaat eden bir yatırım teklifi için aşağıdakilerden hangisi doğrudur?',
    options: [
      "Getirisi yüksek olduğu için öncelikli tercih edilmelidir",
      "Risk ve getiri ilişkisine aykırıdır, riski gizlenmiş olabilir",
      "Kısa vadede risksiz, uzun vadede risklidir",
      "Faiz oranı sabitse risk otomatik olarak ortadan kalkar",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek getiri bir arada vaat ediliyorsa, risk ortadan kalkmamıştır; yalnızca gösterilmemektedir.",
    difficulty: "kolay",
  },
  {
    id: 5,
    text: "Acil durum fonu için aşağıdaki saklama biçimlerinden hangisi en uygundur?",
    options: [
      "Beş yıl vadeli, erken çıkışta ceza uygulanan bir üründe",
      "Kısa sürede nakde çevrilebilen likit bir araçta",
      "Uzun vadede en çok kazandıran yüksek riskli varlıkta",
      "Satışı haftalar sürebilen fiziksel bir varlıkta",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Acil durum fonunun amacı kazanç değil erişilebilirliktir. İhtiyaç anında beklemeden ve değer kaybetmeden çekilebilmesi gerekir.",
    difficulty: "kolay",
  },
  {
    id: 6,
    text: "Kredi kartı ekstresinde yalnızca asgari tutarı ödeyen bir kullanıcı için aşağıdakilerden hangisi doğrudur?",
    options: [
      "Kalan borç faizsiz olarak bir sonraki aya devreder",
      "Ödenmeyen tutara faiz işler ve borç büyümeye devam eder",
      "Kart limiti otomatik olarak yükseltilir",
      "O ay yapılan tüm harcamalar iptal edilir",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Asgari ödeme kartın kapanmasını önler ama borcu bitirmez. Kalan tutara akdi faiz işler; her ay tekrarlandığında borç bileşik biçimde büyür.",
    difficulty: "kolay",
  },
  {
    id: 7,
    text: "50/30/20 bütçe kuralında yüzde 20'lik dilim neyi ifade eder?",
    options: [
      "Zorunlu giderleri",
      "Birikim ve borç kapatmayı",
      "Kişisel harcamaları",
      "Vergi ve sigorta ödemelerini",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Kuralda gelirin yarısı zorunlu ihtiyaçlara, yüzde 30'u isteklere, yüzde 20'si birikime ve borç kapatmaya ayrılır. Birikimi önce ayırmak, kalanla yaşamayı kolaylaştırır.",
    difficulty: "kolay",
  },
  {
    id: 8,
    text: "Bir kişinin kredi notunu en olumsuz etkileyen davranış aşağıdakilerden hangisidir?",
    options: [
      "Kredi kartını hiç kullanmamak",
      "Ödemeleri düzenli olarak geciktirmek",
      "Birden fazla bankada hesabı olmak",
      "Otomatik ödeme talimatı vermek",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Kredi notunu belirleyen en ağırlıklı unsur ödeme geçmişidir. Gecikmeler kayda geçer ve sonraki kredi başvurularında hem onayı hem faiz oranını olumsuz etkiler.",
    difficulty: "orta",
  },
  {
    id: 9,
    text: 'Vadeli mevduatta "brüt faiz" ile "net faiz" arasındaki fark neyden kaynaklanır?',
    options: [
      "Bankanın uyguladığı hesap işletim ücretinden",
      "Faiz gelirinden yapılan stopaj kesintisinden",
      "Enflasyon oranındaki değişimden",
      "Vade sonunda uygulanan kur farkından",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Mevduat faizinden yasal stopaj kesilir. Ürünleri karşılaştırırken brüt oran değil, elinize geçecek net tutar dikkate alınmalıdır.",
    difficulty: "zor",
  },
  {
    id: 10,
    text: "Portföyünde ağırlıklı olarak hisse senedi bulunan bir yatırımcı, emekliliğine iki yıl kala ne yapmalıdır?",
    options: [
      "Riski artırıp getiriyi hızlandırmalıdır",
      "Dalgalanmayı azaltmak için düşük riskli araçların payını artırmalıdır",
      "Tüm birikimi tek bir hisseye toplamalıdır",
      "Portföyü olduğu gibi bırakmalıdır, vade önemsizdir",
    ],
    correctIndex: 1,
    timerSeconds: 15,
    educationNote:
      "Yatırım ufku kısaldıkça kayıpları telafi etme süresi de azalır. Hedefe yaklaşırken portföyün risk düzeyini kademeli düşürmek yaygın bir yaklaşımdır.",
    difficulty: "orta",
  },
];

// ── Maskot balon metinleri ─────────────────────────────────
export const MASCOT_IDLE = [
  "Soruyu bir daha okuyalım.",
  "Acele etmeyin, süre var.",
  "Bu konuyu raporda görmüştük.",
  "Şıkları karşılaştırın.",
  "Cevap çalışma notunda geçiyordu.",
];

// ── Kampanyalar ────────────────────────────────────────────
export const CAMPAIGNS: Campaign[] = [
  {
    id: 1,
    image: "/oyun/kampanyalar/market.jpg",
    tags: "#market #bonus",
    title: "Market alışverişlerinize 500 TL bonus!",
    body: "Anlaşmalı marketlerde ayda 3.000 TL ve üzeri harcamanıza 500 TL değerinde bonus puan tanımlanır.",
    likes: 2798,
    joined: 83583,
    left: "12 gün kaldı",
  },
  {
    id: 2,
    image: "/oyun/kampanyalar/karekod.jpg",
    tags: "#karekod #bonus",
    title: "Karekod ödemelerinize 500 TL bonus!",
    body: "Karekod ile yapacağınız ödemelerde işlem başına ekstra bonus kazanın, kampanya süresince limitsiz.",
    likes: 2445,
    joined: 34301,
    left: "8 gün kaldı",
  },
  {
    id: 3,
    image: "/oyun/kampanyalar/davet.jpg",
    tags: "#online #yurtdışı #indirim",
    title: "Yurt dışı internet alışverişlerinize 600 TL'ye varan indirim!",
    body: "Yurt dışı e-ticaret sitelerindeki harcamalarınızda kademeli indirim, tek işlemde 600 TL sınırıyla.",
    likes: 1694,
    joined: 40360,
    left: "21 gün kaldı",
  },
  {
    id: 4,
    image: "/oyun/kampanyalar/sampiyon.jpg",
    tags: "#yarışma #şampiyon",
    title: "Haftanın şampiyonuna 5.000 bonus puan!",
    body: "Şans Yatırımda haftalık skor sıralamasında ilk sırayı alan yarışmacıya ekstra bonus puan verilir.",
    likes: 3120,
    joined: 12874,
    left: "4 gün kaldı",
  },
  {
    id: 5,
    image: "/oyun/kampanyalar/davet.jpg",
    tags: "#davet #bonus",
    title: "Arkadaşını davet et, 500 bonus puan kazan!",
    body: "Davet ettiğiniz her arkadaşınız ilk yarışmasına katıldığında hesabınıza bonus puan yüklenir.",
    likes: 1876,
    joined: 26140,
    left: "Süresiz",
  },
  {
    id: 6,
    image: "/oyun/kampanyalar/sadakat.jpg",
    tags: "#sadakat #rozet",
    title: "10 yarışma katılımına özel rozet ve 3.000 puan!",
    body: "Ay içinde 10 yarışmaya katılan kullanıcılara sadakat rozeti ve bonus puan hediye edilir.",
    likes: 942,
    joined: 8452,
    left: "17 gün kaldı",
  },
];

// ── Puan geçmişi ───────────────────────────────────────────
export const HISTORY: HistoryRow[] = [
  { date: "18 Ağustos", result: "out", detail: "Elendi · Soru 4", score: 260, points: 0 },
  { date: "17 Ağustos", result: "win", detail: "Kazandı", score: 905, points: 125 },
  { date: "16 Ağustos", result: "out", detail: "Elendi · Soru 2", score: 340, points: 0 },
  { date: "15 Ağustos", result: "win", detail: "Kazandı", score: 810, points: 82 },
  { date: "14 Ağustos", result: "win", detail: "Kazandı", score: 720, points: 105 },
  { date: "13 Ağustos", result: "out", detail: "Elendi · Soru 1", score: 180, points: 0 },
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
export function prepareQuestions(count = CONFIG.questionCount): PreparedQuestion[] {
  return shuffle(QUESTIONS)
    .slice(0, count)
    .map((q) => {
      const indexed = shuffle(q.options.map((text, i) => ({ text, orig: i })));

      if (CONFIG.forceAnswerB) {
        const cur = indexed.findIndex((o) => o.orig === q.correctIndex);
        [indexed[1], indexed[cur]] = [indexed[cur], indexed[1]];
      }

      return {
        text: q.text,
        options: indexed.map((o) => o.text),
        correctIndex: indexed.findIndex((o) => o.orig === q.correctIndex),
        educationNote: q.educationNote,
        timerSeconds: q.timerSeconds,
      };
    });
}

/** Doğru cevabın puanı: 100 taban + kalan süreye göre 0-100 hız bonusu */
export function scoreFor(elapsedSeconds: number, limitSeconds: number): number {
  const ratio = Math.max(0, (limitSeconds - elapsedSeconds) / limitSeconds);
  return Math.round(100 + 100 * ratio);
}

/** Şık dağılımı: doğru cevap ağırlıklı, toplam 100 */
export function buildShares(correctIndex: number): number[] {
  const w = [0, 1, 2, 3].map((i) =>
    i === correctIndex ? 38 + Math.random() * 26 : 6 + Math.random() * 20
  );
  const sum = w.reduce((a, b) => a + b, 0);
  const shares = w.map((v) => Math.round((v / sum) * 100));
  shares[correctIndex] += 100 - shares.reduce((a, b) => a + b, 0);
  return shares;
}

/** Yarışma bittiğinde sonuç ekranlarına taşınan veri */
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
};

export type WinnerRow = {
  label: string;
  score: number;
  payout: number;
  isMe: boolean;
};

export type WinnerStats = {
  winners: number;
  totalScore: number;
  myPayout: number;
  myRank: number;
  board: WinnerRow[];
};

/**
 * Kazanan tablosu.
 * Backend gelene kadar diğer kazananlar demo amaçlı üretiliyor;
 * dağıtım formülü gerçek kuralla aynı: havuz × skor / toplam skor.
 */
export function buildWinnerStats(myScore: number): WinnerStats {
  const otherCount = Math.floor(Math.random() * 4); // 0–3 diğer kazanan
  const others = Array.from({ length: otherCount }, () => ({
    label: `Yarışmacı #${1000 + Math.floor(Math.random() * 8999)}`,
    score: Math.round(myScore * (0.82 + Math.random() * 0.36)),
    isMe: false,
  }));

  const all = [{ label: "Sen", score: myScore, isMe: true }, ...others].sort(
    (a, b) => b.score - a.score
  );

  const totalScore = all.reduce((sum, r) => sum + r.score, 0);

  const board: WinnerRow[] = all.map((r) => ({
    ...r,
    payout: Math.round((CONFIG.prizePool * r.score) / totalScore),
  }));

  return {
    winners: board.length,
    totalScore,
    myPayout: board.find((r) => r.isMe)?.payout ?? 0,
    myRank: board.findIndex((r) => r.isMe) + 1,
    board,
  };
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
export type PowerupKind = "timeShield" | "fiftyFifty";

export type PowerupShopItem = {
  kind: PowerupKind;
  label: string;
  price: number;
  description: string;
  image: string;
};

export const POWERUP_SHOP: PowerupShopItem[] = [
  {
    kind: "timeShield",
    label: "Zaman kalkanı",
    price: 1000,
    description: "Süreyi 15 saniyeden 25 saniyeye çıkarır, soru başına 1 kez kullanılabilir.",
    image: "/oyun/jokerler/zaman-kalkani.jpg",
  },
  {
    kind: "fiftyFifty",
    label: "Çifte şans (50/50)",
    price: 2000,
    description: "İki yanlış şıkkı eler, doğru şık her zaman kalır.",
    image: "/oyun/jokerler/cifte-sans.jpg",
  },
];

export type DonationItem = {
  id: string;
  title: string;
  body: string;
  cost: number;
  badge: string;
  icon: string;
  image: string;
};

export const DONATIONS: DonationItem[] = [
  {
    id: "fidan",
    title: "Bir fidan bağışla",
    body: "TEMA Vakfı işbirliğiyle adınıza bir fidan dikilir, profilinizde kalıcı rozet kazanırsınız.",
    cost: 1500,
    badge: "Fidan Dostu",
    icon: "🌱",
    image: "/oyun/bagislar/fidan.jpg",
  },
  {
    id: "egitim",
    title: "Eğitim desteği",
    body: "Bir öğrencinin finansal okuryazarlık eğitimine katkı sağlarsınız.",
    cost: 3000,
    badge: "Eğitim Gönüllüsü",
    icon: "📚",
    image: "/oyun/bagislar/egitim.jpg",
  },
];

export function buildHistoryRow(result: { won: boolean; score: number; reached: number }, earnedPoints: number): HistoryRow {
  const today = new Date().toLocaleDateString("tr-TR", { day: "numeric", month: "long" });
  return {
    date: today,
    result: result.won ? "win" : "out",
    detail: result.won ? "Kazandı" : `Elendi · Soru ${result.reached}`,
    score: result.score,
    points: earnedPoints,
  };
}


export type LeaderboardPeriod = "gunluk" | "haftalik" | "tumzamanlar";

export type LeaderboardEntry = {
  rank: number;
  label: string;
  score: number;
};

/** Demo liderlik verisi üretir; backend gelince ???? */
export function buildLeaderboard(period: LeaderboardPeriod): LeaderboardEntry[] {
  const seedByPeriod: Record<LeaderboardPeriod, number> = {
    gunluk: 900,
    haftalik: 4200,
    tumzamanlar: 18500,
  };

  const base = seedByPeriod[period];
  const count = 6;

  return Array.from({ length: count }, (_, i) => ({
    rank: i + 1,
    label: `Yarışmacı #${1000 + Math.floor(Math.random() * 8999)}`,
    score: Math.round(base * (1 - i * 0.12) * (0.92 + Math.random() * 0.16)),
  })).sort((a, b) => b.score - a.score)
    .map((entry, i) => ({ ...entry, rank: i + 1 }));
}

export type WeeklyPrize = {
  place: 1 | 2 | 3;
  title: string;
  points: number;
  badge: string;
};

export const WEEKLY_PRIZES: WeeklyPrize[] = [
  { place: 1, title: "AirPods Pro 2", points: 25000, badge: "🥇" },
  { place: 2, title: "Akıllı saat", points: 15000, badge: "🥈" },
  { place: 3, title: "2.500 TL hediye çeki", points: 10000, badge: "🥉" },
];