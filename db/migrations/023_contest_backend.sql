-- Sans Yatirimda backend tablolari ve sabit soru havuzu.
-- v5 ana semasindaki 7B bolumunun mevcut veritabanlari icin idempotent hali.

BEGIN;

CREATE TABLE IF NOT EXISTS topic (
    id SERIAL PRIMARY KEY,
    title_tr VARCHAR(100) NOT NULL,
    title_en VARCHAR(100) NOT NULL,
    body_tr TEXT NOT NULL,
    body_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER REFERENCES topic(id),
    text_tr TEXT NOT NULL,
    text_en TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_index SMALLINT NOT NULL CHECK (correct_index BETWEEN 0 AND 3),
    education_note_tr TEXT NOT NULL,
    education_note_en TEXT NOT NULL,
    difficulty VARCHAR(10) NOT NULL DEFAULT 'orta',
    timer_seconds SMALLINT NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS contest (
    id SERIAL PRIMARY KEY,
    contest_date DATE NOT NULL UNIQUE,
    starts_at TIMESTAMPTZ NOT NULL,
    capacity_total INTEGER NOT NULL DEFAULT 1000,
    prize_pool_points INTEGER NOT NULL DEFAULT 1000000,
    question_count SMALLINT NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contest_topic (
    id SERIAL PRIMARY KEY,
    contest_id INTEGER NOT NULL REFERENCES contest(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topic(id),
    sort_order SMALLINT NOT NULL,
    UNIQUE (contest_id, topic_id)
);

CREATE TABLE IF NOT EXISTS contest_question (
    id SERIAL PRIMARY KEY,
    contest_id INTEGER NOT NULL REFERENCES contest(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES question(id),
    sort_order SMALLINT NOT NULL,
    UNIQUE (contest_id, question_id),
    UNIQUE (contest_id, sort_order)
);

CREATE TABLE IF NOT EXISTS contest_agreement (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS participation (
    id SERIAL PRIMARY KEY,
    contest_id INTEGER NOT NULL REFERENCES contest(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contest_date DATE NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    eliminated_at_question SMALLINT,
    final_score INTEGER NOT NULL DEFAULT 0,
    won BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (contest_id, user_id),
    UNIQUE (user_id, contest_date)
);

CREATE TABLE IF NOT EXISTS answer (
    id SERIAL PRIMARY KEY,
    participation_id INTEGER NOT NULL REFERENCES participation(id) ON DELETE CASCADE,
    contest_question_id INTEGER NOT NULL REFERENCES contest_question(id),
    selected_index SMALLINT,
    is_correct BOOLEAN NOT NULL,
    points_earned INTEGER NOT NULL DEFAULT 0,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (participation_id, contest_question_id)
);

CREATE TABLE IF NOT EXISTS payout (
    id SERIAL PRIMARY KEY,
    participation_id INTEGER NOT NULL REFERENCES participation(id) ON DELETE CASCADE,
    points_awarded INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (participation_id)
);

CREATE TABLE IF NOT EXISTS donation_purchase (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    donation_key VARCHAR(30) NOT NULL,
    badge_label VARCHAR(50) NOT NULL,
    price_points INTEGER NOT NULL,
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, donation_key)
);

CREATE TABLE IF NOT EXISTS user_powerup (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, kind)
);

CREATE TABLE IF NOT EXISTS powerup_purchase (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(20) NOT NULL,
    price_points INTEGER NOT NULL,
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS participation_user_idx
    ON participation (user_id, registered_at DESC);
CREATE INDEX IF NOT EXISTS powerup_purchase_user_idx
    ON powerup_purchase (user_id, purchased_at DESC);

INSERT INTO topic (id, title_tr, title_en, body_tr, body_en) VALUES
    (1, 'Bileşik faiz', 'Compound interest', 'Kazanılan faiz anaparaya eklenir ve yeniden faiz getirir. Erken başlamak süreyi en değerli girdi hâline getirir.', 'Interest earned is added to the principal and starts earning interest itself. Starting early makes time your most valuable asset.'),
    (2, 'Enflasyon ve alım gücü', 'Inflation and purchasing power', 'Fiyatlar sürekli yükselir, aynı para zamanla daha az şey alır. Getiri enflasyonun altında kalırsa reel olarak kayıp vardır.', 'Prices keep rising, so the same money buys less over time. If your return falls below inflation, you lose value in real terms.'),
    (3, 'Çeşitlendirme', 'Diversification', 'Birikimi farklı varlıklara dağıtmak tek bir varlığın kötü gitmesinin etkisini azaltır. Aynı sektördeki varlıklar aynı şoklara birlikte maruz kalır.', 'Spreading your savings across different assets reduces the impact of any single asset performing poorly. Assets in the same sector are exposed to the same shocks together.'),
    (4, 'Risk ve getiri', 'Risk and return', 'Yüksek getiri kural olarak yüksek belirsizlikle gelir. Risksiz ve yüksek getiri bir arada vaat ediliyorsa risk muhtemelen gizlenmiştir.', 'Higher returns generally come with higher uncertainty. If risk-free and high returns are promised together, the risk is probably being hidden.'),
    (5, 'Acil durum fonu', 'Emergency fund', 'Beklenmedik giderlerde borçlanmadan dayanmayı sağlayan rezervdir. İhtiyaç anında hızla ve değer kaybetmeden nakde çevrilebilmelidir.', 'A reserve that lets you cover unexpected expenses without borrowing. It should be quickly convertible to cash without losing value when needed.'),
    (6, 'Borç ve kredi yönetimi', 'Debt and credit management', 'Asgari ödeme borcu bitirmez, kalan tutara faiz işlemeye devam eder. Ödeme geçmişi kredi notunu en çok etkileyen unsurdur.', 'Paying the minimum does not clear the debt; interest keeps accruing on the remaining balance. Payment history is the factor that most affects your credit score.')
ON CONFLICT (id) DO UPDATE SET
    title_tr = EXCLUDED.title_tr,
    title_en = EXCLUDED.title_en,
    body_tr = EXCLUDED.body_tr,
    body_en = EXCLUDED.body_en;

INSERT INTO question (
    id, topic_id, text_tr, text_en, options, correct_index,
    education_note_tr, education_note_en, difficulty, timer_seconds
) VALUES
    (1, 1,
     'Aynı faiz oranı ve aynı anapara ile 10 yıl yatırım yapan iki kişiden biri basit, diğeri bileşik faiz kullanıyor. Aradaki farkın temel nedeni nedir?',
     'Two people invest for 10 years with the same interest rate and principal. One uses simple interest and the other compound interest. What mainly causes the difference?',
     '[{"tr":"Bileşik faizde oran her yıl otomatik olarak yükseltilir","en":"The compound rate automatically increases every year"},{"tr":"Bileşik faizde kazanılan faiz de faiz getirmeye başlar","en":"Earned interest starts earning interest too"},{"tr":"Basit faizde vergi kesintisi daha yüksektir","en":"Tax is higher with simple interest"},{"tr":"Basit faizde anapara her yıl azaltılır","en":"The principal is reduced every year"}]'::jsonb,
     1,
     'Bileşik faizde kazanç anaparaya eklenir; büyüyen tutar yeniden faiz getirir.',
     'With compound interest, earnings are added to principal and the larger amount earns interest again.',
     'orta', 10),
    (2, 2,
     'Yıllık getirisi %30 olan bir yatırım, enflasyonun %45 olduğu bir yılda ne anlama gelir?',
     'What does a 30% annual return mean in a year when inflation is 45%?',
     '[{"tr":"Reel olarak kazanç sağlanmıştır","en":"A real gain was achieved"},{"tr":"Reel olarak kayıp yaşanmıştır","en":"A real loss occurred"},{"tr":"Reel getiri tam olarak sıfırdır","en":"Real return is exactly zero"},{"tr":"Enflasyon reel getiriyi etkilemez","en":"Inflation does not affect real return"}]'::jsonb,
     1,
     'Nominal getiri enflasyonun altında kaldığında alım gücü azalır.',
     'Purchasing power falls when nominal return remains below inflation.',
     'orta', 10),
    (3, 3,
     'Bir yatırımcı tüm birikimini aynı sektördeki beş farklı şirkete dağıtıyor. Bu neden tam bir çeşitlendirme sayılmaz?',
     'An investor spreads all savings across five companies in the same sector. Why is this not full diversification?',
     '[{"tr":"Beş varlık çeşitlendirme için yetersizdir","en":"Five assets are not enough"},{"tr":"Aynı sektördeki varlıklar benzer risklerden birlikte etkilenir","en":"Assets in the same sector are affected by similar risks"},{"tr":"Çeşitlendirme yalnızca farklı ülkelerde yapılabilir","en":"Diversification only works across countries"},{"tr":"Hisseler çeşitlendirmeye uygun değildir","en":"Stocks are unsuitable for diversification"}]'::jsonb,
     1,
     'Aynı sektördeki varlıklar benzer şoklardan birlikte etkilenebilir.',
     'Assets in the same sector can be affected by the same shocks.',
     'zor', 10),
    (4, 4,
     'Garantili, risksiz, aylık %20 getiri vaat eden bir teklif için hangisi doğrudur?',
     'Which statement is true about an offer promising a guaranteed, risk-free 20% monthly return?',
     '[{"tr":"Getirisi yüksek olduğu için tercih edilmelidir","en":"It should be preferred for its high return"},{"tr":"Risk-getiri ilişkisine aykırıdır; riski gizlenmiş olabilir","en":"It contradicts the risk-return relationship and may hide risk"},{"tr":"Yalnızca uzun vadede risklidir","en":"It is risky only in the long term"},{"tr":"Sabit oran riski kaldırır","en":"A fixed rate removes risk"}]'::jsonb,
     1,
     'Yüksek getiri genellikle yüksek belirsizlikle birlikte gelir.',
     'High returns generally come with high uncertainty.',
     'kolay', 10),
    (5, 5,
     'Acil durum fonu için aşağıdaki saklama biçimlerinden hangisi en uygundur?',
     'Which storage method is most suitable for an emergency fund?',
     '[{"tr":"Erken çıkış cezalı beş yıllık ürün","en":"A five-year product with an exit penalty"},{"tr":"Hızla nakde çevrilebilen likit araç","en":"A liquid instrument convertible to cash quickly"},{"tr":"Yüksek riskli varlık","en":"A high-risk asset"},{"tr":"Satışı haftalar süren fiziksel varlık","en":"A physical asset that takes weeks to sell"}]'::jsonb,
     1,
     'Acil durum fonunda amaç yüksek getiri değil, güvenli ve hızlı erişimdir.',
     'The purpose of an emergency fund is safe and quick access, not high return.',
     'kolay', 10),
    (6, 6,
     'Kredi kartı ekstresinde yalnızca asgari tutarı ödeyen biri için hangisi doğrudur?',
     'Which statement is true for someone who pays only the minimum credit-card amount?',
     '[{"tr":"Kalan borç faizsiz devreder","en":"The balance carries over interest-free"},{"tr":"Ödenmeyen tutara faiz işler ve borç büyür","en":"Interest accrues and debt grows"},{"tr":"Kart limiti otomatik yükselir","en":"The limit automatically increases"},{"tr":"Harcamalar iptal edilir","en":"Purchases are cancelled"}]'::jsonb,
     1,
     'Asgari ödeme borcu kapatmaz; kalan tutara faiz işlemeye devam eder.',
     'The minimum payment does not clear the balance; interest keeps accruing.',
     'kolay', 10),
    (7, NULL,
     '50/30/20 bütçe kuralında yüzde 20 neyi ifade eder?',
     'What does the 20% portion represent in the 50/30/20 budget rule?',
     '[{"tr":"Zorunlu giderleri","en":"Essential expenses"},{"tr":"Birikim ve borç kapatmayı","en":"Savings and debt repayment"},{"tr":"Kişisel harcamaları","en":"Personal spending"},{"tr":"Vergi ödemelerini","en":"Tax payments"}]'::jsonb,
     1,
     'Yüzde 20 birikim ve borç kapatmaya ayrılır.',
     'Twenty percent is allocated to savings and debt repayment.',
     'kolay', 10),
    (8, 6,
     'Kredi notunu en olumsuz etkileyen davranış hangisidir?',
     'Which behavior most negatively affects a credit score?',
     '[{"tr":"Kartı hiç kullanmamak","en":"Never using a card"},{"tr":"Ödemeleri düzenli geciktirmek","en":"Regularly making late payments"},{"tr":"Birden fazla banka hesabı olması","en":"Having multiple bank accounts"},{"tr":"Otomatik ödeme vermek","en":"Setting up automatic payments"}]'::jsonb,
     1,
     'Ödeme geçmişi kredi notunun en önemli unsurlarındandır.',
     'Payment history is one of the most important factors in a credit score.',
     'orta', 10),
    (9, NULL,
     'Vadeli mevduatta brüt faiz ile net faiz arasındaki fark neden oluşur?',
     'What causes the difference between gross and net interest on a term deposit?',
     '[{"tr":"Hesap işletim ücreti","en":"Account fee"},{"tr":"Faiz gelirinden stopaj kesintisi","en":"Withholding tax on interest income"},{"tr":"Enflasyon değişimi","en":"Inflation changes"},{"tr":"Kur farkı","en":"Exchange-rate difference"}]'::jsonb,
     1,
     'Faiz gelirinden yasal stopaj kesintisi yapılır.',
     'Statutory withholding tax is deducted from interest income.',
     'zor', 10),
    (10, 4,
     'Ağırlıklı olarak hisse tutan bir yatırımcı emekliliğine iki yıl kala ne yapmalıdır?',
     'What should a stock-heavy investor do two years before retirement?',
     '[{"tr":"Riski artırmalıdır","en":"Increase risk"},{"tr":"Düşük riskli araçların payını artırmalıdır","en":"Increase lower-risk assets"},{"tr":"Tek hisseye geçmelidir","en":"Move into one stock"},{"tr":"Portföyü değiştirmemelidir","en":"Never change the portfolio"}]'::jsonb,
     1,
     'Hedef yaklaştıkça kayıpları telafi etme süresi azalır; risk kademeli düşürülebilir.',
     'As the goal approaches, recovery time shrinks and risk can be reduced gradually.',
     'orta', 10)
ON CONFLICT (id) DO UPDATE SET
    topic_id = EXCLUDED.topic_id,
    text_tr = EXCLUDED.text_tr,
    text_en = EXCLUDED.text_en,
    options = EXCLUDED.options,
    correct_index = EXCLUDED.correct_index,
    education_note_tr = EXCLUDED.education_note_tr,
    education_note_en = EXCLUDED.education_note_en,
    difficulty = EXCLUDED.difficulty,
    timer_seconds = EXCLUDED.timer_seconds;

SELECT setval(pg_get_serial_sequence('topic', 'id'), (SELECT max(id) FROM topic), true);
SELECT setval(pg_get_serial_sequence('question', 'id'), (SELECT max(id) FROM question), true);

COMMIT;
