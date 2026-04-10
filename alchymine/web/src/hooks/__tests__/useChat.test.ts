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
