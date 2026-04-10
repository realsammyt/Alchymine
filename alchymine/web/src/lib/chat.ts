/**
 * Growth Assistant chat — types and low-level SSE streaming client.
 *
 * The backend endpoint (``POST /api/v1/chat``) responds with a
 * ``text/event-stream``.  Each LLM chunk is delivered as:
 *
 *     data: <text chunk>\n\n
 *
 * and the stream terminates with a sentinel:
 *
 *     event: done\ndata: \n\n
 *
 * Errors emitted by the server mid-stream come as:
 *
 *     event: error\ndata: <error message>\n\n
 *
 * We expose a single async generator ``streamChat`` that yields the
 * content chunks and throws on transport/HTTP/error-event failures.
 * The hook layer (``useChat``) owns React state and wires this to the
 * UI; the transport is kept side-effect-free so it can be unit tested
 * with a mocked ``fetch``.
 */

// ─── Types ──────────────────────────────────────────────────────────

/** A single chat message displayed in the UI. */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string; // ISO 8601
}

/** Backend request body for POST /api/v1/chat. */
export interface ChatRequest {
  message: string;
  system_key: string | null;
}

/** Error thrown by ``streamChat`` on non-transport failures. */
export class ChatError extends Error {
  readonly status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ChatError";
    this.status = status;
  }
}

/** Backend response shape for GET /api/v1/chat/history items. */
export interface ChatHistoryItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  system_key: string | null;
  created_at: string; // ISO 8601
}

// ─── Transport ──────────────────────────────────────────────────────

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1";

/**
 * Resolve any legacy localStorage token for the migration path.  New
 * sessions rely on the ``httpOnly access_token`` cookie sent via
 * ``credentials: "include"`` but we match ``lib/api.ts`` exactly so
 * the chat endpoint works for both flows.
 */
function getLegacyAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Stream a chat reply from the backend, yielding content chunks as
 * they arrive.
 *
 * Throws ``ChatError`` (with HTTP status when available) on non-OK
 * responses or on ``event: error`` frames emitted by the server.
 * Abort via the provided signal yields the native ``AbortError``
 * which callers can detect by name.
 */
export async function* streamChat(
  request: ChatRequest,
  signal?: AbortSignal,
  ephemeral?: boolean,
): AsyncGenerator<string> {
  const url = ephemeral
    ? `${BASE}/chat?ephemeral=true`
    : `${BASE}/chat`;
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...getLegacyAuthHeaders(),
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    // Try to surface the FastAPI ``detail`` message when present so the
    // UI can show the safety-filter reason on 400s, etc.
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Body wasn't JSON — fall through with the HTTP status message.
    }
    throw new ChatError(detail, response.status);
  }

  if (!response.body) {
    // Some test environments (and ancient browsers) may not expose a
    // ReadableStream.  Treat this as an empty reply rather than hanging.
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let nextEvent: string | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by blank lines; individual fields by
      // single newlines.  We parse line-by-line because our frames are
      // small and we want early delivery of ``data:`` chunks.
      let newlineIdx: number;
      while ((newlineIdx = buffer.indexOf("\n")) !== -1) {
        const rawLine = buffer.slice(0, newlineIdx);
        buffer = buffer.slice(newlineIdx + 1);
        const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;

        if (line === "") {
          // Blank line → frame boundary; clear any pending event name.
          nextEvent = null;
          continue;
        }

        if (line.startsWith("event:")) {
          nextEvent = line.slice(6).trim();
          continue;
        }

        if (line.startsWith("data:")) {
          // Strip a single leading space per the SSE spec.
          const data = line.slice(5).replace(/^ /, "");
          if (nextEvent === "done") {
            return;
          }
          if (nextEvent === "error") {
            throw new ChatError(data || "Chat stream error");
          }
          if (data.length > 0) {
            yield data;
          }
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Reader may already be released on abort/error — safe to ignore.
    }
  }
}

// ─── Chat history ───────────────────────────────────────────────────

/**
 * Fetch persisted chat history from the backend.
 *
 * Returns messages in chronological (oldest-first) order, matching the
 * shape used by ``ChatMessage`` in the UI layer.
 */
export async function fetchChatHistory(
  systemKey: string | null,
  limit: number = 50,
  q?: string,
): Promise<ChatMessage[]> {
  const params = new URLSearchParams();
  if (systemKey) params.set("system_key", systemKey);
  params.set("limit", String(limit));
  if (q) params.set("q", q);

  const response = await fetch(`${BASE}/chat/history?${params.toString()}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...getLegacyAuthHeaders(),
    },
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Not JSON — use the status message.
    }
    throw new ChatError(detail, response.status);
  }

  const items = (await response.json()) as ChatHistoryItem[];

  return items.map((item) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    createdAt: item.created_at,
  }));
}
