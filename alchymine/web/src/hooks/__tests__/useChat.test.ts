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

beforeEach(() => {
  jest.clearAllMocks();
  (global as unknown as { fetch: jest.Mock }).fetch = jest.fn();
});

describe("useChat", () => {
  it("streams assistant chunks into the last message (happy path)", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      makeSseResponse([
        "data: Hello\n\n",
        "data:  there\n\n",
        "event: done\ndata: \n\n",
      ]),
    );

    const { result } = renderHook(() => useChat());

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
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      makeSseResponse(["data: ok\n\n", "event: done\ndata: \n\n"]),
    );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("Hi", "healing");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));

    const call = (global.fetch as jest.Mock).mock.calls[0];
    const init = call[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({
      message: "Hi",
      system_key: "healing",
    });
  });

  it("surfaces a friendly 400 error and drops the empty assistant bubble", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      makeErrorResponse(400, "Content flagged by safety filter"),
    );

    const { result } = renderHook(() => useChat());

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
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      makeErrorResponse(401, "Not authenticated"),
    );

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("hey");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.error).toMatch(/sign in/i);
  });

  it("records a network error as the error state", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new TypeError("Failed to fetch"),
    );

    const { result } = renderHook(() => useChat());

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
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: { getReader: () => reader },
    } as unknown as Response);

    const { result } = renderHook(() => useChat());

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
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      makeSseResponse(["data: ok\n\n", "event: done\ndata: \n\n"]),
    );

    const { result } = renderHook(() => useChat());

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
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(global.fetch).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });
});
