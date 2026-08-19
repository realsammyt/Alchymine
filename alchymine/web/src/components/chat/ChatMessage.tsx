"use client";

/**
 * ChatMessage — single bubble for user or assistant.
 *
 * User messages render as plain text so markdown characters the user
 * typed are preserved literally.  Assistant messages go through
 * ``react-markdown`` so bold/italic/lists/code render correctly.  The
 * root element uses ``role="listitem"`` so ``ChatMessageList`` can
 * wrap us in a ``role="list"`` for assistive tech.
 *
 * A reply whose stream ended without the server's done sentinel carries
 * ``interrupted`` (issue #297).  It gets a note under the text and, when
 * the caller supplies ``onRetry``, a way to ask again.  Deliberately a
 * ``status`` rather than an ``alert``: nothing is broken and the text
 * above it is still worth reading, so it announces politely instead of
 * cutting in.  Red here would train people to discount the red that
 * matters.
 *
 * A reply the server delivered but could not write to the user's
 * history carries ``unsaved``.  Same convention, different fact, and no
 * retry button: the answer above is complete, and asking again would
 * spend a turn to be told the same thing.  A reply can be both, and then
 * both notes show, because they are two separate things to know.
 *
 * DRAFT copy, awaiting Tyler's sign-off.
 */

import Markdown from "react-markdown";

import type { ChatMessage as ChatMessageType } from "@/lib/chat";

interface Props {
  message: ChatMessageType;
  /** Show an animated caret at the end of the bubble (typing cue). */
  isStreaming?: boolean;
  /**
   * Send the last turn again.  Supplied only for the newest assistant
   * message: a retry re-sends the most recent question, so offering it
   * on an older bubble would answer something other than what it sits
   * under.
   */
  onRetry?: () => void;
}

const INTERRUPTED_NOTE = "This reply may be incomplete. The connection ended before it finished.";

const UNSAVED_NOTE = "This reply could not be saved to your history.";

/** Shared by both notes, so neither reads as the louder of the two. */
const NOTE_CLASSES =
  "mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-yellow-700/30 pt-2 text-xs font-body text-yellow-200/90";

export default function ChatMessage({ message, isStreaming, onRetry }: Props) {
  const isUser = message.role === "user";
  const ariaLabel = isUser ? "You said" : "Growth Assistant replied";
  const showInterrupted = !isUser && message.interrupted === true;
  const showUnsaved = !isUser && message.unsaved === true;

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
        {showInterrupted && (
          <div role="status" className={NOTE_CLASSES}>
            <span>{INTERRUPTED_NOTE}</span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-md px-1.5 py-0.5 font-medium text-yellow-100 underline underline-offset-2 transition-colors hover:bg-yellow-500/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-yellow-300 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
              >
                Ask again
              </button>
            )}
          </div>
        )}
        {showUnsaved && (
          <div role="status" className={NOTE_CLASSES}>
            <span>{UNSAVED_NOTE}</span>
          </div>
        )}
      </div>
    </div>
  );
}
