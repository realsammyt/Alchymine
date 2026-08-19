"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { getProfile, getReport, ApiError } from "@/lib/api";

/**
 * Async state for API calls — tracks loading, data, and error.
 */
export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/** How many times an aborted final attempt is retried on its own. */
const MAX_ABORT_RETRIES = 1;

/**
 * Shown when the retry budget is spent and the attempt still stranded.
 *
 * It says what happened and what to do, and nothing about signals or
 * controllers: from where the reader sits, the request stopped and the
 * button is right there.  DRAFT copy, awaiting Tyler's sign-off.
 */
const GAVE_UP_MESSAGE = "The request was interrupted. Try again.";

/** True when two dependency arrays differ in the way React compares them. */
function depsDiffer(previous: unknown[] | null, next: unknown[]): boolean {
  if (previous === null || previous.length !== next.length) return true;
  return previous.some((value, index) => !Object.is(value, next[index]));
}

/**
 * Hook for fetching data from the API with loading/error handling.
 *
 * The fetcher receives an `AbortSignal` that is aborted when the effect
 * cleans up (deps change or component unmounts).  Pass this signal
 * through to `fetch()` calls to cancel in-flight requests and prevent
 * race conditions.
 *
 * An aborted attempt writes no state, which is right when a newer
 * attempt has taken over and wrong when there is no newer attempt: the
 * hook would sit at `loading: true` with nothing left to move it, and
 * `ApiStateView`'s retry button only exists on the error branch, so
 * there is no way out by hand either.  That strand is what left /journey
 * spinning and the practice nudge invisible on a first visit (issue
 * #313).  So an abort that is still the current attempt, on a mounted
 * component, buys one automatic retry.  It is bounded deliberately: a
 * service having a bad day should meet one more request, not a loop.
 *
 * When that budget is spent and the attempt strands again, the hook
 * settles into the error state rather than returning quietly.  Returning
 * quietly leaves `loading` true forever, which is the same permanent
 * spinner by a longer route, and `ApiStateView` only draws its retry
 * button on the error branch.  An honest error the reader can act on
 * beats a truthful-looking spinner they cannot.
 *
 * The budget belongs to one fetch, not to the hook: when the deps
 * change, the next fetch is asking a different question and starts with
 * its own.  A retry re-runs this effect too, so the reset keys off the
 * deps actually changing rather than off the effect running.
 *
 * @param fetcher - Async function that returns the data (receives AbortSignal)
 * @param deps - Dependency array (re-fetches when deps change)
 */
export function useApi<T>(
  fetcher: ((signal: AbortSignal) => Promise<T>) | null,
  deps: unknown[] = [],
): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!fetcher);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);
  // The attempt currently in flight, so a late rejection can tell "I was
  // replaced" from "I am all there is".
  const currentControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);
  const abortRetriesRef = useRef(0);
  const previousDepsRef = useRef<unknown[] | null>(null);

  const refetch = useCallback(() => setTrigger((n) => n + 1), []);

  // Declared first so its cleanup runs before the fetch effect's, and a
  // real unmount is already recorded by the time the abort below fires.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    // A different question deserves its own retry budget, and this runs
    // before the early return so a hook that starts with no fetcher
    // still records the deps it saw.
    if (depsDiffer(previousDepsRef.current, deps)) {
      previousDepsRef.current = [...deps];
      abortRetriesRef.current = 0;
    }

    if (!fetcher) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    currentControllerRef.current = controller;
    setLoading(true);
    setError(null);

    const settled = () => {
      abortRetriesRef.current = 0;
    };

    /** Nothing newer has started, and there is still someone to show it to. */
    const isStranded = () =>
      mountedRef.current && currentControllerRef.current === controller;

    /**
     * Handle an attempt that ended on an aborted signal.
     *
     * Three outcomes, and only the first two used to exist: a newer
     * attempt has taken over and this one goes quiet, the budget pays for
     * one more try, or the budget is spent and this is the end of the
     * line.  The budget is not refunded here on purpose: this deps
     * generation has had its retry, and what the reader gets instead is a
     * state with a button in it.
     */
    const retryOrGiveUp = () => {
      if (!isStranded()) return;
      if (abortRetriesRef.current < MAX_ABORT_RETRIES) {
        abortRetriesRef.current += 1;
        setTrigger((n) => n + 1);
        return;
      }
      setError(GAVE_UP_MESSAGE);
      setLoading(false);
    };

    fetcher(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          settled();
          setData(result);
          setLoading(false);
          return;
        }
        // Resolved, but for a request that was already called off. The
        // value is not this attempt's to show, and the strand is the
        // same one the rejection path handles.
        retryOrGiveUp();
      })
      .catch((err) => {
        if (controller.signal.aborted) {
          retryOrGiveUp();
          return;
        }
        settled();
        setError(err instanceof Error ? err.message : "An error occurred");
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger, ...deps]);

  return { data, loading, error, refetch };
}

/**
 * Reads intake data stored in sessionStorage by the discover flow.
 */
export function getStoredIntake(): {
  fullName?: string;
  birthDate?: string;
  birthTime?: string;
  birthCity?: string;
  intention?: string;
  intentions?: string[];
} | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem("alchymine_intake");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Reads the last generated report ID from sessionStorage.
 */
export function getStoredReportId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("alchymine_report_id");
}

export type StoredIntake = ReturnType<typeof getStoredIntake>;

export interface IntakeState {
  data: StoredIntake;
  loading: boolean;
}

/**
 * Hook that polls for report status when a report ID is stored in sessionStorage.
 * Returns the current status so system pages can show a generating state.
 */
export function useReportStatus(): {
  status: "idle" | "pending" | "generating" | "complete" | "failed";
  reportId: string | null;
} {
  const [status, setStatus] = useState<
    "idle" | "pending" | "generating" | "complete" | "failed"
  >("idle");
  const [reportId, setReportId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const id = getStoredReportId();
    if (!id) {
      setStatus("idle");
      return;
    }
    setReportId(id);

    let cancelled = false;

    async function check() {
      try {
        const report = await getReport(id!);
        if (cancelled) return;
        if (report.status === "pending" || report.status === "generating") {
          setStatus(report.status as "pending" | "generating");
        } else if (report.status === "complete") {
          setStatus("complete");
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (report.status === "failed") {
          setStatus("failed");
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (err) {
        if (cancelled) return;
        // 202 means still processing
        if (err instanceof ApiError && err.status === 202) {
          setStatus("generating");
          return;
        }
        // Other errors — treat as idle (no report or auth issue)
        setStatus("idle");
        if (pollRef.current) clearInterval(pollRef.current);
      }
    }

    check();
    pollRef.current = setInterval(check, 3000);

    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return { status, reportId };
}

/**
 * Hook that returns intake data with cross-device sync.
 *
 * Tries sessionStorage first (fast, same-tab), then falls back to the
 * server profile (persisted across devices). This enables a user to
 * complete intake on one device and see results on another.
 *
 * When data is loaded from the server, it is cached to sessionStorage
 * so subsequent renders in the same tab don't flash empty state.
 */
export function useIntake(userId: string | null | undefined): IntakeState {
  const sessionIntake = useMemo(() => getStoredIntake(), []);
  const [intake, setIntake] = useState(sessionIntake);
  const needsServer = !sessionIntake?.fullName || !sessionIntake?.birthDate;
  const [loading, setLoading] = useState(needsServer && !!userId);

  useEffect(() => {
    if (intake?.fullName && intake?.birthDate) {
      setLoading(false);
      return;
    }
    if (!userId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getProfile(userId)
      .then((profile) => {
        if (profile.intake) {
          const fromProfile = {
            fullName: profile.intake.full_name,
            birthDate: profile.intake.birth_date,
            birthTime: profile.intake.birth_time ?? undefined,
            birthCity: profile.intake.birth_city ?? undefined,
            intentions: profile.intake.intentions,
            intention: profile.intake.intention,
          };
          setIntake(fromProfile);
          // Cache to sessionStorage so subsequent renders don't flash
          try {
            sessionStorage.setItem(
              "alchymine_intake",
              JSON.stringify(fromProfile),
            );
          } catch {
            /* storage quota or SSR — ignore */
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userId, intake?.fullName, intake?.birthDate]);

  return { data: intake, loading };
}
