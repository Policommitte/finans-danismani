"use client";

import { useEffect, useState } from "react";
import { fetchPhotoUrl } from "../../services/photoCache";

type Props = {
  src: string;
  alt: string;
  /** Verilirse önce Pexels'te canlı bir fotoğraf aranır; bulunursa yerel
   * `src`'nin yerini alır, bulunamazsa/aranmıyorsa yerel `src` kullanılmaya
   * devam eder. Dosya (yerel ya da Pexels) hiç yüklenemezse sessizce boş
   * bırakılır - kırık görsel ikonu gösterilmez. */
  query?: string;
  className?: string;
};

/** `Banner` (CampaignsTab) ve ödül fotoğrafları (LeaderboardPanel) gibi farklı
 * boyut/yerleşimlerdeki tüm "gerçek fotoğraf" kullanımlarının paylaştığı
 * çekirdek - sarmalayıcı div'i BİLEREK içermez, boyut/kırpma çağıran yere ait. */
export function PhotoImage({ src, alt, query, className }: Props) {
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

  if (broken) {
    return null;
  }

  return (
    <img src={resolvedSrc} alt={alt} className={className} onError={() => setBroken(true)} />
  );
}
