"use client";

import { createPortal } from "react-dom";
import { matchNewsLogo, matchSourceLogo } from "./logos";
import { guvenliUrl } from "../chat/SourceList";
import { useLanguage } from "../../contexts/LanguageContext";

function GenericNewsIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h13l3 3v13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" />
      <path d="M8 9h8" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </svg>
  );
}

export type NewsDetailArticle = {
  title: string;
  source: string;
  time: string;
  body: string[];
  symbol?: string;
  /**
   * Haberin yayindaki adresi (`rag.documents.kaynak_url`). Portfoyden
   * TUREYEN "haberler" (bkz. `bulten/page.tsx::buildHoldingArticle`) icin
   * bu alan hic gonderilmez - onlarin disarida gercek bir karsiligi yok.
   */
  sourceUrl?: string | null;
};

export function NewsDetailModal({ article, onClose }: { article: NewsDetailArticle; onClose: () => void }) {
  const { language } = useLanguage();
  const logoMatch = matchNewsLogo(article.symbol ?? article.title);
  const sourceLogo = matchSourceLogo(article.source);
  const kaynakAdresi = guvenliUrl(article.sourceUrl);

  return createPortal(
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-[1px]"
      onClick={onClose}
    >
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-xl border app-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b app-border app-card px-5 py-4 shadow-sm">
          <div className="flex items-center gap-4">
            <span
              className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-xl"
              style={{ backgroundColor: logoMatch?.background ?? "var(--color-primary-soft)" }}
            >
              {logoMatch ? (
                <div className={logoMatch.fill ? "h-full w-full" : "h-full w-full max-w-[46px] p-2"}>
                  <logoMatch.Logo />
                </div>
              ) : (
                <span className="app-primary-text">
                  <GenericNewsIcon />
                </span>
              )}
            </span>
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold app-muted">
                {sourceLogo && (
                  <img src={sourceLogo} alt="" aria-hidden="true" className="h-4 w-4 shrink-0 rounded-sm object-contain" />
                )}
                <span>
                  {article.source} · {article.time}
                </span>
              </div>
              <h2 className="mt-1 text-lg font-bold app-heading">{article.title}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded px-2 py-1 text-xl leading-none app-muted hover:opacity-80"
          >
            ×
          </button>
        </div>

        <div className="space-y-4 px-5 py-5">
          {article.body.map((paragraph, index) => (
            <p key={index} className="text-sm leading-relaxed text-[var(--color-text)]">
              {paragraph}
            </p>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t app-border px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border app-border app-surface px-4 py-2.5 text-sm font-semibold app-muted transition hover:opacity-80"
          >
            {language === "tr" ? "← Bültene dön" : "← Back to bulletin"}
          </button>
          {kaynakAdresi && (
            <a
              href={kaynakAdresi}
              target="_blank"
              rel="noreferrer"
              title={kaynakAdresi}
              className="inline-flex items-center gap-1.5 text-sm font-semibold app-heading underline decoration-current/40 underline-offset-2 hover:opacity-80"
            >
              {language === "tr" ? "Kaynağa git" : "View source"}
              <svg
                viewBox="0 0 24 24"
                className="h-3.5 w-3.5 shrink-0"
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
            </a>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
