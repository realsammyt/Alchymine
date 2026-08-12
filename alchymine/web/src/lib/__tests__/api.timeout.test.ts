import { getMe, ApiError } from "@/lib/api";

/**
 * Regression test for the request timeout added to the API client.
 *
 * Previously `request()` called `fetch` with no timeout, so a hung
 * connection (an unreachable/unresponsive API origin on a deployed site)
 * never settled — leaving the UI stuck on a loading spinner forever after
 * login. The client now aborts requests that exceed REQUEST_TIMEOUT_MS and
 * surfaces a recoverable ApiError instead.
 */
describe("API request timeout", () => {
  const realFetch = global.fetch;

  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("rejects with a timeout ApiError when the request hangs", async () => {
    jest.useFakeTimers();

    // A fetch that never resolves on its own, but rejects (like a real
    // browser) when its AbortSignal fires.
    global.fetch = jest.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }) as unknown as typeof fetch;

    const promise = getMe();
    // Attach the assertion before advancing timers so the rejection is handled.
    const assertion = expect(promise).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      message: expect.stringMatching(/timed out/i),
    });

    // Advance past the timeout budget to trigger the abort.
    await jest.advanceTimersByTimeAsync(20000);
    await assertion;

    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("does not time out a request that resolves promptly", async () => {
    jest.useFakeTimers();

    global.fetch = jest.fn(async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: "u1", email: "a@b.co" }),
      } as Response;
    }) as unknown as typeof fetch;

    const me = await getMe();
    expect(me).toMatchObject({ id: "u1", email: "a@b.co" });
    // The pending timeout timer must be cleared so it never fires.
    expect(jest.getTimerCount()).toBe(0);
  });

  it("exports ApiError for callers to narrow on", () => {
    expect(new ApiError(0, "x")).toBeInstanceOf(Error);
  });
});
