"use client";

/**
 * ChatPanel — composed chat experience: header, message list, input,
 * and dismissable error banner.
 *
 * Owns its own ``useChat`` instance so the parent page only needs to
 * pass an optional ``systemKey``.  Sprint 3 will add starter prompts
 * and history loading; Sprint 5 will add per-page context injection.
 */

import { useState } from "react";

import { useChat } from "@/hooks/useChat";

import ChatInput from "./ChatInput";
import ChatMessageList from "./ChatMessageList";

interface Props {
  /** Optional pillar scope: intelligence | healing | wealth | creative | perspective */
  systemKey?: string | null;
}

const SYSTEM_LABELS: Record<string, string> = {
  intelligence: "Personal Intelligence",
  healing: "Ethical Healing",
  wealth: "Generational Wealth",
  creative: "Creative Development",
  perspective: "Perspective Enhancement",
};

export default function ChatPanel({ systemKey = null }: Props) {
  const { messages, isStreaming, error, sendMessage, resetConversation } =
    useChat();
  const [errorDismissed, setErrorDismissed] = useState(false);

  const visibleError = errorDismissed ? null : error;

  const handleSend = (text: string) => {
    // Reset the dismissed flag so the next error is shown.
    setErrorDismissed(false);
    void sendMessage(text, systemKey);
  };

  const systemLabel = systemKey ? SYSTEM_LABELS[systemKey] ?? systemKey : null;

  return (
    <section
      aria-label="Growth Assistant chat"
      className="flex h-full w-full flex-col overflow-hidden rounded-2xl border border-white/5 bg-surface/80 shadow-xl"
    >
      {/* Header banner */}
      <header className="flex items-center justify-between border-b border-white/5 px-4 py-3">
        <div>
          <h2 className="font-display text-base font-medium text-text">
            Growth Assistant
          </h2>
          <p className="text-xs font-body text-text/50">
            {systemLabel
              ? `${systemLabel} specialist`
              : "Your integrated transformation coach"}
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={resetConversation}
            className="rounded-lg px-2 py-1 text-xs font-body text-text/40 transition-colors hover:bg-white/5 hover:text-text/80"
          >
            New conversation
          </button>
        )}
      </header>

      {/* Error banner */}
      {visibleError && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 border-b border-red-500/20 bg-red-500/10 px-4 py-2.5 text-sm text-red-200"
        >
          <span className="font-body">{visibleError}</span>
          <button
            type="button"
            onClick={() => setErrorDismissed(true)}
            aria-label="Dismiss error"
            className="shrink-0 rounded-md p-0.5 text-red-200/70 transition-colors hover:bg-red-500/10 hover:text-red-100"
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}

      {/* Message list */}
      <ChatMessageList
        messages={messages}
        isStreaming={isStreaming}
        emptyState={
          <div className="max-w-sm text-center">
            <p className="mb-2 font-display text-lg text-text/90">
              Welcome to your Growth Assistant
            </p>
            <p className="text-sm font-body text-text/50">
              Ask a question about any pillar of your transformation journey —
              identity, healing, wealth, creativity, or perspective.
            </p>
          </div>
        }
      />

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </section>
  );
}
