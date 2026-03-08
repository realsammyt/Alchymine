"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { getProfile } from "@/lib/api";

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
