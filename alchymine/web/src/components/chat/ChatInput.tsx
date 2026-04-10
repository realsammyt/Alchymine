"use client";

/**
 * ChatInput — auto-growing textarea + send button for the chat panel.
 *
 * Rules:
 *   - Enter submits (unless Shift is held → newline).
 *   - Empty / whitespace-only submissions are blocked.
 *   - ``maxLength`` (2000 by default) matches the backend's Pydantic
 *     ``max_length`` so users can't paste a message that would be
 *     rejected by the server.
 *   - Shows a remaining-character counter when within the last 100.
 *   - Disabled state (e.g. during streaming) shows a spinner in the
 *     send button and prevents typing.
 *   - Auto-expands up to roughly 6 lines (~144px) before scrolling.
 */

import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  maxLength?: number;
  placeholder?: string;
}

const DEFAULT_MAX = 2000;
const MAX_HEIGHT_PX = 144; // ~6 lines at 24px line-height
const COUNTER_THRESHOLD = 100;

export default function ChatInput({
  onSend,
  disabled = false,
  maxLength = DEFAULT_MAX,
  placeholder = "Message your Growth Assistant…",
}: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Re-run autosize whenever ``value`` changes (e.g. after clear on
  // submit) so the textarea collapses back to one row.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const trimmed = value.trim();
  const canSend = !disabled && trimmed.length > 0;
  const remaining = maxLength - value.length;
  const showCounter = remaining <= COUNTER_THRESHOLD;

  const submit = () => {
    if (!canSend) return;
    onSend(trimmed);
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-white/5 bg-surface/60 p-3">
      <div className="flex items-end gap-2">
        <label htmlFor="chat-input" className="sr-only">
          Chat message
        </label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            const next = e.target.value.slice(0, maxLength);
            setValue(next);
          }}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          maxLength={maxLength}
          aria-label="Chat message"
          className="flex-1 resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm font-body text-text placeholder:text-text/30 focus:border-primary/40 focus:outline-none focus:ring-1 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          aria-label="Send message"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/20 text-primary transition-colors hover:bg-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {disabled ? (
            <span
              aria-hidden
              className="h-4 w-4 animate-spin rounded-full border-2 border-primary/60 border-t-transparent"
            />
          ) : (
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
      {showCounter && (
        <div
          className={`mt-1.5 text-right text-xs font-body ${
            remaining < 0 ? "text-red-400" : "text-text/40"
          }`}
          aria-live="polite"
        >
          {remaining} characters remaining
        </div>
      )}
    </div>
  );
}
