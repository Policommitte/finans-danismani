"use client";

import { matchNewsLogo, matchSourceLogo } from "./logos";

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
};

export function NewsDetailModal({ article, onClose }: { article: NewsDetailArticle; onClose: () => void }) {
  const logoMatch = matchNewsLogo(article.symbol ?? article.title);
  const sourceLogo = matchSourceLogo(article.source);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4 py-6" onClick={onClose}>
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-xl border app-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b app-border px-5 py-4">
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

        <div className="border-t app-border px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border app-border app-surface px-4 py-2.5 text-sm font-semibold app-muted transition hover:opacity-80"
          >
            ← Bültene dön
          </button>
        </div>
      </div>
    </div>
  );
}
