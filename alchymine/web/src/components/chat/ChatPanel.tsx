"use client";

/**
 * ChatPanel — composed chat experience: header, message list, input,
 * starter prompt chips, and dismissable error banner.
 *
 * Owns its own ``useChat`` instance so the parent page only needs to
 * pass an optional ``systemKey``.  When the conversation is empty (no
 * history loaded and no messages sent yet), contextual starter-prompt
 * chips are rendered so users have a low-friction entry point.
 *
 * Sprint 5 (#165): accepts ``initialPrompt`` so the SystemCoachBanner
 * can deep-link a specific coaching question into the chat.
 */

import { useEffect, useRef, useState } from "react";

import { useChat } from "@/hooks/useChat";
import { getStarterPrompts } from "@/lib/starterPrompts";

import ChatInput from "./ChatInput";
import ChatMessageList from "./ChatMessageList";

interface Props {
  /** Optional pillar scope: intelligence | healing | wealth | creative | perspective */
  systemKey?: string | null;
  /** If set, auto-send this message on first mount (from deep-link). */
  initialPrompt?: string;
}

const SYSTEM_LABELS: Record<string, string> = {
  intelligence: "Personal Intelligence",
  healing: "Ethical Healing",
  wealth: "Generational Wealth",
  creative: "Creative Development",
  perspective: "Perspective Enhancement",
};

export default function ChatPanel({
  systemKey = null,
  initialPrompt,
}: Props) {
  const {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    sendMessage,
    resetConversation,
  } = useChat({ systemKey });
  const [errorDismissed, setErrorDismissed] = useState(false);

  // Auto-send the initial prompt once (from deep-link query param).
  const initialSentRef = useRef(false);
  useEffect(() => {
    if (initialPrompt && !initialSentRef.current && !isLoadingHistory) {
      initialSentRef.current = true;
      void sendMessage(initialPrompt, systemKey);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPrompt, isLoadingHistory]);

  const visibleError = errorDismissed ? null : error;

  const handleSend = (text: string) => {
    // Reset the dismissed flag so the next error is shown.
    setErrorDismissed(false);
    void sendMessage(text, systemKey);
  };

  const starterPrompts = getStarterPrompts(systemKey);
  const showStarters = messages.length === 0 && !isLoadingHistory;
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
              {isLoadingHistory
                ? "Loading your conversation history..."
                : "Ask a question about any pillar of your transformation journey \u2014 identity, healing, wealth, creativity, or perspective."}
            </p>
            {/* Starter prompt chips */}
            {showStarters && starterPrompts.length > 0 && (
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt.label}
                    type="button"
                    onClick={() => handleSend(prompt.message)}
                    disabled={isStreaming}
                    className="rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-body text-primary/80 transition-colors hover:bg-primary/15 hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {prompt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        }
      />

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </section>
  );
}
