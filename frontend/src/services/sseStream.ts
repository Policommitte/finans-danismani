import { getAccessToken, getApiUrl } from "./apiClient";

/**
 * Ortak SSE (Server-Sent Events) okuyucu.
 *
 * `chatService.ts::streamChat` ve `marketService.ts::streamQuickAnalysis`
 * AYNI cerceve ayrimini (bosluklu iki satirla ayrilmis "data: {json}"
 * bloklari) paylasir - kod burada TEK yerde tutulur, ikisi de bunu cagirir.
 *
 * Native `EventSource` KULLANILMAZ: yalnizca GET destekler ve
 * `Authorization` header'i gonderemez (bkz. `chatService.ts` modul
 * docstring'i, mimari v4 bolum 4.6) - bu yuzden `fetch` + `ReadableStream`
 * ile elle ayristirilir.
 */
export async function streamSse<T>(
  path: string,
  onEvent: (event: T) => void,
  options?: { method?: "GET" | "POST"; body?: unknown; signal?: AbortSignal },
): Promise<void> {
  const token = getAccessToken();
  const response = await fetch(getApiUrl(path), {
    method: options?.method ?? "GET",
    headers: {
      ...(options?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
    signal: options?.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error("Akış başlatılamadı.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const dataLine = chunk.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) {
        continue;
      }
      onEvent(JSON.parse(dataLine.slice(6)) as T);
    }
  }
}
