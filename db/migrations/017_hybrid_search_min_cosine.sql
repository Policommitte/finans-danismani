-- rag.hybrid_search: sonuclara ASGARI BENZERLIK esigi (`p_min_cos`) eklenir ve
-- cosine benzerligi `cos_sim` kolonu olarak DISARI VERILIR.
--
-- SORUN
-- -----
-- Fonksiyon "en alakali K" degil "en yakin K" donduruyordu. Cosine mesafesi
-- yalnizca `dense` CTE'sinin ORDER BY'inda hesaplaniyor, SELECT listesine
-- ALINMIYORDU - yani hesaplandigi ifadenin disina hic cikmiyordu. Disari cikan
-- tek skor RRF'tir ve RRF RANK tabanlidir: 1. sira her zaman 1/(60+1)=0.0164
-- eder, sonuc mukemmel de olsa tamamen alakasiz da olsa. Skorun alabilecegi tum
-- aralik ~0.012-0.033 oldugu icin uzerine esik koymak imkansizdi.
--
-- Sonuc: "bankacilik sektorundeki haberleri ozetle" sorgusu insaat ve istihdam
-- haberlerini kaynak olarak gosteriyordu.
--
-- ⚠️ ESIK NEDEN `dense` CTE'SINE KONMADI
-- --------------------------------------
-- `fused` bir FULL OUTER JOIN'dir. Yalnizca BM25 ile eslesen bir chunk - dense
-- top-20'ye HIC girmemis olsa bile - buraya `d.rnk IS NULL` ile girer ve
-- lexical ayagindan gelen skoruyla hayatta kalir. Sorunlu ornek tam olarak
-- buydu: `plainto_tsquery` AND'i OR'a cevrildigi icin (bkz. asagidaki `q` CTE'si)
-- "sektor" kelimesi tek basina eslesiyor ve alakasiz haber listeye giriyordu.
-- Esik yalnizca dense ayaga uygulansaydi bu satirlar filtreye HIC ugramazdi.
--
-- ⚠️ FILTRE `LIMIT`TEN ONCE UYGULANIR
-- -----------------------------------
-- Aday havuzu iki ayaktan p_top_k*4'er satir genisligindedir. Once filtreleyip
-- sonra limitleyerek elenen satirlarin yerine havuzun DERINLIGINDEN gecerli
-- sonuclar cekilir. Ters sirada (once LIMIT, sonra filtre) K'dan cok daha az
-- sonuc kalirdi.
--
-- ⚠️ EMBEDDING'I NULL OLAN CHUNK ELENIR
-- -------------------------------------
-- `NULL >= esik` -> NULL -> satir gecmez. Esik ISTENDIGINDE dogrulanamayan
-- satiri disarida birakmak bilincli tercihtir. `p_min_cos` NULL birakilirsa
-- (varsayilan) hicbir filtre uygulanmaz ve davranis bu migration oncesiyle
-- BIREBIR ayni kalir.
--
-- ⚠️ SAF BM25 YOLU ETKILENMEZ
-- ---------------------------
-- Embedder tanimli degilse (EMBEDDING_API_KEY bos) ya da sorgu-zamani embedding
-- cagrisi basarisiz olursa backend bu fonksiyonu HIC cagirmaz,
-- `SqlRagRepository.search()`e duser (bkz. o sinifin docstring'i). Orada
-- embedding olmadigi icin esik UYGULANAMAZ - ayarin sessizce etkisiz kalmasinin
-- tek nedeni budur.

BEGIN;

-- Donus tipi degistigi icin `CREATE OR REPLACE` YETMEZ: Postgres "cannot change
-- return type of existing function" hatasi verir. Ayrica eski imza bir OVERLOAD
-- olarak kalirsa isimli parametreli cagrilar (`p_query => ...`) belirsiz hale
-- gelir - bu yuzden once eski imza DROP edilir.
DROP FUNCTION IF EXISTS rag.hybrid_search(
    TEXT, vector, INT, INT, TEXT, VARCHAR, DATE, DATE, INT
);

CREATE FUNCTION rag.hybrid_search(
    p_query     TEXT,
    p_embedding vector(1024),                       -- ⚠️ EMBEDDING_DIM 2/2
    p_top_k     INT DEFAULT 5,
    p_asset_id  INT DEFAULT NULL,
    p_sirket    TEXT DEFAULT NULL,
    p_tip       VARCHAR DEFAULT NULL,
    p_date_from DATE DEFAULT NULL,
    p_date_to   DATE DEFAULT NULL,
    p_k_rrf     INT DEFAULT 60,
    p_min_cos   DOUBLE PRECISION DEFAULT NULL
)
RETURNS TABLE (chunk_id INT, document_id INT, content TEXT,
               baslik TEXT, sirket VARCHAR, tarih DATE, tip VARCHAR,
               score DOUBLE PRECISION, cos_sim DOUBLE PRECISION)
LANGUAGE sql STABLE AS $$
-- plainto_tsquery terimleri AND'ler: dogal dildeki bir soruda tum kelimelerin
-- ayni chunk'ta gecmesi neredeyse imkansiz oldugu icin BM25 ayagi sessizce bos
-- doner ve arama saf vektor aramasina duserdi. Bu yuzden OR'a cevriliyor.
-- NULLIF: sorgu yalnizca stopword iceriyorsa tsquery bos kalir, eslesme aranmaz.
WITH q AS (
    SELECT NULLIF(replace(plainto_tsquery('turkish', p_query)::TEXT,
                          ' & ', ' | '), '')::tsquery AS tsq
),
filtered AS (
    -- p_sirket rag.documents.sirket KOLONUNA BAKMAZ: o kolon haberin
    -- KAYNAĞINI tutar (örn. "AA Ekonomi", "BigPara Döviz"), sözü edilen
    -- şirketi değil. Eşleşme yalnızca varlık sembolü/unvanı (assets JOIN'i)
    -- ve başlık üzerinden yapılır - search()'ün BM25 dalındaki fallback ile
    -- aynı mantık (bkz. app/repositories/sql.py::SqlRagRepository.search).
    -- NOT: asset_id bugün neredeyse hiç doldurulmadığı için gerçek veride
    -- bu filtre pratikte yalnızca başlık eşleşmesine dayanır.
    SELECT c.id, c.content, c.embedding, c.content_tsv, c.document_id
    FROM rag.chunks c
    JOIN rag.documents d ON d.id = c.document_id
    LEFT JOIN assets a   ON a.id = d.asset_id
    WHERE (p_asset_id IS NULL OR d.asset_id = p_asset_id)
      AND (p_sirket IS NULL
           OR upper(a.symbol) = upper(p_sirket)
           OR upper(a.name) = upper(p_sirket)
           OR d.baslik ILIKE '%' || p_sirket || '%')
      AND (p_tip IS NULL OR d.tip = p_tip)
      AND (p_date_from IS NULL OR d.tarih >= p_date_from)
      AND (p_date_to IS NULL OR d.tarih <= p_date_to)
),
dense AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> p_embedding) rnk
    FROM filtered WHERE embedding IS NOT NULL
    ORDER BY embedding <=> p_embedding LIMIT p_top_k * 4
),
lexical AS (
    SELECT f.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(f.content_tsv, q.tsq) DESC) rnk
    FROM filtered f CROSS JOIN q
    WHERE f.content_tsv @@ q.tsq
    LIMIT p_top_k * 4
),
fused AS (
    SELECT COALESCE(d.id, l.id) id,
           COALESCE(1.0/(p_k_rrf+d.rnk),0) + COALESCE(1.0/(p_k_rrf+l.rnk),0) rrf
    FROM dense d FULL OUTER JOIN lexical l ON l.id = d.id
),
-- `<=>` pgvector'un COSINE MESAFESIDIR (1 - benzerlik); benzerlige cevirmek
-- icin 1'den cikarilir. Ayri bir CTE'de hesaplanmasinin iki sebebi var:
-- (1) `dense` CTE'si yalnizca rank uretir, mesafeyi disari tasimaz - bu
-- migration'in tum sebebi; (2) ifade WHERE ve SELECT'te tekrarlanmasin.
scored AS (
    SELECT c.id, c.document_id, c.content,
           doc.baslik, doc.sirket, doc.tarih, doc.tip,
           f.rrf,
           (1 - (c.embedding <=> p_embedding))::DOUBLE PRECISION AS cos_sim
    FROM fused f
    JOIN rag.chunks c      ON c.id  = f.id
    JOIN rag.documents doc ON doc.id = c.document_id
)
-- ⚠️ NaN AYRICA ELENIR. pgvector sifir normlu vektorde NaN doner ve Postgres
-- NaN'i TUM sayilardan BUYUK sayar (`'NaN'::float8 >= 0.95` -> true). Salt
-- `>=` yazilsaydi dogrulanamayan satirlar esikten SESSIZCE gecerdi. `<> 'NaN'`
-- calisir cunku Postgres'te `NaN = NaN` dogrudur.
--
-- Kolonlar `s.` ile NITELENIR: RETURNS TABLE adlari (`content`, `cos_sim`...)
-- fonksiyon govdesinde cikti parametresi olarak gorunur ve ciplak kolon adi
-- "column reference is ambiguous" hatasi verirdi.
SELECT s.id, s.document_id, s.content, s.baslik, s.sirket, s.tarih, s.tip,
       s.rrf, s.cos_sim
FROM scored s
WHERE p_min_cos IS NULL
   OR (s.cos_sim IS NOT NULL
       AND s.cos_sim <> 'NaN'::DOUBLE PRECISION
       AND s.cos_sim >= p_min_cos)
ORDER BY s.rrf DESC LIMIT p_top_k;
$$;

COMMENT ON FUNCTION rag.hybrid_search(TEXT, vector, INT, INT, TEXT, VARCHAR,
                                      DATE, DATE, INT, DOUBLE PRECISION) IS
    'Dense (cosine) + BM25 -> RRF hibrit arama. score = RRF (rank tabanli, '
    'mutlak kalite bilgisi TASIMAZ); cos_sim = gercek cosine benzerligi. '
    'p_min_cos verilirse cos_sim esigin altindaki satirlar LIMIT UYGULANMADAN '
    'ONCE elenir; NULL ise filtre yoktur.';

COMMIT;
