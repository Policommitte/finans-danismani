"use client";

import { useRef, useState } from "react";
import { useCameraCapture } from "../../hooks/useCameraCapture";
import { tcknChecksumValid } from "../../utils/tckn";

export type IdCardExtraction = {
  firstName?: string;
  lastName?: string;
  tckn?: string;
  birthDate?: string; // ISO YYYY-MM-DD
};

type Props = {
  onExtracted: (data: IdCardExtraction) => void;
};

type Phase = "closed" | "camera" | "captured" | "reading" | "done" | "error";

// OCR'in siklikla karistirdigi harf/rakam ciftleri - TCKN adaylarini bulurken
// bu harfleri rakama cevirip checksum'i tekrar denemek, gercek kartlarda cok
// sik gorulen "0 yerine O", "1 yerine I/l", "5 yerine S", "8 yerine B" gibi
// yanlis okumalari tolere eder. Sadece TCKN aramasinda kullanilir - isim
// alanlarinda ORIJINAL metin degistirilmeden kalir.
const DIGIT_CONFUSABLES: Record<string, string> = {
  O: "0",
  Q: "0",
  D: "0",
  I: "1",
  L: "1",
  S: "5",
  B: "8",
  Z: "2",
  G: "6",
  T: "7",
};

function toDigits(run: string): string {
  return run
    .split("")
    .map((ch) => DIGIT_CONFUSABLES[ch] ?? ch)
    .join("");
}

/**
 * Basilik/MRZ alanlarini tek seferde guvenilir kesip okuyan hazir bir
 * kutuphane yok - bu yuzden yaklasim: TUM goruntuyu OCR'la, sonra regex ile
 * alan cikar. TCKN adaylari checksum (tcknChecksumValid) ile ayirt edilir -
 * kimlik kartinda TCKN'e yakin baska sayilar da gorunebilir (seri no, vs.),
 * bu yuzden ilk gecerli checksum'i tutan aday secilir.
 *
 * Gercek kart fotograflarinda OCR nadiren temiz "11 ardisik rakam" uretir -
 * hologram/arka plan deseni yuzunden rakamlar harfe donusebilir ya da
 * komsu karakterlerle birlesebilir. Bu yuzden once "rakama benzeyen"
 * (rakam + DIGIT_CONFUSABLES harfleri) 10-16 uzunlugundaki bloklar bulunur,
 * harfler rakama cevrilir, sonra bu blok icindeki HER 11'lik pencere
 * checksum ile denenir.
 */
function findTckn(text: string): string | undefined {
  const blocks = text.match(/[0-9OQDILSBZGT]{10,16}/g) ?? [];
  for (const block of blocks) {
    const digits = toDigits(block);
    if (!/^\d+$/.test(digits)) continue;
    for (let start = 0; start + 11 <= digits.length; start++) {
      const candidate = digits.slice(start, start + 11);
      if (tcknChecksumValid(candidate)) {
        return candidate;
      }
    }
  }
  return undefined;
}

/**
 * Isim alanlari (ADI/SOYADI etiketi sonrasi satir) en zayif halka - OCR
 * yanlis okuyabilir, bu yuzden sonuc HER ZAMAN sadece "on doldurma" -
 * cagiran taraf (register formu) input'lari duzenlenebilir birakir, hicbir
 * alan salt-okunur yapilmaz ve bu bilesen NVI dogrulamasinin yerine gecmez.
 */
function extractFromText(raw: string): IdCardExtraction {
  const text = raw.toUpperCase().replace(/\r/g, "");
  const result: IdCardExtraction = {};

  const tckn = findTckn(text);
  if (tckn) {
    result.tckn = tckn;
  }

  // Dogum tarihi: DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY / DD MM YYYY.
  const dateMatch = text.match(/\b(\d{2})[.\-/ ](\d{2})[.\-/ ](\d{4})\b/);
  if (dateMatch) {
    const [, day, month, year] = dateMatch;
    const y = Number(year);
    const m = Number(month);
    const d = Number(day);
    if (y > 1900 && y < 2100 && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      result.birthDate = `${year}-${month}-${day}`;
    }
  }

  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // "SOYADI" / "SURNAME/SOYADI:" gibi tek dilli veya cift dilli etiket
    // varyasyonlarini yakalamak icin satirin BASINDA degil, ICINDE arar.
    if (!result.lastName && /SOYAD/.test(line)) {
      const inline = line.replace(/^.*SOYAD[IİI]?\s*[:-]?\s*/, "").trim();
      const candidate = inline || lines[i + 1];
      if (candidate && /^[A-ZÇĞİÖŞÜ\s]{2,}$/.test(candidate)) {
        result.lastName = candidate;
      }
    }
    if (!result.firstName && /\bADI\b/.test(line) && !/ADI\s*VE\s*SOYAD/.test(line) && !/SOYAD/.test(line)) {
      const inline = line.replace(/^.*\bADI\s*[:-]?\s*/, "").trim();
      const candidate = inline || lines[i + 1];
      if (candidate && /^[A-ZÇĞİÖŞÜ\s]{2,}$/.test(candidate)) {
        result.firstName = candidate;
      }
    }
  }

  return result;
}

/**
 * Gri tonlama + yuzdelik dilim bazli kontrast germe. Kimlik/ehliyet
 * fotograflarinda hologram, guvenlik deseni ve donuk ısık OCR'i ciddi
 * yaniltiyor - bu iki islem (agir binarizasyon YAPMADAN, sadece kontrasti
 * gercek metin/arka plan araligina germeden) tesseract'in dogru okuma
 * ihtimalini belirgin sekilde artiran, dusuk riskli standart bir on-isleme
 * adimidir.
 */
function preprocessForOcr(canvas: HTMLCanvasElement): string {
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas.toDataURL("image/png");
  const { width, height } = canvas;
  const imageData = ctx.getImageData(0, 0, width, height);
  const { data } = imageData;
  const n = width * height;

  const gray = new Uint8ClampedArray(n);
  for (let i = 0; i < n; i++) {
    gray[i] = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2];
  }

  const histogram = new Array(256).fill(0);
  for (const v of gray) histogram[v]++;
  const lowCut = n * 0.02;
  const highCut = n * 0.02;
  let acc = 0;
  let lo = 0;
  for (let t = 0; t < 256; t++) {
    acc += histogram[t];
    if (acc >= lowCut) {
      lo = t;
      break;
    }
  }
  acc = 0;
  let hi = 255;
  for (let t = 255; t >= 0; t--) {
    acc += histogram[t];
    if (acc >= highCut) {
      hi = t;
      break;
    }
  }
  const range = Math.max(hi - lo, 1);

  for (let i = 0; i < n; i++) {
    const stretched = Math.min(255, Math.max(0, ((gray[i] - lo) / range) * 255));
    data[i * 4] = stretched;
    data[i * 4 + 1] = stretched;
    data[i * 4 + 2] = stretched;
  }
  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL("image/png");
}

function loadImageToCanvas(dataUrl: string, canvas: HTMLCanvasElement): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("canvas context yok"));
        return;
      }
      ctx.drawImage(img, 0, 0);
      resolve();
    };
    img.onerror = () => reject(new Error("görüntü yüklenemedi"));
    img.src = dataUrl;
  });
}

export function IdCardScanner({ onExtracted }: Props) {
  const [phase, setPhase] = useState<Phase>("closed");
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [foundSummary, setFoundSummary] = useState<string[]>([]);
  const [rawText, setRawText] = useState("");
  const [showRawText, setShowRawText] = useState(false);
  const camera = useCameraCapture();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function openCamera() {
    setErrorMessage("");
    setFoundSummary([]);
    setRawText("");
    setPhase("camera");
    setStatusMessage("Kamera açılıyor…");
    const result = await camera.open();
    if (result === "unavailable") {
      // Izin reddedildi/kamera yok/API desteklenmiyor - dosya seciciye sessizce dus.
      setPhase("closed");
      fileInputRef.current?.click();
      return;
    }
    setStatusMessage("Kimlik kartını kadraja alıp fotoğraf çekin - iyi ışıkta, parlama olmadan");
  }

  async function capturePhoto() {
    const dataUrl = camera.capture();
    const canvas = canvasRef.current;
    if (!dataUrl || !canvas) return;
    camera.close();
    await loadImageToCanvas(dataUrl, canvas);
    setPhase("captured");
    const processedDataUrl = preprocessForOcr(canvas);
    await runOcr(processedDataUrl);
  }

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    await loadImageToCanvas(dataUrl, canvas);
    setPhase("captured");
    const processedDataUrl = preprocessForOcr(canvas);
    await runOcr(processedDataUrl);
  }

  async function runOcr(imageDataUrl: string) {
    setPhase("reading");
    setStatusMessage("Okunuyor…");
    setErrorMessage("");
    setRawText("");
    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("tur");
      // PSM 11 (sparse text): fotograf/hologram/logo gibi metin-olmayan
      // buyuk alanlarla cevrili, birbirinden kopuk kisa metin bloklari
      // (etiket: deger ciftleri) icin - bir kimlik/ehliyet kartinin tipik
      // duzeni - varsayilan "tek paragraf" moduna gore daha uygun.
      await worker.setParameters({ tessedit_pageseg_mode: "11" as never });
      const { data } = await worker.recognize(imageDataUrl);
      await worker.terminate();

      setRawText(data.text);
      const extracted = extractFromText(data.text);
      const summary: string[] = [];
      if (extracted.firstName) summary.push(`Ad: ${extracted.firstName}`);
      if (extracted.lastName) summary.push(`Soyad: ${extracted.lastName}`);
      if (extracted.tckn) summary.push(`TC Kimlik No: ${extracted.tckn}`);
      if (extracted.birthDate) summary.push(`Doğum tarihi: ${extracted.birthDate}`);

      if (summary.length === 0) {
        setPhase("error");
        setErrorMessage("Kartta bilgi okunamadı, lütfen daha net bir fotoğrafla tekrar deneyin.");
        return;
      }

      onExtracted(extracted);
      setFoundSummary(summary);
      setPhase("done");
      setStatusMessage("Bulunan bilgiler forma dolduruldu, lütfen kontrol edin");
    } catch {
      setPhase("error");
      setErrorMessage("Okuma sırasında bir sorun oluştu, lütfen tekrar deneyin.");
    }
  }

  function reset() {
    camera.close();
    setPhase("closed");
    setErrorMessage("");
    setFoundSummary([]);
    setRawText("");
    setShowRawText(false);
  }

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileSelected}
      />
      <canvas ref={canvasRef} className="hidden" />

      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--color-text)]">
            Kimlik kartınızı tarayarak otomatik doldurun
          </p>
          <p className="mt-0.5 text-xs text-[var(--color-muted)]">
            İsteğe bağlı - kartı okutunca alanlar doldurulur, siz kontrol edip düzenlersiniz.
          </p>
        </div>
        {phase === "closed" && (
          <button
            type="button"
            onClick={openCamera}
            className="shrink-0 rounded-lg border border-[var(--color-primary)] px-3.5 py-2 text-xs font-semibold text-[var(--color-primary)] transition hover:bg-[var(--color-primary-soft)]"
          >
            Kartı tara
          </button>
        )}
        {(phase === "done" || phase === "error") && (
          <button
            type="button"
            onClick={reset}
            className="shrink-0 rounded-lg border border-[var(--color-border)] px-3.5 py-2 text-xs font-semibold text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
          >
            Tekrar tara
          </button>
        )}
      </div>

      {phase === "camera" && (
        <div className="mt-3 space-y-2">
          <video ref={camera.videoRef} className="w-full rounded-lg bg-black" muted playsInline />
          <p className="text-xs text-[var(--color-muted)]">{statusMessage}</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={capturePhoto}
              className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-xs font-semibold text-white transition hover:opacity-90"
            >
              Fotoğrafı çek
            </button>
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-[var(--color-border)] px-4 py-2 text-xs font-semibold text-[var(--color-text)]"
            >
              Vazgeç
            </button>
          </div>
        </div>
      )}

      {(phase === "captured" || phase === "reading") && (
        <p className="mt-3 text-xs font-medium text-[var(--color-primary)]">{statusMessage}</p>
      )}

      {phase === "done" && (
        <div className="mt-3 rounded-lg border border-[var(--color-success)] bg-[var(--color-primary-soft)] p-3 text-xs text-[var(--color-success)]">
          <p className="font-semibold">{statusMessage}</p>
          <ul className="mt-1 list-inside list-disc">
            {foundSummary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {phase === "error" && (
        <div className="mt-3 space-y-2">
          <p className="rounded-lg border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] p-3 text-xs text-[var(--color-danger-text)]">
            {errorMessage}
          </p>
          {rawText.trim() && (
            <div>
              <button
                type="button"
                onClick={() => setShowRawText((v) => !v)}
                className="text-xs font-medium text-[var(--color-primary)] underline"
              >
                {showRawText ? "Okunan ham metni gizle" : "Okunan ham metni göster"}
              </button>
              {showRawText && (
                <pre className="mt-1.5 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg border border-[var(--color-border)] bg-[var(--color-input-bg)] p-2 text-[11px] text-[var(--color-muted)]">
                  {rawText}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
