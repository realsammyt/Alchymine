/**
 * useChat hook — unit tests.
 *
 * We mock ``global.fetch`` with a tiny stream shim that yields the
 * chunks we want the hook to see.  The shim only implements the
 * surface area ``streamChat`` actually touches (``ok``, ``status``,
 * ``body.getReader()``) so we don't need a real ReadableStream impl.
 */

import { StrictMode } from "react";

import { act, renderHook, waitFor } from "@testing-library/react";

import { useChat } from "@/hooks/useChat";

// ─── Stream shim helpers ─────────────────────────────────────────────

function makeSseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const queue = [...frames];
  const reader = {
    read: jest.fn(async () => {
      if (queue.length === 0) {
        return { done: true, value: undefined };
      }
      const next = queue.shift() as string;
      return { done: false, value: encoder.encode(next) };
    }),
    releaseLock: jest.fn(),
  };
  return {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  } as unknown as Response;
}

function makeErrorResponse(status: number, detail: string): Response {
  return {
    ok: false,
    status,
    body: null,
    json: jest.fn().mockResolvedValue({ detail }),
  } as unknown as Response;
}

function makeJsonResponse(data: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: jest.fn().mockResolvedValue(data),
  } as unknown as Response;
}

beforeEach(() => {
  jest.clearAllMocks();
  (global as unknown as { fetch: jest.Mock }).fetch = jest.fn();
});

describe("useChat", () => {
  it("streams assistant chunks into the last message (happy path)", async () => {
    // First call: history fetch; second call: chat stream.
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse([
          "data: Hello\n\n",
          "data:  there\n\n",
          "event: done\ndata: \n\n",
        ]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));

    // Wait for history load.
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.error).toBeNull();
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({
      role: "user",
      content: "Hi",
    });
    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "Hello there",
    });
  });

  it("sends the system_key in the request body when provided", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse(["data: ok\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: "healing" }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi", "healing");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    // The second call is the chat POST.
    const call = (global.fetch as jest.Mock).mock.calls[1];
    const init = call[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({
      message: "Hi",
      system_key: "healing",
    });
  });

  it("surfaces a friendly 400 error and drops the empty assistant bubble", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeErrorResponse(400, "Content flagged by safety filter"),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("bad");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.error).toMatch(/safety filter/i);
    // User message kept; assistant placeholder removed.
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("maps 401 to a sign-in prompt", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeErrorResponse(401, "Not authenticated"),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("hey");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.error).toMatch(/sign in/i);
  });

  it("records a network error as the error state", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("hey");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.error).toMatch(/failed to fetch/i);
    // Assistant placeholder removed; user message kept.
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("abort during streaming keeps accumulated content without setting error", async () => {
    // Custom shim: first read yields content, second read never resolves
    // until aborted, at which point it throws an AbortError.
    const encoder = new TextEncoder();
    let aborted = false;
    const reader = {
      read: jest.fn().mockImplementation(async () => {
        if (!aborted) {
          aborted = true;
          return { done: false, value: encoder.encode("data: partial\n\n") };
        }
        const err = new Error("The operation was aborted.");
        err.name = "AbortError";
        throw err;
      }),
      releaseLock: jest.fn(),
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: { getReader: () => reader },
      } as unknown as Response);

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    // Kick off a send and immediately cancel.
    let sendPromise: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage("hi");
    });
    act(() => {
      result.current.cancelStream();
    });
    await act(async () => {
      await sendPromise!;
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.error).toBeNull();
    // Assistant bubble retained with whatever content we got.
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].content).toBe("partial");
  });

  it("resetConversation clears messages and error", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse(["data: ok\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("hi");
    });
    await waitFor(() => expect(result.current.messages).toHaveLength(2));

    act(() => {
      result.current.resetConversation();
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.error).toBeNull();
  });

  it("blocks empty/whitespace-only messages", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(makeJsonResponse([]));

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    // Only 1 call: the history fetch.  No chat POST.
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result.current.messages).toHaveLength(0);
  });

  it("loads history on mount and populates messages", async () => {
    const historyItems = [
      { id: "h1", role: "user", content: "Previous Q", created_at: "2026-04-08T10:00:00Z" },
      { id: "h2", role: "assistant", content: "Previous A", created_at: "2026-04-08T10:00:01Z" },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce(makeJsonResponse(historyItems));

    const { result } = renderHook(() => useChat({ systemKey: "healing" }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({
      id: "h1",
      role: "user",
      content: "Previous Q",
    });
    expect(result.current.messages[1]).toMatchObject({
      id: "h2",
      role: "assistant",
      content: "Previous A",
    });

    // Verify the history fetch URL includes system_key.
    const historyCall = (global.fetch as jest.Mock).mock.calls[0];
    expect(historyCall[0]).toContain("system_key=healing");
  });

  it("skips history load when systemKey is undefined", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(makeJsonResponse([]));

    const { result } = renderHook(() => useChat());

    // Give it a tick to see if it would fire.
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    // No fetch at all — history loading was skipped.
    expect(global.fetch).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it("handles history fetch failure gracefully", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useChat({ systemKey: null }));

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    // Should not set an error — history failure is non-fatal.
    expect(result.current.error).toBeNull();
    expect(result.current.messages).toHaveLength(0);
  });
});

/**
 * Issue #297. An interrupted reply used to be indistinguishable from a
 * finished one, and a reply that failed mid-flight was thrown away
 * wholesale. Both are about the same thing: the user is entitled to know
 * what happened to the text in front of them.
 */
describe("useChat interrupted replies", () => {
  it("keeps a partial reply and marks it when the stream ends without the sentinel", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makeSseResponse(["data: Start of an ans\n\n"]));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "Start of an ans",
      interrupted: true,
    });
    // A cut connection is not a fault worth a red banner. The bubble
    // says what happened, quietly, where the text is.
    expect(result.current.error).toBeNull();
  });

  it("keeps what already rendered when the read fails mid-stream", async () => {
    const encoder = new TextEncoder();
    let read = 0;
    const reader = {
      read: jest.fn().mockImplementation(async () => {
        read += 1;
        if (read === 1) {
          return { done: false, value: encoder.encode("data: most of it\n\n") };
        }
        throw new TypeError("network error");
      }),
      releaseLock: jest.fn(),
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: { getReader: () => reader },
      } as unknown as Response);

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    // Evicting the bubble here replaced a mostly-good reply with a
    // banner, which is strictly less than the user already had.
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1]).toMatchObject({
      content: "most of it",
      interrupted: true,
    });
    expect(result.current.error).not.toBeNull();
  });

  it("still drops the placeholder when the failure lands before any content", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    // Nothing to keep, so an empty bubble next to the banner would be
    // noise rather than content.
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("leaves a completed reply unmarked", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse(["data: All of it\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.messages[1].interrupted).toBeFalsy();
  });

  it("retryLastTurn sends the last user message again as a new turn", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makeSseResponse(["data: cut off\n\n"]))
      .mockResolvedValueOnce(
        makeSseResponse(["data: the whole answer\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: "healing" }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("What should I try?", "healing");
    });
    await waitFor(() => expect(result.current.messages[1].interrupted).toBe(true));

    await act(async () => {
      await result.current.retryLastTurn();
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    // A retry is a new turn, not an edit: the question is asked again,
    // so both exchanges stay on screen and in the transcript.
    expect(result.current.messages).toHaveLength(4);
    expect(result.current.messages[2]).toMatchObject({
      role: "user",
      content: "What should I try?",
    });
    expect(result.current.messages[3]).toMatchObject({
      role: "assistant",
      content: "the whole answer",
    });

    // The retry keeps the scope the original turn was sent on.
    const retryCall = (global.fetch as jest.Mock).mock.calls[2];
    expect(JSON.parse((retryCall[1] as RequestInit).body as string)).toEqual({
      message: "What should I try?",
      system_key: "healing",
    });
  });

  it("retryLastTurn does nothing before anything has been sent", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(makeJsonResponse([]));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.retryLastTurn();
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result.current.messages).toHaveLength(0);
  });
});

/**
 * The server delivered the reply and could not write it to the user's
 * history, and it says so with an `unsaved` frame before `done`. The
 * reply is whole, so it stays exactly as it rendered; the note under it
 * is about the transcript, not about the answer.
 */
describe("useChat replies the server could not save", () => {
  it("marks the reply and keeps every word of it", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse([
          "data: All of it\n\n",
          "event: unsaved\ndata: \n\n",
          "event: done\ndata: \n\n",
        ]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "All of it",
      unsaved: true,
    });
    // Not interrupted: nothing is missing from what is on screen, and a
    // note offering a retry would send them after text they already have.
    expect(result.current.messages[1].interrupted).toBeFalsy();
    // Not an error either. A red banner across the conversation would
    // outweigh what actually happened.
    expect(result.current.error).toBeNull();
  });

  it("leaves an ordinary reply unmarked", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makeSseResponse(["data: All of it\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    expect(result.current.messages[1].unsaved).toBeFalsy();
  });
});

/**
 * Issue #313. Under StrictMode React runs each effect, cleans it up, and
 * runs it again. The history effect one-shotted on a ref that the
 * cleanup never reset, so the second run returned early while the first
 * run's `cancelled` flag suppressed both the messages and the
 * `setIsLoadingHistory(false)`. The result in dev was a permanent
 * "Loading your conversation history..." over a conversation that had
 * already arrived.
 */
describe("useChat history under StrictMode", () => {
  it("finishes loading history when the effect runs twice", async () => {
    const historyItems = [
      {
        id: "h1",
        role: "user",
        content: "Previous Q",
        created_at: "2026-04-08T10:00:00Z",
      },
    ];
    (global.fetch as jest.Mock).mockResolvedValue(makeJsonResponse(historyItems));

    const { result } = renderHook(() => useChat({ systemKey: "healing" }), {
      wrapper: StrictMode,
    });

    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toMatchObject({ content: "Previous Q" });
  });
});

// ─── Plan refusals ───────────────────────────────────────────────────

function makePlanGateResponse(status: number, detail: unknown): Response {
  // `clone` matters: readPlanGate clones before reading so the generic
  // error path still has a body. A mock without it would send every
  // refusal down the plain-error branch and pass for the wrong reason.
  const res = {
    ok: false,
    status,
    body: null,
    json: jest.fn().mockResolvedValue({ detail }),
  };
  return {
    ...res,
    clone: () => res as unknown as Response,
  } as unknown as Response;
}

const ALLOWANCE_DETAIL = {
  code: "plan_allowance_reached",
  message: "You've used this month's included coaching. Upgrade to keep going.",
  retry_at: "2026-09-01T00:00:00+00:00",
  meter: "spend_micros_monthly",
  plan: "pro",
  upgrade_url: "/pricing",
};

describe("useChat plan refusals", () => {
  it("sets upsell rather than error when the plan cannot pay", async () => {
    // The two are kept apart because they render differently: a yellow
    // banner with somewhere to go versus a red one that reads as broken.
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makePlanGateResponse(429, ALLOWANCE_DETAIL));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("How do I start?");
    });

    await waitFor(() => expect(result.current.upsell).not.toBeNull());
    expect(result.current.upsell?.code).toBe("plan_allowance_reached");
    expect(result.current.upsell?.upgradeUrl).toBe("/pricing");
    expect(result.current.upsell?.retryAt).toEqual(
      new Date("2026-09-01T00:00:00+00:00"),
    );
    expect(result.current.error).toBeNull();
  });

  it("drops the empty assistant bubble but keeps what the user typed", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makePlanGateResponse(429, ALLOWANCE_DETAIL));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("How do I start?");
    });

    await waitFor(() => expect(result.current.upsell).not.toBeNull());
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toMatchObject({
      role: "user",
      content: "How do I start?",
    });
  });

  it("clears the upsell on the next send", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makePlanGateResponse(429, ALLOWANCE_DETAIL))
      .mockResolvedValueOnce(
        makeSseResponse(["data: Sure\n\n", "event: done\ndata: \n\n"]),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("first");
    });
    await waitFor(() => expect(result.current.upsell).not.toBeNull());

    await act(async () => {
      await result.current.sendMessage("second");
    });

    await waitFor(() => expect(result.current.upsell).toBeNull());
  });

  it("treats an entitlement refusal the same way", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(
        makePlanGateResponse(402, {
          code: "plan_upgrade_required",
          message: "Coaching chat is part of a paid plan. Upgrade to start a conversation.",
          retry_at: null,
          meter: null,
          plan: "free",
          upgrade_url: "/pricing",
        }),
      );

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(() => expect(result.current.upsell).not.toBeNull());
    expect(result.current.upsell?.code).toBe("plan_upgrade_required");
    expect(result.current.upsell?.retryAt).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("still reports a genuine fault as an error", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce(makeJsonResponse([]))
      .mockResolvedValueOnce(makeErrorResponse(500, "boom"));

    const { result } = renderHook(() => useChat({ systemKey: null }));
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false));

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.upsell).toBeNull();
  });
});
