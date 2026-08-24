import type { ReactNode } from "react";
import { matchNewsLogo } from "./logos";
import { newsThumbnail } from "./thumbnails";

export function NewsCard({
  icon,
  image,
  symbol,
  tag,
  time,
  title,
  summary,
  onOpen,
}: {
  icon?: ReactNode;
  image?: string;
  symbol?: string;
  tag?: "positive" | "negative" | "neutral";
  time?: string;
  title: string;
  summary: string;
  onOpen?: () => void;
}) {
  const logoMatch = matchNewsLogo(symbol ?? title);

  return (
    <div className="app-news-card-slot h-[320px]">
      <article className="app-hover-card app-news-card flex flex-col overflow-hidden rounded-xl border shadow-sm">
        <button
          type="button"
          onClick={onOpen}
          aria-label={`${title} haberini aç`}
          disabled={!onOpen}
          className="block h-[140px] w-full shrink-0 overflow-hidden border-0 bg-transparent p-0 text-left disabled:cursor-default"
        >
          <img
            src={image ?? newsThumbnail(`${symbol ?? ""} ${title}`)}
            alt=""
            aria-hidden="true"
            className="app-hover-card-image h-full w-full object-cover"
          />
        </button>
        <div className="flex flex-1 flex-col gap-3 p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {(logoMatch || icon) && (
                <span className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-lg app-primary-soft">
                  {logoMatch ? (
                    <span
                      className={`grid h-7 w-7 place-items-center overflow-hidden rounded-md ${logoMatch.fill ? "" : "p-0.5"}`}
                      style={{ backgroundColor: logoMatch.background }}
                    >
                      <logoMatch.Logo />
                    </span>
                  ) : (
                    icon
                  )}
                </span>
              )}
              {symbol && <span className="rounded-md app-card-muted px-2 py-0.5 text-xs font-semibold app-heading">{symbol}</span>}
            </div>
            {time && <span className="text-xs font-semibold app-muted">{time}</span>}
            {tag && tag !== "neutral" && (
              <span className={`text-xs font-semibold ${tag === "positive" ? "app-success" : "app-danger"}`}>
                {tag === "positive" ? "▲ Olumlu" : "▼ Olumsuz"}
              </span>
            )}
          </div>
          <div>
            <button
              type="button"
              onClick={onOpen}
              disabled={!onOpen}
              className="block border-0 bg-transparent p-0 text-left disabled:cursor-default"
            >
              <h4 className="app-news-card-title text-sm font-semibold app-heading hover:underline">{title}</h4>
            </button>
            <p className="app-news-card-summary mt-1 text-sm app-muted">{summary}</p>
          </div>
        </div>
      </article>
    </div>
  );
}
