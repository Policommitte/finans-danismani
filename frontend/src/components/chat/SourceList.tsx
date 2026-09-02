import type { Source } from "../../models/chat";

/**
 * `href`'e yazilmaya UYGUN mu?
 *
 * `kaynak_url` ingestion hattindan gelir - bizim yazdigimiz bir deger degil.
 * Ham haliyle `href`'e konursa `javascript:` semali tek bir satir tiklanabilir
 * XSS'e donusur. Bu yuzden adres COZULUR ve yalnizca http/https gecer;
 * cozulemeyen (goreli/bozuk) adres link URETMEZ, kart duz metne duser.
 */
export function guvenliUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }

  try {
    const cozulen = new URL(url);
    return ["http:", "https:"].includes(cozulen.protocol) ? cozulen.href : null;
  } catch {
    return null;
  }
}

/** "https://www.aa.com.tr/tr/ekonomi/..." -> "aa.com.tr" */
function alanAdi(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/**
 * "2026-08-10" -> "10.08.2026"
 *
 * `toLocaleDateString` KULLANILMAZ: sunucu ile tarayicinin yerel ayari
 * farkliysa ayni tarih iki farkli metne cevrilir ve React hydration uyumsuzlugu
 * verir. Sabit formatli girdiyi elle cevirmek deterministiktir.
 */
function tarihiBicimle(tarih: string | null): string {
  if (!tarih) {
    return "";
  }

  const parcalar = tarih.split("-");
  if (parcalar.length !== 3) {
    return tarih;
  }

  const [yil, ay, gun] = parcalar;
  return `${gun}.${ay}.${yil}`;
}

function KaynakIcerigi({ source, adres }: { source: Source; adres: string | null }) {
  const altSatir = [source.sirket, tarihiBicimle(source.tarih), adres ? alanAdi(adres) : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <>
      {/* Alti cizgi HOVER'da beliriyor: `app-heading` gibi `@layer components`
          sinifları Tailwind utility'si DEGILDIR, `hover:app-heading` hicbir CSS
          uretmez (projede `.app-primary:hover` bu yuzden elle yazilmis). Renk
          degistirmek yerine `market/page.tsx`'teki dis-link desenine uyuluyor. */}
      <span className="block app-heading group-hover:underline decoration-current/40 underline-offset-2">
        {source.baslik}
      </span>
      {altSatir && (
        <span className="mt-0.5 flex items-center gap-1">
          <span>{altSatir}</span>
          {adres && (
            <svg
              viewBox="0 0 24 24"
              className="h-3 w-3 shrink-0 opacity-60 transition-opacity group-hover:opacity-100"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <path d="M15 3h6v6" />
              <path d="M10 14 21 3" />
            </svg>
          )}
        </span>
      )}
    </>
  );
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1">
      {sources.slice(0, 3).map((source) => {
        const adres = guvenliUrl(source.kaynak_url);
        const ortakSinif = "block rounded-md app-surface px-2 py-1 text-xs app-muted";

        // Adresi olmayan kaynak (eski kayitlar, canli veri yolu) TIKLANAMAZ
        // olmali: bos bir `<a>` kullaniciya okuyabilecegi bir yer varmis gibi
        // gorunur, tiklayinca hicbir sey olmaz.
        if (!adres) {
          return (
            <div key={source.doc_id} className={ortakSinif}>
              <KaynakIcerigi source={source} adres={null} />
            </div>
          );
        }

        return (
          <a
            key={source.doc_id}
            href={adres}
            target="_blank"
            rel="noreferrer"
            // Uzerine gelindiginde tam adres tarayicinin kendi ipucunda ve
            // durum cubugunda gorunur; kullanici nereye gidecegini tiklamadan
            // once bilir.
            title={adres}
            className={`${ortakSinif} group focus-visible:underline`}
          >
            <KaynakIcerigi source={source} adres={adres} />
          </a>
        );
      })}
    </div>
  );
}
