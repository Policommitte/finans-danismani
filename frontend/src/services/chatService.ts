import type { ChatEvent, ChatRequest } from "../models/chat";
import { getAccessToken, getApiUrl } from "./apiClient";

export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const token = getAccessToken();
  const response = await fetch(getApiUrl("/api/chat/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    throw new Error("Sohbet akisi baslatilamadi.");
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
      const dataLine = chunk
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (!dataLine) {
        continue;
      }
      onEvent(JSON.parse(dataLine.slice(6)) as ChatEvent);
    }
  }
}
