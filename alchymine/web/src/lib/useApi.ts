"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * Async state for API calls — tracks loading, data, and error.
 */
export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook for fetching data from the API with loading/error handling.
 *
 * @param fetcher - Async function that returns the data
 * @param deps - Dependency array (re-fetches when deps change)
 */
export function useApi<T>(
  fetcher: (() => Promise<T>) | null,
  deps: unknown[] = [],
): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!fetcher);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  const refetch = useCallback(() => setTrigger((n) => n + 1), []);

  useEffect(() => {
    if (!fetcher) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "An error occurred");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
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
