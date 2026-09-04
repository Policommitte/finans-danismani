import type { ChatEvent, ChatRequest } from "../models/chat";
import { getAccessToken, getApiUrl } from "./apiClient";
import { streamSse } from "./sseStream";

/**
 * Belge analiz raporunu indirir ve tarayicida "farkli kaydet" akisini
 * tetikler.
 *
 * DUZ `<a href>` KULLANILAMAZ: indirme ucu (`GET /api/chat/reports/:id`)
 * `Authorization` header'i ister (mimari v4 bolum 4.6 - sohbet uclarinin
 * hepsi boyle), tarayicinin normal navigasyonu header ekleyemez. Bu yuzden
 * `fetch` ile cekilip blob URL'e cevrilir ve GECICI bir `<a>` elemaniyla
 * tiklanir - indirme baslar baslamaz element ve blob URL TEMIZLENIR.
 */
export async function downloadChatReport(messageId: number, filename: string): Promise<void> {
  const token = getAccessToken();
  let response: Response;
  try {
    response = await fetch(getApiUrl(`/api/chat/reports/${messageId}`), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    // `fetch` burada HTTP hatasi degil, AG SEVIYESINDE bir istisna firlatir
    // (sunucuya HIC ULASILAMADI - kapali, yeniden basliyor, CORS reddetti).
    // Tarayicinin ham "Failed to fetch" mesaji kullaniciya hicbir sey
    // anlatmaz; ayirt edip ACIK bir mesaj veriyoruz.
    throw new Error(
      "Sunucuya ulaşılamadı. Backend çalışmıyor ya da yeniden başlatılmış olabilir.",
    );
  }

  if (!response.ok) {
    throw new Error("Rapor indirilemedi, süresi dolmuş olabilir.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Streams one chat turn. Pass an `AbortSignal` to let the user stop a long
 * answer (or to cancel on unmount): aborting rejects with an `AbortError`,
 * which the caller treats as a normal end of stream, not a failure.
 */
export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return streamSse<ChatEvent>("/api/chat/stream", onEvent, { method: "POST", body: payload, signal });
}
