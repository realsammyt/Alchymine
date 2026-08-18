/**
 * Growth Assistant chat — types and low-level SSE streaming client.
 *
 * The backend endpoint (``POST /api/v1/chat``) responds with a
 * ``text/event-stream``.  Each LLM chunk is delivered as one event:
 *
 *     data: <text chunk>\n\n
 *
 * A ``data:`` field ends at the first newline, so a chunk that carries
 * newlines spans several ``data:`` lines inside that same event, which
 * we rejoin with newlines at the blank line that closes it:
 *
 *     data: <first line>\ndata: <second line>\n\n
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

import { PlanGateError, readPlanGate } from "@/lib/planGate";

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

/**
 * Thrown when the caller's plan cannot pay for the turn they asked for.
 *
 * The gate runs in the handler body, above the stream, so this arrives
 * as a real 402 or 429 *before* it opens. That matters: once the stream is
 * open the status line is already sent, and a quota state buried in an
 * ``event: error`` frame looks like success to everything above the SSE
 * parser.
 */
export class ChatUpsellError extends ChatError {
  readonly gate: PlanGateError;

  constructor(gate: PlanGateError, status: number) {
    super(gate.message, status);
    this.name = "ChatUpsellError";
    this.gate = gate;
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

/** What one completed SSE event means to the caller. */
type FrameOutcome =
  | { kind: "chunk"; text: string }
  | { kind: "done" }
  | { kind: "error"; message: string }
  | { kind: "empty" };

/**
 * Resolve one completed event from its name and its ``data:`` lines.
 *
 * The lines rejoin with newlines because that is what the server split
 * them on: a ``data:`` field cannot carry a newline, so a chunk with
 * paragraph breaks in it arrives as several lines of one event. An
 * event with no data lines, or one whose data is empty, carries nothing
 * to show.
 */
function resolveFrame(name: string | null, dataLines: string[]): FrameOutcome {
  if (name === "done") return { kind: "done" };

  const text = dataLines.join("\n");

  if (name === "error") {
    return { kind: "error", message: text || "Chat stream error" };
  }
  return text.length > 0 ? { kind: "chunk", text } : { kind: "empty" };
}

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
    // A plan refusal is structured and renders as an upsell rather than
    // an error, so it is separated out before the generic path flattens
    // the body to a string.
    const gate = await readPlanGate(response);
    if (gate) throw new ChatUpsellError(gate, response.status);

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
  let eventName: string | null = null;
  let dataLines: string[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE fields are separated by single newlines and events by blank
      // lines.  We read line-by-line but deliver per event, because the
      // lines of one event are pieces of a single chunk of text.  Each
      // model chunk is its own event, so delivery stays as early as it
      // ever was.
      let newlineIdx: number;
      while ((newlineIdx = buffer.indexOf("\n")) !== -1) {
        const rawLine = buffer.slice(0, newlineIdx);
        buffer = buffer.slice(newlineIdx + 1);
        const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;

        if (line !== "") {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            // Strip a single leading space per the SSE spec.
            dataLines.push(line.slice(5).replace(/^ /, ""));
          }
          // Any other line is a comment or a field we don't use, and the
          // spec says to ignore it.  Nothing the server sends takes this
          // path: content travels in ``data:`` lines only.
          continue;
        }

        // Blank line: the event is complete.
        const outcome = resolveFrame(eventName, dataLines);
        eventName = null;
        dataLines = [];

        if (outcome.kind === "done") return;
        if (outcome.kind === "error") throw new ChatError(outcome.message);
        if (outcome.kind === "chunk") yield outcome.text;
      }
    }

    // The reader is finished.  Data lines still pending here belong to an
    // event whose terminating blank line never arrived, which means the
    // connection closed mid-reply.  The text in them is real, so it goes
    // to the caller rather than being discarded silently.  Any trailing
    // partial line left in ``buffer`` stays unparsed: a half-written
    // field cannot be told apart from a complete one.
    if (dataLines.length > 0) {
      const outcome = resolveFrame(eventName, dataLines);
      if (outcome.kind === "error") throw new ChatError(outcome.message);
      if (outcome.kind === "chunk") yield outcome.text;
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
