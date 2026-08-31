"use client";

import { useEffect, useState } from "react";
import Card from "../ui/Card";
import type { Powerups } from "../../hooks/useQuiz";
import {
  CAMPAIGNS,
  DONATIONS,
  POWERUP_SHOP,
  type DonationItem,
  type PowerupKind,
} from "../../models/oyun";
import { useLanguage } from "../../contexts/LanguageContext";
import { fetchPhotoUrl } from "../../services/photoCache";

type SubTab = "jokerler" | "bagislar" | "kampanyalar";

const SUB_TABS: { id: SubTab; label: { tr: string; en: string } }[] = [
  { id: "jokerler", label: { tr: "Jokerler", en: "Power-ups" } },
  { id: "bagislar", label: { tr: "Bağışlar", en: "Donations" } },
  { id: "kampanyalar", label: { tr: "Kampanyalar", en: "Campaigns" } },
];

type Props = {
  pointsBalance: number;
  powerups: Powerups;
  ownedBadges: string[];
  onBuyPowerup: (kind: PowerupKind, price: number) => void;
  onBuyDonation: (item: DonationItem) => void;
};

/**
 * Görsel banner — dosya henüz yoksa sessizce boş bırakır, kırık ikon göstermez.
 * `query` verilirse önce Pexels'te canlı bir fotoğraf aranır; bulunursa yerel
 * `src`'nin yerini alır, bulunamazsa/aranmıyorsa yerel `src` kullanılmaya devam eder.
 */
function Banner({ src, alt, query }: { src: string; alt: string; query?: string }) {
  const [resolvedSrc, setResolvedSrc] = useState(src);
  const [broken, setBroken] = useState(false);

  useEffect(() => {
    setResolvedSrc(src);
    setBroken(false);
    if (!query) {
      return;
    }
    let active = true;
    fetchPhotoUrl(query).then((url) => {
      if (active && url) {
        setResolvedSrc(url);
        setBroken(false);
      }
    });
    return () => {
      active = false;
    };
  }, [src, query]);

  return (
    <div
      className="relative -mx-5 -mt-5 mb-4 aspect-[2/1] overflow-hidden rounded-t-xl"
      style={{ background: "var(--color-surface-muted)" }}
    >
      {!broken && (
        <img
          src={resolvedSrc}
          alt={alt}
          className="absolute inset-0 h-full w-full object-cover"
          onError={() => setBroken(true)}
        />
      )}
    </div>
  );
}

export function CampaignsTab({
  pointsBalance,
  powerups,
  ownedBadges,
  onBuyPowerup,
  onBuyDonation,
}: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const [subTab, setSubTab] = useState<SubTab>("jokerler");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2" role="tablist">
          {SUB_TABS.map((t) => {
            const active = subTab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => setSubTab(t.id)}
                className="rounded-lg px-3 py-1.5 text-xs font-semibold transition"
                style={
                  active
                    ? { background: "var(--color-primary)", color: "var(--color-on-primary)" }
                    : { background: "var(--color-surface-muted)", color: "var(--color-muted)" }
                }
              >
                {t.label[language]}
              </button>
            );
          })}
        </div>

        <div
          className="rounded-lg px-3 py-1.5 text-xs font-semibold"
          style={{ background: "var(--color-surface-muted)", color: "var(--color-heading)" }}
        >
          {language === "tr" ? "Bakiye" : "Balance"}:{" "}
          <b className="tabular-nums">{pointsBalance.toLocaleString(locale)}</b>{" "}
          {language === "tr" ? "puan" : "points"}
        </div>
      </div>

      {subTab === "jokerler" && (
        <div className="grid gap-3 sm:grid-cols-2">
          {POWERUP_SHOP.map((item) => {
            const owned = powerups[item.kind];
            const affordable = pointsBalance >= item.price;
            return (
              <Card key={item.kind}>
                <Banner src={item.image} alt={item.label[language]} query={item.imageQuery} />

                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="app-heading text-sm font-semibold">{item.label[language]}</p>
                    <p className="app-muted mt-1 text-xs leading-relaxed">{item.description[language]}</p>
                  </div>
                  <span
                    className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold"
                    style={{
                      background: "var(--color-primary-soft)",
                      color: "var(--color-primary-soft-text)",
                    }}
                  >
                    {owned} {language === "tr" ? "adet" : "owned"}
                  </span>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="app-heading text-sm font-bold tabular-nums">
                    {item.price.toLocaleString(locale)} {language === "tr" ? "puan" : "points"}
                  </span>
                  <button
                    onClick={() => onBuyPowerup(item.kind, item.price)}
                    disabled={!affordable}
                    className="rounded-lg px-4 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40"
                    style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
                  >
                    {language === "tr" ? "Satın al" : "Buy"}
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {subTab === "bagislar" && (
        <div className="grid gap-3 sm:grid-cols-2">
          {DONATIONS.map((item) => {
            const owned = ownedBadges.includes(item.badge.tr);
            const affordable = pointsBalance >= item.cost;
            return (
              <Card key={item.id}>
                <Banner src={item.image} alt={item.title[language]} query={item.imageQuery} />

                <div className="flex items-start gap-3">
                  <span
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-xl"
                    style={{ background: "var(--color-surface-muted)" }}
                  >
                    {item.icon}
                  </span>
                  <div>
                    <p className="app-heading text-sm font-semibold">{item.title[language]}</p>
                    <p className="app-muted mt-1 text-xs leading-relaxed">{item.body[language]}</p>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="app-heading text-sm font-bold tabular-nums">
                    {item.cost.toLocaleString(locale)} {language === "tr" ? "puan" : "points"}
                  </span>
                  {owned ? (
                    <span
                      className="rounded-lg px-4 py-2 text-xs font-semibold"
                      style={{
                        background: "var(--color-primary-soft)",
                        color: "var(--color-success)",
                      }}
                    >
                      {language === "tr" ? "Rozet kazanıldı" : "Badge earned"}
                    </span>
                  ) : (
                    <button
                      onClick={() => onBuyDonation(item)}
                      disabled={!affordable}
                      className="rounded-lg px-4 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40"
                      style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
                    >
                      {language === "tr" ? "Bağışla" : "Donate"}
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {subTab === "kampanyalar" && (
        <div className="grid gap-3 sm:grid-cols-2">
          {CAMPAIGNS.map((c) => (
            <Card key={c.id}>
              <Banner src={c.image} alt={c.title[language]} query={c.imageQuery} />

              <p className="app-muted text-[11px]">{c.tags[language]}</p>
              <p className="app-heading mt-1 text-sm font-semibold leading-snug">{c.title[language]}</p>
              <p className="app-muted mt-2 text-xs leading-relaxed">{c.body[language]}</p>
              <div className="app-muted mt-3 flex items-center justify-between text-[11px]">
                <span>
                  {c.joined.toLocaleString(locale)} {language === "tr" ? "katılımcı" : "participants"}
                </span>
                <span>{c.left[language]}</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
