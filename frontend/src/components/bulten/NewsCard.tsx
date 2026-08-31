"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useLanguage } from "../../contexts/LanguageContext";
import { fetchPhotoUrl } from "../../services/photoCache";
import { matchNewsLogo } from "./logos";
import { detectPhoto, topicThumbnail } from "./thumbnails";

export function NewsCard({
  icon,
  image,
  photoQuery,
  symbol,
  tag,
  time,
  title,
  summary,
  onOpen,
}: {
  icon?: ReactNode;
  image?: string;
  /**
   * Sunucudan hazir bir `image` gelmiyorsa (orn. portfoy varligi karti) VE
   * bilinen bir yerel foto eslesmesi yoksa, bu sorguyla Pexels'te canli bir
   * fotograf aranir. `image` verilmisse ya da yerel eslesme bulunmussa hic
   * Pexels'e gidilmez - gereksiz istek atilmaz.
   */
  photoQuery?: string;
  symbol?: string;
  tag?: "positive" | "negative" | "neutral";
  time?: string;
  title: string;
  summary: string;
  onOpen?: () => void;
}) {
  const { language } = useLanguage();
  const logoMatch = matchNewsLogo(symbol ?? title);
  const seed = `${symbol ?? ""} ${title}`;
  const localPhoto = image ?? detectPhoto(seed);
  const [resolvedImage, setResolvedImage] = useState(localPhoto ?? topicThumbnail(seed));

  useEffect(() => {
    setResolvedImage(localPhoto ?? topicThumbnail(seed));
    if (localPhoto || !photoQuery) {
      return;
    }
    let active = true;
    fetchPhotoUrl(photoQuery).then((url) => {
      if (active && url) {
        setResolvedImage(url);
      }
    });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localPhoto, photoQuery, seed]);

  return (
    <div className="app-news-card-slot h-[320px]">
      <article
        onClick={onOpen}
        onKeyDown={(event) => {
          if (!onOpen || (event.key !== "Enter" && event.key !== " ")) {
            return;
          }
          event.preventDefault();
          onOpen();
        }}
        role={onOpen ? "button" : undefined}
        tabIndex={onOpen ? 0 : undefined}
        aria-label={onOpen ? (language === "tr" ? `${title} haberini aç` : `Open ${title} article`) : undefined}
        className={`app-hover-card app-news-card flex flex-col overflow-hidden rounded-xl border shadow-sm ${
          onOpen ? "cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500" : ""
        }`}
      >
        <div
          className="block h-[140px] w-full shrink-0 overflow-hidden border-0 bg-transparent p-0 text-left"
        >
          <img
            src={resolvedImage}
            alt=""
            aria-hidden="true"
            className="app-hover-card-image h-full w-full object-cover"
          />
        </div>
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
                {tag === "positive"
                  ? language === "tr" ? "▲ Olumlu" : "▲ Positive"
                  : language === "tr" ? "▼ Olumsuz" : "▼ Negative"}
              </span>
            )}
          </div>
          <div>
            <h4 className="app-news-card-title text-sm font-semibold app-heading">{title}</h4>
            <p className="app-news-card-summary mt-1 text-sm app-muted">{summary}</p>
          </div>
        </div>
      </article>
    </div>
  );
}
