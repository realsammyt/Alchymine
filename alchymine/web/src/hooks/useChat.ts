"use client";

/**
 * useChat — React hook managing a single Growth Assistant conversation.
 *
 * Owns:
 *   - ``messages``    the in-memory conversation (no history loading —
 *                     that's tracked in issue #164 / Sprint 3).
 *   - ``isStreaming`` true from when a send is issued until the
 *                     assistant stream completes, errors, or is
 *                     aborted.
 *   - ``error``       non-null when the most recent send failed
 *                     (network, HTTP, SSE error frame).  The user
 *                     message is *kept* in ``messages`` so the user
 *                     can see what they tried to say.  So is any
 *                     assistant text that had already arrived; only an
 *                     empty placeholder is removed.
 *
 * Interrupted replies (issue #297): a stream that ends without its done
 * sentinel, and any fault that lands after some text has rendered, mark
 * that assistant message ``interrupted``.  The bubble then says so and
 * offers ``retryLastTurn``.  The alternative was the old behaviour,
 * where a truncated reply looked exactly like a finished one and a
 * failed one was deleted out from under the reader.
 *
 * Abort semantics:
 *   - ``cancelStream()`` triggers the ``AbortController`` attached to
 *     the in-flight fetch.  Any content already received stays in the
 *     assistant message; ``isStreaming`` flips false; ``error`` is
 *     *not* set (user-initiated cancel is not an error).
 *   - ``resetConversation()`` clears messages + error + cancels any
 *     in-flight stream.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  ChatError,
  ChatInterruptedError,
  ChatUpsellError,
  fetchChatHistory,
  streamChat,
  type ChatMessage,
} from "@/lib/chat";
import type { PlanGateError } from "@/lib/planGate";

interface UseChatOptions {
  /** System key to load history for on mount.  Pass `undefined` to skip. */
  systemKey?: string | null;
}

interface UseChatResult {
  messages: ChatMessage[];
  isStreaming: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  /**
   * Non-null when the last send was refused because of the caller's
   * plan.  Kept apart from ``error`` because the two render
   * differently: this one is a yellow upsell with somewhere to go,
   * ``error`` is a red fault.
   */
  upsell: PlanGateError | null;
  sendMessage: (content: string, systemKey?: string | null) => Promise<void>;
  /**
   * Send the last user message again, on the scope it was sent with.
   * The affordance offered next to an interrupted reply.  It is a new
   * turn rather than an edit: the question appears again and both
   * exchanges stay in the transcript, because the server has no notion
   * of replacing a turn and inventing one client-side would put the UI
   * and the history out of step.
   */
  retryLastTurn: () => Promise<void>;
  cancelStream: () => void;
  resetConversation: () => void;
}

function makeId(): string {
  // ``crypto.randomUUID`` is available in all supported browsers and in
  // the jsdom test environment via the Web Crypto API shim.  Guard for
  // the ancient fallback case anyway so SSR doesn't explode.
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function useChat(options?: UseChatOptions): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [upsell, setUpsell] = useState<PlanGateError | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // What ``retryLastTurn`` re-sends: the message and the scope it went
  // out on, so a retry from a system page does not fall back to the
  // general coach.
  const lastTurnRef = useRef<{ content: string; systemKey: string | null } | null>(
    null,
  );

  const systemKey = options?.systemKey;

  // Make sure we abort any in-flight fetch if the component unmounts
  // mid-stream — prevents "setState on unmounted component" warnings
  // and cancels server-side work the user will never see.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Load persisted chat history when the scope is known, and again if it
  // changes.  The `cancelled` flag is the only guard: a ref that latched
  // on the first run and was never reset in cleanup made this effect
  // unrunnable a second time, which under StrictMode meant the run that
  // was allowed to set state was the one that had already been cancelled
  // history arrived, nothing rendered, and the loading state never
  // cleared (issue #313).  Dropping the ref costs one extra fetch per
  // StrictMode mount in dev and nothing at all in production.
  useEffect(() => {
    // `systemKey` can be explicitly `undefined` to skip loading.
    if (systemKey === undefined) return;

    let cancelled = false;
    setIsLoadingHistory(true);

    fetchChatHistory(systemKey ?? null)
      .then((history) => {
        if (!cancelled && history.length > 0) {
          // Never clobber messages sent while history was loading (e.g. the
          // auto-sent initialPrompt from a coach-banner deep link) — a plain
          // setMessages(history) would silently erase the in-flight exchange.
          setMessages((prev) => (prev.length > 0 ? prev : history));
        }
      })
      .catch(() => {
        // History load failure is non-fatal — the user can still chat.
      })
      .finally(() => {
        if (!cancelled) setIsLoadingHistory(false);
      });

    return () => {
      cancelled = true;
    };
  }, [systemKey]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const resetConversation = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setError(null);
    setUpsell(null);
    setIsStreaming(false);
    // History is not reloaded: a reset starts a fresh conversation, not a
    // fresh session.  The user clicked "New conversation" deliberately,
    // and the effect above only re-runs on a scope change.
    lastTurnRef.current = null;
  }, []);

  const sendMessage = useCallback(
    async (content: string, systemKey: string | null = null): Promise<void> => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) return;

      // Fresh send → clear any previous error or upsell banner.
      setError(null);
      setUpsell(null);

      const userMessage: ChatMessage = {
        id: makeId(),
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
      };
      const assistantId = makeId();
      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
      };

      // Optimistic insert: user message first, then empty assistant
      // bubble the typing indicator will anchor to.
      setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
      setIsStreaming(true);
      lastTurnRef.current = { content: trimmed, systemKey };

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulated = "";
      let aborted = false;
      let interrupted = false;
      try {
        for await (const chunk of streamChat(
          { message: trimmed, system_key: systemKey },
          controller.signal,
        )) {
          accumulated += chunk;
          // Functional update so concurrent sends can't clobber state.
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: accumulated } : m,
            ),
          );
        }
      } catch (err: unknown) {
        // Native fetch abort raises ``AbortError`` (DOMException).  We
        // also respect the signal flag directly in case a runtime
        // throws something else on abort.
        if (
          controller.signal.aborted ||
          (err instanceof Error && err.name === "AbortError")
        ) {
          aborted = true;
        } else if (err instanceof ChatUpsellError) {
          // Their plan, not a fault. Rendered as an upsell, and the
          // empty assistant bubble goes away the same as on an error.
          setUpsell(err.gate);
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        } else if (err instanceof ChatInterruptedError) {
          // The stream closed without its done sentinel.  Nothing here
          // failed as such: what arrived is real, and what is missing is
          // the rest of it.  That reads as a note on the bubble rather
          // than a red banner across the conversation.
          interrupted = true;
        } else {
          let message = "Something went wrong. Please try again.";
          if (err instanceof ChatError) {
            if (err.status === 401) {
              message = "You need to sign in to chat.";
            } else if (err.status === 400) {
              message = err.message || "Message blocked by safety filter.";
            } else if (err.message) {
              message = err.message;
            }
          } else if (err instanceof Error && err.message) {
            message = err.message;
          }
          setError(message);
          if (accumulated.length > 0) {
            // A fault mid-reply. The text already on screen is the
            // user's to keep: evicting it traded a mostly-good answer
            // for a banner, which is strictly less than they had.
            interrupted = true;
          } else {
            // Nothing arrived, so the placeholder is an empty bubble
            // next to the banner. Keep the user message so they can see
            // what they sent.
            setMessages((prev) => prev.filter((m) => m.id !== assistantId));
          }
        }
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setIsStreaming(false);
        if (aborted && accumulated.length === 0) {
          // User cancelled before any content arrived — drop the empty
          // assistant bubble so the UI doesn't show a stray placeholder.
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        }
        if (interrupted) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, interrupted: true } : m,
            ),
          );
        }
      }
    },
    [isStreaming],
  );

  const retryLastTurn = useCallback(async (): Promise<void> => {
    const last = lastTurnRef.current;
    if (!last) return;
    await sendMessage(last.content, last.systemKey);
  }, [sendMessage]);

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    upsell,
    sendMessage,
    retryLastTurn,
    cancelStream,
    resetConversation,
  };
}

export type { ChatMessage };
