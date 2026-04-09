"use client";

/**
 * ChatMessageList — scrollable, auto-scrolling list of chat bubbles.
 *
 * Auto-scroll behaviour: whenever ``messages`` changes (new bubble or
 * streaming content update) we smooth-scroll the bottom sentinel into
 * view.  If the user has manually scrolled up we respect that by
 * tracking a ``pinnedToBottom`` ref — the auto-scroll is suppressed
 * until they scroll back down to within ~80px of the bottom.
 *
 * Typing indicator: when ``isAwaitingFirstToken`` is true (streaming
 * has started but no assistant content has arrived yet) we show a
 * subtle three-dot indicator inside the last assistant bubble via the
 * ``isStreaming`` flag on ``ChatMessage``.  The parent (``ChatPanel``)
 * is responsible for computing that flag.
 */

import { useEffect, useRef, useState } from "react";

import type { ChatMessage as ChatMessageType } from "@/lib/chat";

import ChatMessage from "./ChatMessage";

interface Props {
  messages: ChatMessageType[];
  isStreaming: boolean;
  emptyState?: React.ReactNode;
}

const NEAR_BOTTOM_PX = 80;

export default function ChatMessageList({
  messages,
  isStreaming,
  emptyState,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [pinnedToBottom, setPinnedToBottom] = useState(true);

  // Track whether the user is pinned to the bottom of the scroller.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setPinnedToBottom(distanceFromBottom <= NEAR_BOTTOM_PX);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-scroll on new messages / streaming content.
  useEffect(() => {
    if (!pinnedToBottom) return;
    // jsdom doesn't implement scrollIntoView — guard for tests and any
    // ancient runtime without the API.
    const el = bottomRef.current;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, pinnedToBottom]);

  // Identify the last assistant message for typing-indicator logic.
  const lastAssistantId = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role === "assistant") return msg.id;
    }
    return null;
  })();

  const showEmpty = messages.length === 0;

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-4"
      aria-live="polite"
      aria-busy={isStreaming}
    >
      {showEmpty ? (
        <div className="flex h-full items-center justify-center">
          {emptyState ?? (
            <p className="text-center text-sm text-text/40 font-body">
              Ask your Growth Assistant anything to begin.
            </p>
          )}
        </div>
      ) : (
        <div role="list" className="flex flex-col gap-3">
          {messages.map((m) => (
            <ChatMessage
              key={m.id}
              message={m}
              isStreaming={isStreaming && m.id === lastAssistantId}
            />
          ))}
        </div>
      )}
      <div ref={bottomRef} aria-hidden />
    </div>
  );
}
