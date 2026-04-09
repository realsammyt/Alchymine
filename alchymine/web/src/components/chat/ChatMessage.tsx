"use client";

/**
 * ChatMessage — single bubble for user or assistant.
 *
 * User messages render as plain text so markdown characters the user
 * typed are preserved literally.  Assistant messages go through
 * ``react-markdown`` so bold/italic/lists/code render correctly.  The
 * root element uses ``role="listitem"`` so ``ChatMessageList`` can
 * wrap us in a ``role="list"`` for assistive tech.
 */

import Markdown from "react-markdown";

import type { ChatMessage as ChatMessageType } from "@/lib/chat";

interface Props {
  message: ChatMessageType;
  /** Show an animated caret at the end of the bubble (typing cue). */
  isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming }: Props) {
  const isUser = message.role === "user";
  const ariaLabel = isUser ? "You said" : "Growth Assistant replied";

  return (
    <div
      role="listitem"
      aria-label={ariaLabel}
      className={`flex ${isUser ? "justify-end" : "justify-start"} w-full`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm font-body leading-relaxed shadow-sm ${
          isUser
            ? "bg-primary/15 text-text rounded-br-sm border border-primary/20"
            : "bg-white/5 text-text/90 rounded-bl-sm border border-white/5"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="chat-markdown prose prose-invert prose-sm max-w-none break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            {message.content ? (
              <Markdown>{message.content}</Markdown>
            ) : (
              <span className="text-text/40" aria-hidden>
                &hellip;
              </span>
            )}
          </div>
        )}
        {isStreaming && !isUser && (
          <span
            aria-hidden
            className="ml-1 inline-block h-3.5 w-1.5 animate-pulse rounded-sm bg-primary/60 align-middle"
          />
        )}
      </div>
    </div>
  );
}
