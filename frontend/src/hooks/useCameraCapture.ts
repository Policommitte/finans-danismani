"use client";

import { useEffect, useRef, useState } from "react";

export type CameraOpenResult = "opened" | "unavailable";

/**
 * Kamera erisimi/foto cekme icin paylasilan mantik - once kimlik kartı
 * tarayicisi (`register/IdCardScanner.tsx`) icin yazildi, sonra sohbet
 * ekleri (`chat/AttachmentMenu.tsx`) icin de aynen kullanildi.
 *
 * Sadece HAM bir dataURL uretir (PNG); OCR'a ozel on-isleme (gri tonlama,
 * kontrast germe - `IdCardScanner.tsx::preprocessForOcr`) burada YAPILMAZ,
 * cagiran taraf gerekirse kendi canvas'inda uygular.
 */
export function useCameraCapture() {
  const [isStreaming, setIsStreaming] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  function stopStream() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setIsStreaming(false);
  }

  useEffect(() => stopStream, []);

  /**
   * Kamerayi acmayi dener. Izin reddedilirse veya API yoksa "unavailable"
   * doner - cagiran taraf bu durumda sessizce dosya seciciye (`<input
   * type="file" capture="environment">`) dusmelidir.
   */
  async function open(): Promise<CameraOpenResult> {
    if (!navigator.mediaDevices?.getUserMedia) {
      return "unavailable";
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsStreaming(true);
      return "opened";
    } catch {
      return "unavailable";
    }
  }

  /** Suanki video karesini PNG dataURL olarak yakalar; akis yoksa `null`. */
  function capture(): string | null {
    const video = videoRef.current;
    if (!video || !streamRef.current) {
      return null;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return null;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  }

  function close() {
    stopStream();
  }

  return { videoRef, isStreaming, open, capture, close };
}
