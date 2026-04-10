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
 *                     can see what they tried to say; the unfinished
 *                     assistant placeholder (if any) is removed.
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
  fetchChatHistory,
  streamChat,
  type ChatMessage,
} from "@/lib/chat";

interface UseChatOptions {
  /** System key to load history for on mount.  Pass `undefined` to skip. */
  systemKey?: string | null;
}

interface UseChatResult {
  messages: ChatMessage[];
  isStreaming: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  sendMessage: (content: string, systemKey?: string | null) => Promise<void>;
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
  const abortRef = useRef<AbortController | null>(null);
  const historyLoadedRef = useRef(false);

  const systemKey = options?.systemKey;

  // Make sure we abort any in-flight fetch if the component unmounts
  // mid-stream — prevents "setState on unmounted component" warnings
  // and cancels server-side work the user will never see.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Load persisted chat history on mount.  Only runs once per hook
  // instance (guarded by historyLoadedRef).  The systemKey is passed
  // explicitly rather than using the dependency array so a `null`
  // key still triggers history load (all messages).
  useEffect(() => {
    if (historyLoadedRef.current) return;
    // `systemKey` can be explicitly `undefined` to skip loading.
    if (systemKey === undefined) return;
    historyLoadedRef.current = true;

    let cancelled = false;
    setIsLoadingHistory(true);

    fetchChatHistory(systemKey ?? null)
      .then((history) => {
        if (!cancelled && history.length > 0) {
          setMessages(history);
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
    setIsStreaming(false);
    // Do NOT reset historyLoadedRef — a reset starts a fresh
    // conversation, not a fresh session.  The user clicked "New
    // conversation" intentionally.
  }, []);

  const sendMessage = useCallback(
    async (content: string, systemKey: string | null = null): Promise<void> => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) return;

      // Fresh send → clear any previous error banner.
      setError(null);

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

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulated = "";
      let aborted = false;
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
          // Remove the empty assistant placeholder so the error banner
          // isn't accompanied by a dangling blank bubble.  Keep the
          // user message so they can see what they sent.
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
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
      }
    },
    [isStreaming],
  );

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    error,
    sendMessage,
    cancelStream,
    resetConversation,
  };
}

export type { ChatMessage };
