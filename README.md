<div align="center">

# POLIFIN

### Zahmetsiz bir yatırım deneyimi için &nbsp;·&nbsp; For an effortless investing experience

**Akıllı Kişisel Finans Danışmanı** — çoklu ajan mimarisi, RAG ve MCP tabanlı, Türkçe konuşan yapay zekâ destekli yatırım platformu.<br>
**Smart Personal Finance Advisor** — a Turkish-speaking, AI-powered investing platform built on a multi-agent architecture, RAG and MCP.

*InternTech 2026 · Team Policommittee (Ekip 4)*

[![Backend CI](https://github.com/Policommitte/finans-danismani/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/Policommitte/finans-danismani/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/Policommitte/finans-danismani/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/Policommitte/finans-danismani/actions/workflows/frontend-ci.yml)
![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C)
![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL_16-pgvector-4169E1?logo=postgresql&logoColor=white)

**[Türkçe](#türkçe)** &nbsp;·&nbsp; **[English](#english)** &nbsp;·&nbsp; **[Demo videoları / Demo videos](#demo)**

<a href="docs/media/videos/01-genel-bakis.mp4"><img src="docs/media/gifs/01-genel-bakis.gif" alt="Polifin genel bakış / Polifin overview" width="820"></a>

</div>

> [!IMPORTANT]
> **TR —** Polifin bir staj/eğitim projesidir. Tüm alım-satım işlemleri **sanal portföyde** gerçekleşir, banka hesabı bağlama ekranı simülasyondur ve platformun ürettiği hiçbir içerik **yatırım tavsiyesi değildir**.<br>
> **EN —** Polifin is an internship/educational project. All trades run against a **virtual portfolio**, the bank-linking screen is a simulation, and nothing the platform produces is **investment advice**.

---

<a id="demo"></a>

## Demo videoları · Demo videos

Önizlemeler hızlandırılmış GIF'lerdir; **tam videoyu açmak için görsele tıklayın**. &nbsp;/&nbsp; Previews are sped-up GIFs; **click any preview to open the full video**. Videolardaki kişi ve hesap verileri kurgusaldır. / All people and account data in the videos are fictional.

<table>
<tr>
<td width="50%" valign="top">

**1 · Genel bakış / Overview**

<a href="docs/media/videos/01-genel-bakis.mp4"><img src="docs/media/gifs/01-genel-bakis.gif" alt="Genel bakış"></a>

Giriş, hesap bağlama (simülasyon), dashboard, portföy dağılımı ve işlem geçmişi.<br>
<sub>Login, simulated account linking, dashboard, allocation and transaction history.</sub>

</td>
<td width="50%" valign="top">

**2 · Belge analizi + RAG / Document analysis + RAG**

<a href="docs/media/videos/02-rag-belge-analizi.mp4"><img src="docs/media/gifs/02-rag-belge-analizi.gif" alt="Belge analizi"></a>

Yüklenen hesap ekstresi PDF'i analiz edilir, aylık yatırılabilir tutar hesaplanır ve özet rapor PDF olarak üretilir.<br>
<sub>An uploaded bank statement PDF is analysed, the monthly investable amount is computed, and a summary report PDF is generated.</sub>

</td>
</tr>
<tr>
<td valign="top">

**3 · Yatırım paketleri / Investment packages**

<a href="docs/media/videos/03-yatirim-paketleri.mp4"><img src="docs/media/gifs/03-yatirim-paketleri.gif" alt="Yatırım paketleri"></a>

"Yatırım yapmak istiyorum" rehberli akışı: bütçe, vade, risk ve amaç sorularından hazır pakete ve tek tuşla emre.<br>
<sub>The guided "I want to invest" flow: from budget, horizon, risk and goal questions to a ready-made package and one-click orders.</sub>

</td>
<td valign="top">

**4 · Polifin AI sohbet / Polifin AI chat**

<a href="docs/media/videos/04-polifin-ai-sohbet.mp4"><img src="docs/media/gifs/04-polifin-ai-sohbet.gif" alt="Polifin AI sohbet"></a>

Portföy riski sorusu, haber araştırması, varlık bazında AI analizi ve sohbetten onaylı emir ("asels 16 lot alalım").<br>
<sub>Portfolio risk Q&A, news research, per-asset AI analysis, and a confirmed order placed straight from chat.</sub>

</td>
</tr>
<tr>
<td valign="top">

**5 · Güvenlik ajanı / Security agent**

<a href="docs/media/videos/05-guvenlik-ajani.mp4"><img src="docs/media/gifs/05-guvenlik-ajani.gif" alt="Güvenlik ajanı"></a>

Prompt injection ve başka bir müşterinin verisini kimlik numarasıyla isteme denemesi, akış başlamadan reddedilir.<br>
<sub>A prompt-injection attempt asking for another customer's data is rejected before the pipeline even starts.</sub>

</td>
<td valign="top">

**6 · Otonom işlemler / Autonomous recommendations**

<a href="docs/media/videos/06-otonom-islemler.mp4"><img src="docs/media/gifs/06-otonom-islemler.gif" alt="Otonom işlemler"></a>

Kullanıcı sormadan gelen gerekçeli öneri kartları (Onayla / Reddet), işlem ekranı ve hazır sepetler.<br>
<sub>Unprompted, explained recommendation cards (Approve / Reject), the trading screen and ready-made baskets.</sub>

</td>
</tr>
<tr>
<td valign="top">

**7 · Bülten / Newsletter**

<a href="docs/media/videos/07-bulten.mp4"><img src="docs/media/gifs/07-bulten.gif" alt="Bülten"></a>

Piyasa haberleri ve her haberin kullanıcının kendi portföyüne etkisi.<br>
<sub>Market news, each linked to its impact on the user's own portfolio.</sub>

</td>
<td valign="top">

**8 · Müşteri kazanımı / Customer acquisition**

<a href="docs/media/videos/08-musteri-kazanimi.mp4"><img src="docs/media/gifs/08-musteri-kazanimi.gif" alt="Müşteri kazanımı"></a>

Danışman paneli: atıl bakiyesi olan müşterileri bulan lead motoru, durum takibi ve e-posta teması.<br>
<sub>Advisor panel: a lead engine that surfaces customers with idle balances, with status tracking and e-mail outreach.</sub>

</td>
</tr>
<tr>
<td valign="top">

**9 · Şans Yatırımda**

<a href="docs/media/videos/09-sans-yatirimda.mp4"><img src="docs/media/gifs/09-sans-yatirimda.gif" alt="Şans Yatırımda"></a>

Finansal okuryazarlık bilgi yarışması: puan, lider tablosu ve ödül mağazası.<br>
<sub>A financial-literacy quiz game with points, a leaderboard and a reward store.</sub>

</td>
<td valign="top">
</td>
</tr>
</table>

---

# Türkçe

**İçindekiler:** [Polifin nedir?](#polifin-nedir) · [Problem](#problem) · [Özellikler](#özellikler) · [Mimari](#mimari) · [Teknoloji yığını](#teknoloji-yığını) · [Hızlı başlangıç](#hızlı-başlangıç) · [Test ve kalite](#test-ve-kalite) · [Proje yapısı](#proje-yapısı) · [Durum ve bilinen sınırlar](#durum-ve-bilinen-sınırlar) · [Dokümanlar](#dokümanlar) · [Ekip](#ekip)

## Polifin nedir?

Polifin, bireysel yatırımcının portföyünü, piyasayı ve riskini tek ekranda toplayan; sorularını Türkçe yanıtlayan ve gerektiğinde kullanıcı sormadan öneri getiren bir kişisel finans danışmanıdır. Tek bir büyük modele her şeyi sormak yerine, her biri kendi alanında uzman ve yetkileri birbirinden ayrılmış ajanlar birlikte çalışır; cevaplar kaynağa dayanır, sayılar dil modelinden değil veritabanından ve deterministik hesaplardan gelir.

Proje, InternTech 2026 staj programı kapsamında 11 kişilik bir ekip tarafından dört haftada (haftalık sprintlerle) ve sıfır bütçeyle, tamamen ücretsiz API katmanları üzerinde geliştirildi.

## Problem

| | |
|---|---|
| **%8** | Türkiye'de bakiyeli pay senedi yatırımcısının nüfusa oranı (MKK, 2026 başı) |
| **%20** | ABD hanehalkında, 401(k) emeklilik sistemi hariç borsa yatırımı oranı (SCF ve Gallup) |
| **%57** | Daha fazla boş zamanı olsa daha fazla yatırım yapacağını söyleyen mevcut yatırımcılar (WEF 2024, 13 ülke) |
| **24 dk** | Yetişkinlerin kişisel finans yönetimine haftada ayırdığı ortalama süre (Moneybox ve OnePoll 2024, Birleşik Krallık) |

İnsanlar yatırım yapmak istiyor; ancak gündemi takip etmeye, bilgi kirliliğini ayıklamaya ve karar vermeye ayıracak zamanları yok. Özel yatırım danışmanlığı ise ölçeklenmiyor. Sunumdaki modele göre (TÜİK 2025, Dünya Bankası 2024, TBB 2025 ve BDDK 2025 verileri üzerinden kurulan ekip tahmini):

| | Polifin | Özel yatırım danışmanı |
|---|---|---|
| Hizmet verilebilecek kullanıcı sayısı | ~1.450.000* | 150 |
| Müşteri başına maliyet | 8,15 ₺ | 1.151 ₺ |
| Aylık müşteri kazanım hızı | 2.000 müşteri | 1,7 müşteri |

<sub>* 25–45 yaş aralığında, Türkiye'deki tüm bankalarda 121.786 TL – 1 milyon TL arasında yatırım yapılabilir bakiyeye sahip hesap sayısı.</sub>

## Özellikler

**Polifin AI (yatırım asistanı).** Portföy, piyasa ve risk sorularını Türkçe yanıtlar; cevap SSE ile canlı akar. Sohbet geçmişi saklanır, sohbetten onaylı emir verilebilir ve her finansal yanıt "yatırım tavsiyesi değildir" ibaresini taşır.

**Belge ve görsel analizi.** Yüklenen PDF, Excel veya görsel finansal belgeler (örneğin başka bir bankanın hesap ekstresi) ayrıştırılır, sayısal göstergeler çıkarılır ve grafikli bir özet rapor PDF olarak üretilir.

**Rehberli yatırım paketleri.** "Yatırım yapmak istiyorum" akışı sohbet içinde dört soru sorar (bütçe, vade, risk, amaç), uygun hazır paketi önerir ve paketi sanal hesapta tek tuşla piyasa emrine çevirir.

**Otonom öneri motoru.** Piyasa ve haber verisi sürekli taranır; sinyalleri LLM değil deterministik bir kural motoru üretir. Güven eşiğini ve kullanıcının risk profiline uyumu geçen sinyaller, kural adı ve gerekçesiyle birlikte öneri kartına dönüşür. Elenen sinyaller de gerekçesiyle kayda geçer.

**İşlem ve portföy.** Sanal portföyde piyasa ve limit emirleri, koruyucu stop-loss, komisyon hesabı, hazır sepetler, atıl nakit uyarıları, portföy performansı ve varlık dağılımı.

**Piyasa ve teknik analiz.** Yahoo Finance üzerinden periyodik güncellenen BIST, ABD hisseleri, kripto, döviz, altın ve emtia fiyatları; teknik gösterge özeti (al / nötr / sat), fiyat alarmı ve isteğe bağlı TimesFM tabanlı tahmin bandı.

**Risk paneli.** Deterministik 0–100 risk skoru, kullanıcının beyan ettiği risk toleransıyla karşılaştırma, skoru yükselten etkenler ve öneriler.

**Bülten ve ekonomik takvim.** Haber arşivinden derlenen bülten; her haber kullanıcının portföyündeki ilgili pozisyonla ilişkilendirilir.

**Müşteri kazanımı (danışman paneli).** Lead motoru atıl bakiyesi olan veya hareketsiz kalan müşterileri kurallarla belirler; danışman durumları takip eder ve e-posta ile temas kurar. Aynı müşteriye aynı gün iki kez temas veritabanı düzeyinde engellenir.

**Şans Yatırımda.** Finansal okuryazarlığı oyunlaştıran bilgi yarışması: puan, lider tablosu, joker ve ödül mağazası.

**Arayüz.** Türkçe ve İngilizce dil desteği, açık ve koyu tema, ilk kullanım turu, onboarding ve duyarlı tasarım.

## Mimari

Her soru aynı hattan geçer: giriş denetimi, yönlendirme, paralel çalışan uzman ajanlar, onlara bağımlı risk ajanı, çıkış denetimi ve tek sesli sentez.

![Ajan akışı](docs/media/diagrams/ajan-akisi.png)

| Ajan | Görevi |
|---|---|
| **Portföy Ajanı** | Kullanıcının bakiye, pozisyon ve getiri verisini veritabanından analiz edip özetler. |
| **Piyasa Ajanı** | Canlı fiyat, duyuru ve haber arşivinden, bahsedilen varlıklar hakkında güncel bilgi toplar. |
| **Döküman Ajanı** | Yüklenen PDF / Excel / görsel finansal belgeleri analiz edip özet PDF üretir. |
| **Risk Ajanı** | Portföy ve piyasa verisine dayanarak deterministik risk skorunu yorumlar, stratejik öneri sunar. |
| **Güvenlik Ajanı** | Akışın başında girişi, sentezden önce ajan çıktılarını denetler. |

Piyasa, portföy ve döküman ajanları paralel; risk ajanı onların çıktısına bağlı olduğu için sıralı çalışır. Bir ajan başarısız olursa akış düşmez, kalan ajanların çıktısıyla yanıt üretilir. Ajanlar veriye doğrudan değil, tek bir **MCP sunucusundaki** araç grupları (`portfolio_*`, `market_*`, `rag_*`) üzerinden ve ajan bazlı yetkilendirmeyle erişir; örneğin piyasa ajanı portföy araçlarını çağıramaz.

### RAG hattı

![RAG pipeline](docs/media/diagrams/rag-pipeline.png)

Arama PostgreSQL içinde çalışır: pgvector ile anlamsal (dense) arama ve `tsvector` tabanlı sözlüksel (BM25 benzeri) arama ayrı ayrı sıralanır, sonuçlar Reciprocal Rank Fusion ile birleştirilir ve kosinüs benzerliği eşiğinden geçirilir. Embedding sağlayıcısı tanımlı değilse veya sorgu anında zaman aşımına uğrarsa istek düşmez, arama sessizce sözlüksel ayağa iner. Yanıtlar kaynak gösterir.

### Öneri motoru

![Öneri motoru](docs/media/diagrams/oneri-motoru.png)

### Güvenlik

![Güvenlik katmanları](docs/media/diagrams/guvenlik-katmanlari.png)

Güvenlik iki noktada uygulanır. **Giriş denetimi** prompt injection, yetkisiz komut, kapsam dışı istek ve kişisel veri taleplerini akış başlamadan yakalar; önce Türkçe normalizasyonlu bir kural motoru çalışır, yalnızca şüpheli durumda LLM'e başvurulur. **Çıkış kapısı** sentezden önce çalışır, çünkü kullanıcıya akıtılan token geri alınamaz; habere veya rapora gömülü dolaylı saldırılar burada durur. Parolalar bcrypt (salt dahil) ile özetlenir, oturumlar imzalı JWT ile taşınır.

## Teknoloji yığını

| Katman | Teknolojiler |
|---|---|
| Backend | Python 3.13 · FastAPI · Pydantic · SQLAlchemy (async) · SSE |
| Orkestrasyon | LangGraph · LangChain Core · tek MCP sunucusu (araç grupları + ajan yetkilendirmesi) |
| Modeller | NVIDIA Nemotron (NIM) · Google Gemini · OpenRouter (yedek sağlayıcı) · TimesFM (isteğe bağlı tahmin) |
| RAG | PostgreSQL 16 + pgvector (`vector(1024)`, HNSW) · Cohere `embed-v4.0` · hibrit arama + RRF |
| Piyasa verisi | yfinance (Yahoo Finance) · pandas · pandas-ta-classic |
| Belgeler | pdfplumber · openpyxl · ReportLab · matplotlib |
| Kimlik | PyJWT · bcrypt |
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS · Recharts · lightweight-charts · Framer Motion |
| Kalite | pytest · ruff · black · Vitest · GitHub Actions |

Model adları koda sabit yazılmaz; her ajanın modeli `.env` üzerinden ayrı ayrı seçilir (`DEFAULT_MODEL`, `SECURITY_MODEL`, `SYNTHESIZER_MODEL`, ...).

## Hızlı başlangıç

Gereksinimler: Python 3.13, Node.js 20+, Docker (veritabanı için, isteğe bağlı).

**1 · Veritabanı (isteğe bağlı ama önerilir)**

```bash
docker compose up -d db      # şema + örnek veri ilk kalkışta otomatik yüklenir
```

**2 · Backend**

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env              # ardından .env içini doldurun (aşağıya bakın)
uvicorn app.main:app --reload --reload-dir app     # Windows: python run.py
```

Swagger: <http://localhost:8000/docs> · Sağlık: <http://localhost:8000/health>

**3 · Frontend**

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Frontend varsayılan olarak `http://localhost:8000` adresindeki API'ye bağlanır; değiştirmek için `NEXT_PUBLIC_API_BASE_URL` tanımlayın.

**Demo hesapları (yerel örnek veri):** müşteri `mehmet@example.com`, danışman `danisman@example.com`; tüm örnek kullanıcıların şifresi `demo1234`.

### Kademeli çalışma

Sistem aşağıdakilerin hiçbiri olmadan da uçtan uca çalışır; her biri bağımsız olarak açılır.

| `.env` içinde eksik olan | Ne olur |
|---|---|
| `DATABASE_URL` | Repository katmanı bellek içi temel kayıtlara düşer; fiyat ve performans geçmişi üretilmez. |
| `LLM_API_KEY` / model adı | Ajanlar LLM'siz çalışır; kaynaklardan deterministik alıntı ve özet üretir. |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | `rag_search` yalnızca sözlüksel ayakla çalışır; tanımlandığında hibrit arama devreye girer. |
| `FORECAST_MODEL` (+ torch, timesfm) | Grafiklerde tahmin bandı çizilmez; gerisi aynen çalışır. |

Yerel veritabanı için: `DATABASE_URL=postgresql+psycopg://finans:finans@localhost:5432/finans`. Tüm ayarlar açıklamalarıyla [`.env.example`](.env.example) içindedir. Gerçek API anahtarlarını asla commit etmeyin.

## Test ve kalite

```bash
cd backend && pytest -q                    # 1.090 test; veritabanı ve ağ gerektirmez
cd backend && ruff check . && black --check .
cd frontend && npm test
```

Backend testleri katmana göre klasörlenmiştir (`unit`, `agents`, `services`, `api`, `integration`). Test paketi dış ağa çıkamaz; gerçek PostgreSQL isteyen entegrasyon testleri yalnızca `TEST_DATABASE_URL` tanımlıyken çalışır. `main` dalı korumalıdır: her değişiklik PR, en az bir onay ve yeşil CI ile birleşir. Ayrıntılar: [backend/README.md](backend/README.md), [CONTRIBUTING.md](CONTRIBUTING.md).

## Proje yapısı

```
backend/         FastAPI uygulaması
  app/agents/        uzman ajanlar (portföy, piyasa, risk, döküman, güvenlik)
  app/engine/        LangGraph orkestratörü, yönlendirme, sentez, kapsam denetimi
  app/mcp/           MCP sunucusu, istemcisi ve ajan yetkilendirmesi
  app/ingestion/     chunking, embedding, backfill
  app/signals/       deterministik sinyal (kural) motoru
  app/services/      domain servisleri (öneri, paket, işlem, lead, bülten, yarışma, ...)
  app/repositories/  veri erişim katmanı (SQL + bellek içi)
  app/market/        fiyat sağlayıcısı, zamanlayıcı, teknik göstergeler
  app/documents/     belge ayrıştırma, görsel analiz, PDF rapor
  app/forecast/      isteğe bağlı zaman serisi tahmini
  tests/             unit · agents · services · api · integration
frontend/        Next.js arayüzü (dashboard, portföy, piyasa, işlemler, öneriler,
                 bülten, danışman paneli, Şans Yatırımda, raporlar, profil)
db/              PostgreSQL + pgvector şeması, örnek veri ve migration'lar
borsa-verisi/    Yahoo Finance → PostgreSQL tek seferlik veri toplama betiği
docs/            mimari, API sözleşmesi, kararlar, tanıtım medyası
```

## Durum ve bilinen sınırlar

Proje, InternTech 2026 final sunumundaki hâliyle çalışır durumdadır. Bir staj projesi olduğu için aşağıdaki noktaları açıkça belirtmek isteriz:

- İşlemler sanal portföyde gerçekleşir; gerçek bir aracı kuruma emir iletilmez. Banka hesabı bağlama ekranı simülasyondur, hesap numarası doğrulanmaz.
- Duyuru ve haberler RAG indeksindeki arşivden okunur; canlı bir KAP API entegrasyonu yoktur.
- Hibrit aramanın anlamsal ayağı bir embedding API anahtarı gerektirir; anahtar yoksa sistem sözlüksel aramayla çalışmaya devam eder.
- Fiyat tahmini bir kesinlik iddiası değildir: ölçümlerimizde TimesFM tabanlı yapılandırma naive tabanı yalnızca az farkla geçti (MAPE %6,93'e karşı %7,07); asıl değer %80 tahmin bandının kalibrasyonundadır (ölçülen kapsam %79,1).
- Sunumda hedef mimari olarak anlatılan uçtan uca şifreli konuşmalar henüz kodda yoktur. Bugün mevcut olanlar: bcrypt + salt parola özeti, imzalı JWT oturumu ve iki aşamalı güvenlik ajanı.
- Yahoo Finance resmî bir API değildir. Erişilemediğinde son doğrulanmış fiyat korunur, sentetik fiyat üretilmez.
- Frontend test kapsamı backend'e göre bilinçli olarak dardır.

## Dokümanlar

- [Sistem mimarisi (v4)](SYSTEM_ARCHITECTURE_v4.md) — tek geçerli mimari referans
- [API sözleşmesi](docs/api-sozlesmesi.md) — REST uçları, hata gövdesi, SSE olayları
- [Backend kararları](docs/backend-kararlar.md) · [RAG ajanı ve MCP katmanı](docs/rag-agent-ve-mcp-katmani.md) · [Gelecek işler](docs/gelecek-isler.md)
- [Backend README](backend/README.md) · [Veritabanı README](db/README.md) · [Katkı rehberi](CONTRIBUTING.md)

## Ekip

**Team Policommittee — InternTech 2026, Ekip 4**

| Rol | İsimler |
|---|---|
| Scrum Master | Arda Uzan |
| İş Analistleri | Kerem Yoldaş · Fatih Akçay · Efkan Çıtak |
| Yapay Zekâ | Öykü Yaşar · Berkay Öztürk |
| Backend | Eren Ünel · Yağız Eren Koşar · Berat Efe Uğurlu |
| Frontend | Efe Özekici · Erkin Menekşe |

<div align="right"><a href="#polifin">↑ başa dön</a></div>

---

# English

**Contents:** [What is Polifin?](#what-is-polifin) · [The problem](#the-problem) · [Features](#features) · [Architecture](#architecture) · [Tech stack](#tech-stack) · [Quick start](#quick-start) · [Testing and quality](#testing-and-quality) · [Repository layout](#repository-layout) · [Status and known limitations](#status-and-known-limitations) · [Documentation](#documentation) · [Team](#team)

## What is Polifin?

Polifin is a personal finance advisor that puts a retail investor's portfolio, the market and their risk on a single screen, answers questions in Turkish, and brings recommendations without being asked when something is worth acting on. Instead of sending everything to one large model, it runs a set of specialist agents with separated permissions. Answers are grounded in sources, and numbers come from the database and deterministic calculations rather than from a language model.

The project was built for the InternTech 2026 internship programme by a team of eleven in four weeks of weekly sprints, on a zero budget and entirely on free API tiers. The product UI supports both Turkish and English; code comments and internal docs are mostly in Turkish.

## The problem

| | |
|---|---|
| **8%** | Share of Türkiye's population holding equities with a balance (MKK, early 2026) |
| **20%** | US households investing in the stock market outside 401(k) retirement plans (SCF and Gallup) |
| **57%** | Existing investors who say they would invest more if they had more free time (WEF 2024, 13 countries) |
| **24 min** | Average time adults spend on personal finance management per week (Moneybox and OnePoll 2024, UK) |

People want to invest, but they lack the time to follow the news, filter out the noise and make decisions, and private investment advisory does not scale. According to the model in our presentation (a team estimate built on TÜİK 2025, World Bank 2024, TBB 2025 and BDDK 2025 data):

| | Polifin | Private investment advisor |
|---|---|---|
| Users that can be served | ~1,450,000* | 150 |
| Cost per customer | ₺8.15 | ₺1,151 |
| Monthly customer acquisition | 2,000 customers | 1.7 customers |

<sub>* Number of accounts across all banks in Türkiye held by 25–45 year-olds with an investable balance between ₺121,786 and ₺1 million.</sub>

## Features

**Polifin AI (investment assistant).** Answers portfolio, market and risk questions in Turkish with responses streamed live over SSE. Conversation history is kept, orders can be placed from chat after explicit confirmation, and every financial answer carries a "not investment advice" notice.

**Document and image analysis.** Uploaded PDF, Excel or image financial documents (for example a statement from another bank) are parsed, key figures are extracted, and a summary report with charts is generated as a PDF.

**Guided investment packages.** The "I want to invest" flow asks four questions in chat (budget, horizon, risk, goal), proposes a matching ready-made package, and turns it into market orders on the virtual account with one click.

**Autonomous recommendation engine.** Market and news data are scanned continuously; signals are produced by a deterministic rule engine, not an LLM. Signals that pass a confidence threshold and fit the user's risk profile become recommendation cards showing the rule name and its rationale. Suppressed signals are logged with their reason too.

**Trading and portfolio.** Market and limit orders on a virtual portfolio, protective stop-loss, commission calculation, ready-made baskets, idle-cash nudges, portfolio performance and allocation.

**Market and technical analysis.** Periodically refreshed prices from Yahoo Finance for BIST and US equities, crypto, FX, gold and commodities; a technical indicator summary (buy / neutral / sell), price alerts and an optional TimesFM-based forecast band.

**Risk panel.** A deterministic 0–100 risk score, compared against the user's declared risk tolerance, with the drivers behind the score and suggestions.

**Newsletter and economic calendar.** A bulletin compiled from the news archive, with each story linked to the relevant position in the user's portfolio.

**Customer acquisition (advisor panel).** A lead engine uses rules to find customers with idle balances or inactivity; advisors track statuses and reach out by e-mail. Contacting the same customer twice on the same day is prevented at the database level.

**Şans Yatırımda.** A quiz game that gamifies financial literacy, with points, a leaderboard, lifelines and a reward store.

**Interface.** Turkish and English, light and dark themes, a first-run tour, onboarding and responsive layout.

## Architecture

Every question travels the same pipeline: an input check, routing, specialist agents running in parallel, a risk agent that depends on them, an output gate, and a single-voice synthesis step.

```mermaid
flowchart LR
    Q([Question]) --> S1[Security<br/>input check]
    S1 -- suspicious --> R[Refusal /<br/>out-of-scope reply]
    S1 --> RT[Router<br/>who should run?]
    RT --> M[Market research]
    RT --> P[Portfolio analysis]
    RT --> D[Document analysis]
    M --> RS[Risk & strategy<br/>depends on the others]
    P --> RS
    D --> RS
    RS --> S2[Security gate<br/>output check]
    S2 --> SY[Synthesis<br/>single-voice answer]
    SY --> A([Live SSE stream])
```

| Agent | Responsibility |
|---|---|
| **Portfolio Agent** | Analyses and summarises the user's balance, positions and returns from the database. |
| **Market Agent** | Gathers up-to-date information on the mentioned assets from live prices, disclosures and the news archive. |
| **Document Agent** | Analyses uploaded PDF / Excel / image financial documents and produces a summary PDF. |
| **Risk Agent** | Interprets the deterministic risk score using portfolio and market data and offers strategic suggestions. |
| **Security Agent** | Checks the input at the start of the pipeline and the agents' outputs before synthesis. |

The market, portfolio and document agents run in parallel; the risk agent runs after them because it depends on their output. If one agent fails, the pipeline does not: the answer is produced from the remaining agents' output. Agents never touch data directly. They go through tool groups (`portfolio_*`, `market_*`, `rag_*`) on a single **MCP server** with per-agent authorisation, so the market agent, for instance, cannot call portfolio tools.

### RAG pipeline

<img src="docs/media/diagrams/rag-pipeline.png" alt="RAG pipeline (labels in Turkish)" width="760">

Retrieval runs inside PostgreSQL. A semantic (dense) search over pgvector and a lexical (BM25-style) search over `tsvector` are ranked separately, merged with Reciprocal Rank Fusion, and filtered by a cosine-similarity threshold. If no embedding provider is configured, or the query-time embedding call times out, the request does not fail and search quietly falls back to the lexical leg. Answers cite their sources.

### Recommendation engine

<img src="docs/media/diagrams/oneri-motoru.png" alt="Recommendation engine (labels in Turkish)" width="760">

Top lane, *autonomous*: news and market scanning, rule engine (no LLM, deterministic), confidence threshold, profile fit, recommendation card with rule name and rationale. Bottom lane, *guided*: four questions in chat, ready-made package scored by the same pipeline, one-click order on the virtual account. The "not investment advice" notice is attached server-side to every recommendation and package.

### Security

<img src="docs/media/diagrams/guvenlik-katmanlari.png" alt="Security layers (labels in Turkish)" width="760">

Security is enforced at two points. The **input check** catches prompt injection, unauthorised commands, out-of-scope requests and requests for personal data before the pipeline starts; a rule engine with Turkish text normalisation runs first, and an LLM is consulted only when the input looks suspicious. The **output gate** runs before synthesis, because a token that has been streamed to the user cannot be taken back; indirect attacks embedded in news or reports are stopped here. Passwords are hashed with bcrypt (salted) and sessions use signed JWTs.

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.13 · FastAPI · Pydantic · SQLAlchemy (async) · SSE |
| Orchestration | LangGraph · LangChain Core · a single MCP server (tool groups + per-agent authorisation) |
| Models | NVIDIA Nemotron (NIM) · Google Gemini · OpenRouter (fallback provider) · TimesFM (optional forecasting) |
| RAG | PostgreSQL 16 + pgvector (`vector(1024)`, HNSW) · Cohere `embed-v4.0` · hybrid search + RRF |
| Market data | yfinance (Yahoo Finance) · pandas · pandas-ta-classic |
| Documents | pdfplumber · openpyxl · ReportLab · matplotlib |
| Auth | PyJWT · bcrypt |
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS · Recharts · lightweight-charts · Framer Motion |
| Quality | pytest · ruff · black · Vitest · GitHub Actions |

Model names are never hard-coded; each agent's model is chosen separately through `.env` (`DEFAULT_MODEL`, `SECURITY_MODEL`, `SYNTHESIZER_MODEL`, ...).

## Quick start

Requirements: Python 3.13, Node.js 20+, Docker (optional, for the database).

**1 · Database (optional but recommended)**

```bash
docker compose up -d db      # schema + sample data load automatically on first start
```

**2 · Backend**

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env              # then fill in .env (see below)
uvicorn app.main:app --reload --reload-dir app     # Windows: python run.py
```

Swagger: <http://localhost:8000/docs> · Health: <http://localhost:8000/health>

**3 · Frontend**

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

The frontend talks to the API at `http://localhost:8000` by default; set `NEXT_PUBLIC_API_BASE_URL` to change it.

**Demo accounts (local sample data):** customer `mehmet@example.com`, advisor `danisman@example.com`; every sample user's password is `demo1234`.

### Graceful degradation

The system runs end to end without any of the following; each can be switched on independently.

| Missing from `.env` | What happens |
|---|---|
| `DATABASE_URL` | The repository layer falls back to basic in-memory records; no price or performance history is produced. |
| `LLM_API_KEY` / model name | Agents run without an LLM and produce deterministic excerpts and summaries from sources. |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | `rag_search` runs on the lexical leg only; hybrid search kicks in once they are set. |
| `FORECAST_MODEL` (+ torch, timesfm) | No forecast band is drawn on charts; everything else works as usual. |

For the local database use `DATABASE_URL=postgresql+psycopg://finans:finans@localhost:5432/finans`. Every setting is documented (in Turkish) in [`.env.example`](.env.example). Never commit real API keys.

## Testing and quality

```bash
cd backend && pytest -q                    # 1,090 tests; no database or network required
cd backend && ruff check . && black --check .
cd frontend && npm test
```

Backend tests are organised by layer (`unit`, `agents`, `services`, `api`, `integration`). The suite is blocked from reaching the external network, and integration tests that need a real PostgreSQL run only when `TEST_DATABASE_URL` is set. The `main` branch is protected: every change lands through a PR with at least one approval and green CI. Details: [backend/README.md](backend/README.md), [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository layout

```
backend/         FastAPI application
  app/agents/        specialist agents (portfolio, market, risk, document, security)
  app/engine/        LangGraph orchestrator, routing, synthesis, scope control
  app/mcp/           MCP server, client and per-agent authorisation
  app/ingestion/     chunking, embeddings, backfill
  app/signals/       deterministic signal (rule) engine
  app/services/      domain services (recommendations, packages, trading, leads, news, contest, ...)
  app/repositories/  data access layer (SQL + in-memory)
  app/market/        price provider, scheduler, technical indicators
  app/documents/     document parsing, vision analysis, PDF reports
  app/forecast/      optional time-series forecasting
  tests/             unit · agents · services · api · integration
frontend/        Next.js UI (dashboard, portfolio, market, trading, recommendations,
                 newsletter, advisor panel, Şans Yatırımda, reports, profile)
db/              PostgreSQL + pgvector schema, sample data and migrations
borsa-verisi/    one-off Yahoo Finance → PostgreSQL data collection script
docs/            architecture, API contract, decisions, showcase media
```

## Status and known limitations

The project works as shown in the InternTech 2026 final presentation. Because it is an internship project, we want to be explicit about the following:

- Trades run on a virtual portfolio; no order is ever sent to a real broker. The bank-linking screen is a simulation and the account number is not verified.
- Disclosures and news are read from the archive in the RAG index; there is no live KAP (Public Disclosure Platform) API integration.
- The semantic leg of hybrid search requires an embedding API key; without one the system keeps working on lexical search.
- Price forecasting is not a claim of certainty: in our measurements the TimesFM-based configuration beat the naive baseline only narrowly (MAPE 6.93% vs 7.07%); the real value is in the calibration of the 80% forecast band (measured coverage 79.1%).
- End-to-end encrypted conversations, presented as the target architecture, are not in the code yet. What exists today: bcrypt + salt password hashing, signed JWT sessions and the two-stage security agent.
- Yahoo Finance is not an official API. When it is unreachable the last verified price is kept; synthetic prices are never generated.
- Frontend test coverage is deliberately narrower than the backend's.

## Documentation

Most internal documentation is in Turkish.

- [System architecture (v4)](SYSTEM_ARCHITECTURE_v4.md) — the single source of truth for the architecture
- [API contract](docs/api-sozlesmesi.md) — REST endpoints, error body, SSE events
- [Backend decisions](docs/backend-kararlar.md) · [RAG agent and MCP layer](docs/rag-agent-ve-mcp-katmani.md) · [Future work](docs/gelecek-isler.md)
- [Backend README](backend/README.md) · [Database README](db/README.md) · [Contributing guide](CONTRIBUTING.md)

## Team

**Team Policommittee — InternTech 2026, Team 4**

| Role | Names |
|---|---|
| Scrum Master | Arda Uzan |
| Business Analysts | Kerem Yoldaş · Fatih Akçay · Efkan Çıtak |
| AI | Öykü Yaşar · Berkay Öztürk |
| Backend | Eren Ünel · Yağız Eren Koşar · Berat Efe Uğurlu |
| Frontend | Efe Özekici · Erkin Menekşe |

<div align="right"><a href="#polifin">↑ back to top</a></div>
