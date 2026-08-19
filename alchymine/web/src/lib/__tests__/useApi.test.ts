/**
 * useApi: the async state every first-visit surface sits on.
 *
 * Issue #313. The hook aborts its in-flight request on cleanup and then
 * no-ops in both `.then` and `.catch` when the signal is aborted. That
 * is right for an attempt a newer one has replaced, and wrong for the
 * last attempt there is: nothing sets `loading` back to false, so the
 * consumer renders its loading state forever. `ApiStateView`'s retry
 * button only exists on the error branch, so there is not even a way
 * out by hand. Observed on /journey (stuck spinner) and on the practice
 * nudge (renders nothing at all while loading, so a strand hides it).
 *
 * Driving that branch needs the hook's own AbortController, which is
 * internal. The stub below captures the instances it hands out so a test
 * can abort one at the moment the real trigger would have, which is the
 * only way to reach the branch from outside.
 */

import { act, renderHook, waitFor } from "@testing-library/react";

import { useApi } from "../useApi";

/** A promise with its resolve/reject exposed, so a test can settle it. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const RealAbortController = global.AbortController;
let controllers: AbortController[] = [];

beforeEach(() => {
  controllers = [];
  class CapturingAbortController extends RealAbortController {
    constructor() {
      super();
      controllers.push(this);
    }
  }
  (global as unknown as { AbortController: unknown }).AbortController =
    CapturingAbortController;
});

afterEach(() => {
  (global as unknown as { AbortController: unknown }).AbortController =
    RealAbortController;
});

describe("useApi", () => {
  it("moves from loading to data on a successful fetch", async () => {
    const fetcher = jest.fn().mockResolvedValue({ value: 42 });

    const { result } = renderHook(() => useApi(fetcher, []));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
  });

  it("surfaces a failure as an error the consumer can retry from", async () => {
    const fetcher = jest.fn().mockRejectedValue(new Error("upstream is down"));

    const { result } = renderHook(() => useApi(fetcher, []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("upstream is down");
    expect(result.current.data).toBeNull();
  });

  it("sits idle with no fetcher", async () => {
    const { result } = renderHook(() => useApi<null>(null, []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBeNull();
  });

  it("retries once when the only attempt in flight is aborted", async () => {
    // The strand: a request that got aborted with nothing following it.
    // Whatever aborted it, the component is still mounted and still has
    // nothing to show, so one more try beats a spinner that never ends.
    const first = deferred<string>();
    const fetcher = jest
      .fn()
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => Promise.resolve("second time lucky"));

    const { result } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(controllers).toHaveLength(1));

    await act(async () => {
      controllers[0].abort();
      first.reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBe("second time lucky");
  });

  it("gives up after one retry rather than looping", async () => {
    const attempts: ReturnType<typeof deferred<string>>[] = [];
    const fetcher = jest.fn().mockImplementation(() => {
      const next = deferred<string>();
      attempts.push(next);
      return next.promise;
    });

    const { result } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(controllers).toHaveLength(1));

    await act(async () => {
      controllers[0].abort();
      attempts[0].reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

    await act(async () => {
      controllers[1].abort();
      attempts[1].reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });

    // A bounded retry, not a reconnect loop hammering a service that is
    // already having a bad day.
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(fetcher).toHaveBeenCalledTimes(2);

    // And giving up is a state, not a shrug.  Loading has to end where
    // the retry budget does, because the error branch is the only one
    // `ApiStateView` draws a Try Again button on: staying at loading:true
    // is the stuck spinner this whole hook exists to prevent.
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeNull();
  });

  it("settles a fetcher that resolves after its own abort", async () => {
    // The `.then` twin of the branch above: an attempt whose signal
    // aborted but whose promise resolves anyway, with the retry budget
    // already spent.  It must not slip out of the hook leaving loading
    // true either.
    const attempts: ReturnType<typeof deferred<string>>[] = [];
    const fetcher = jest.fn().mockImplementation(() => {
      const next = deferred<string>();
      attempts.push(next);
      return next.promise;
    });

    const { result } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(controllers).toHaveLength(1));

    await act(async () => {
      controllers[0].abort();
      attempts[0].resolve("too late to matter");
      await Promise.resolve();
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

    await act(async () => {
      controllers[1].abort();
      attempts[1].resolve("too late again");
      await Promise.resolve();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    // The data belongs to a request nobody is waiting on any more.
    expect(result.current.data).toBeNull();
  });

  it("gives a fetch on new deps its own retry budget", async () => {
    // The budget is per fetch, not per hook instance.  A page that
    // stranded once on Monday's key must not hand Tuesday's key a spent
    // budget and a permanent error.
    const attempts: ReturnType<typeof deferred<string>>[] = [];
    const fetcher = jest.fn().mockImplementation(() => {
      const next = deferred<string>();
      attempts.push(next);
      return next.promise;
    });

    const { rerender } = renderHook(
      ({ key }: { key: string }) => useApi(fetcher, [key]),
      { initialProps: { key: "a" } },
    );
    await waitFor(() => expect(controllers).toHaveLength(1));

    // Spend the budget: strand, retry, strand again.
    await act(async () => {
      controllers[0].abort();
      attempts[0].reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    await act(async () => {
      controllers[1].abort();
      attempts[1].reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(fetcher).toHaveBeenCalledTimes(2);

    rerender({ key: "b" });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));

    await act(async () => {
      controllers[2].abort();
      attempts[2].reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(4));
  });

  it("does not retry an attempt a newer one already replaced", async () => {
    const first = deferred<string>();
    const fetcher = jest
      .fn()
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => Promise.resolve("for the new key"));

    const { rerender, result } = renderHook(
      ({ key }: { key: string }) => useApi(fetcher, [key]),
      { initialProps: { key: "a" } },
    );
    await waitFor(() => expect(controllers).toHaveLength(1));

    // Changing the deps aborts the first attempt and starts a second.
    rerender({ key: "b" });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

    await act(async () => {
      first.reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });

    await waitFor(() => expect(result.current.data).toBe("for the new key"));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("does not retry after the component unmounts", async () => {
    const first = deferred<string>();
    const fetcher = jest.fn().mockImplementation(() => first.promise);

    const { unmount } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(controllers).toHaveLength(1));

    unmount();
    await act(async () => {
      first.reject(new DOMException("Aborted", "AbortError"));
      await Promise.resolve();
    });

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("refetch starts a fresh attempt", async () => {
    const fetcher = jest
      .fn()
      .mockResolvedValueOnce("first")
      .mockResolvedValueOnce("second");

    const { result } = renderHook(() => useApi(fetcher, []));
    await waitFor(() => expect(result.current.data).toBe("first"));

    act(() => {
      result.current.refetch();
    });

    await waitFor(() => expect(result.current.data).toBe("second"));
  });
});
