/**
 * useChat hook — unit tests.
 *
 * We mock ``global.fetch`` with a tiny stream shim that yields the
 * chunks we want the hook to see.  The shim only implements the
 * surface area ``streamChat`` actually touches (``ok``, ``status``,
 * ``body.getReader()``) so we don't need a real ReadableStream impl.
 */

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
