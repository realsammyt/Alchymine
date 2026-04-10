"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

export type ChatMode = "bubble" | "panel" | "split";

interface ChatOverlayState {
  mode: ChatMode;
  searchOpen: boolean;
  systemKey: string | null;
  openChat: () => void;
  closeChat: () => void;
  expandChat: () => void;
  collapseChat: () => void;
  toggleSearch: () => void;
  setSystemKey: (key: string | null) => void;
}

const ChatContext = createContext<ChatOverlayState | null>(null);

const STORAGE_KEY = "alchymine:chat-mode";

export function ChatProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ChatMode>("bubble");
  const [searchOpen, setSearchOpen] = useState(false);
  const [systemKey, setSystemKey] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "bubble") {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  }, [mode]);

  const openChat = useCallback(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    setMode(saved === "split" ? "split" : "panel");
  }, []);

  const closeChat = useCallback(() => {
    setMode("bubble");
    setSearchOpen(false);
  }, []);

  const expandChat = useCallback(() => setMode("split"), []);
  const collapseChat = useCallback(() => setMode("panel"), []);
  const toggleSearch = useCallback(() => setSearchOpen((o) => !o), []);

  const value = useMemo(
    () => ({
      mode,
      searchOpen,
      systemKey,
      openChat,
      closeChat,
      expandChat,
      collapseChat,
      toggleSearch,
      setSystemKey,
    }),
    [
      mode,
      searchOpen,
      systemKey,
      openChat,
      closeChat,
      expandChat,
      collapseChat,
      toggleSearch,
    ],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChatOverlay(): ChatOverlayState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatOverlay must be used within ChatProvider");
  return ctx;
}
