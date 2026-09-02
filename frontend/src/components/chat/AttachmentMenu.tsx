"use client";

import { useEffect, useRef, useState } from "react";
import { useCameraCapture } from "../../hooks/useCameraCapture";
import type { ChatAttachmentKind } from "../../models/chat";

export type PendingAttachment = {
  kind: ChatAttachmentKind;
  filename: string;
  mimeType: string;
  /** Tam data URL (`data:<mime>;base64,<veri>`) - hem onizleme hem de
   * gonderim oncesi base64 cikarimi icin kullanilir. */
  dataUrl: string;
};

const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;
const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp,image/gif";
const FILE_ACCEPT = ".pdf,.txt,.csv,.md,.json,application/pdf,text/plain,text/csv,text/markdown,application/json";

function PlusIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}

function ImageIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function dataUrlByteLength(dataUrl: string): number {
  const base64 = dataUrl.split(",")[1] ?? "";
  return Math.ceil((base64.length * 3) / 4);
}

export function AttachmentMenu({
  onAttach,
  onError,
  disabled,
}: {
  onAttach: (attachment: PendingAttachment) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const camera = useCameraCapture();
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  function checkSize(dataUrl: string): boolean {
    if (dataUrlByteLength(dataUrl) > MAX_ATTACHMENT_BYTES) {
      onError("Dosya 10MB sınırını aşıyor, lütfen daha küçük bir dosya deneyin.");
      return false;
    }
    return true;
  }

  async function startCamera() {
    setMenuOpen(false);
    const result = await camera.open();
    if (result === "unavailable") {
      // Izin reddedildi/kamera yok - dosya seciciye sessizce dus (goersel kabul eder).
      imageInputRef.current?.click();
      return;
    }
    setCameraOpen(true);
  }

  function capturePhoto() {
    const dataUrl = camera.capture();
    camera.close();
    setCameraOpen(false);
    if (!dataUrl || !checkSize(dataUrl)) return;
    onAttach({ kind: "image", filename: "kamera-fotografi.png", mimeType: "image/png", dataUrl });
  }

  function cancelCamera() {
    camera.close();
    setCameraOpen(false);
  }

  async function handleImageSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setMenuOpen(false);
    if (!file) return;
    const dataUrl = await readFileAsDataUrl(file);
    if (!checkSize(dataUrl)) return;
    onAttach({ kind: "image", filename: file.name, mimeType: file.type || "image/jpeg", dataUrl });
  }

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setMenuOpen(false);
    if (!file) return;
    const dataUrl = await readFileAsDataUrl(file);
    if (!checkSize(dataUrl)) return;
    onAttach({
      kind: "file",
      filename: file.name,
      mimeType: file.type || "application/octet-stream",
      dataUrl,
    });
  }

  return (
    <div className="relative" ref={menuRef}>
      <input ref={imageInputRef} type="file" accept={IMAGE_ACCEPT} className="hidden" onChange={handleImageSelected} />
      <input ref={fileInputRef} type="file" accept={FILE_ACCEPT} className="hidden" onChange={handleFileSelected} />

      <button
        type="button"
        aria-label="Ek ekle"
        disabled={disabled}
        onClick={() => setMenuOpen((v) => !v)}
        className="grid h-9 w-9 shrink-0 place-items-center rounded-md border app-border text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)] disabled:cursor-not-allowed disabled:opacity-40"
      >
        <PlusIcon />
      </button>

      {menuOpen && (
        <div
          className="absolute bottom-full left-0 z-10 mb-2 w-52 overflow-hidden rounded-lg border app-border app-card shadow-lg"
          role="menu"
        >
          <button
            type="button"
            role="menuitem"
            onClick={startCamera}
            className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-sm text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
          >
            <CameraIcon />
            Kamerayı Aç
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setMenuOpen(false);
              imageInputRef.current?.click();
            }}
            className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-sm text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
          >
            <ImageIcon />
            Görsel Yükle
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setMenuOpen(false);
              fileInputRef.current?.click();
            }}
            className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-sm text-[var(--color-text)] transition hover:bg-[var(--color-primary-soft)]"
          >
            <FileIcon />
            Dosya Yükle
          </button>
        </div>
      )}

      {cameraOpen && (
        <div className="absolute bottom-full left-0 z-20 mb-2 w-72 rounded-lg border app-border app-card p-3 shadow-xl">
          <video ref={camera.videoRef} className="w-full rounded-md bg-black" muted playsInline />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={capturePhoto}
              className="flex-1 rounded-md bg-[var(--color-primary)] px-3 py-2 text-xs font-semibold text-white transition hover:opacity-90"
            >
              Fotoğrafı çek
            </button>
            <button
              type="button"
              onClick={cancelCamera}
              className="rounded-md border app-border px-3 py-2 text-xs font-semibold text-[var(--color-text)]"
            >
              Vazgeç
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
