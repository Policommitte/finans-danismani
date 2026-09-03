"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useChatStream } from "../hooks/useChatStream";

export type ChatContextValue = ReturnType<typeof useChatStream>;

const ChatContext = createContext<ChatContextValue | null>(null);

/**
 * One chat state for the whole app. Before this, the widget, the landing page
 * and the asset modal each called `useChatStream()` on their own and opened
 * separate conversations - a question asked from the market modal never
 * showed up in the widget.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChatStream();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const value = useContext(ChatContext);
  if (!value) {
    throw new Error("useChat must be used inside ChatProvider");
  }
  return value;
}
