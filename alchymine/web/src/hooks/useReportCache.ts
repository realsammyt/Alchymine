"use client";

/**
 * useReportCache — persist the latest report result per system in
 * localStorage so the Growth Assistant can reference it on the first
 * chat turn without re-fetching from the backend.
 *
 * Each system key gets its own storage slot
 * (`alchymine:report:<systemKey>`).  The hook exposes a `getContext()`
 * helper that returns a short summary string suitable for injection
 * into the chat request body as additional context.
 *
 * Data shape is intentionally loose (`Record<string, unknown>`) because
 * the five systems produce different report formats.  The hook stores
 * the raw JSON blob and extracts a best-effort summary.
 */

import { useCallback, useEffect, useRef } from "react";

const STORAGE_PREFIX = "alchymine:report:";

/** Lightweight summary extracted from a cached report for chat context. */
export interface ReportContext {
  /** The system the report belongs to. */
  systemKey: string;
  /** A short JSON string with the most salient fields. */
  summary: string;
}

/**
 * Best-effort extraction of summary information from a raw report blob.
 *
 * The goal is NOT to send the entire report to the chat endpoint — just
 * enough context so the assistant can reference recent results without
 * the user having to repeat them.  We cap the output at ~1500 chars.
 */
function extractSummary(data: Record<string, unknown>): string {
  // Many report shapes include a top-level `summary` or `highlights` key.
  const candidates: string[] = [];

  for (const key of ["summary", "highlights", "overview", "profile"]) {
    if (data[key] != null) {
      const serialized = JSON.stringify(data[key]);
      if (serialized.length <= 1500) {
        candidates.push(`${key}: ${serialized}`);
      } else {
        candidates.push(`${key}: ${serialized.slice(0, 1500)}...`);
      }
    }
  }

  if (candidates.length > 0) {
    return candidates.join("\n");
  }

  // Fallback: top-level keys as a brief overview.
  const keys = Object.keys(data).slice(0, 10);
  return `Report fields: ${keys.join(", ")}`;
}

export interface UseReportCacheResult {
  /** Persist a report blob for the given system. */
  saveReport: (systemKey: string, data: Record<string, unknown>) => void;
  /** Retrieve the cached report blob (or `null`). */
  getReport: (systemKey: string) => Record<string, unknown> | null;
  /** Build a chat-context string from the cached report (or `null`). */
  getContext: (systemKey: string | null) => ReportContext | null;
}

export function useReportCache(): UseReportCacheResult {
  // Cache parsed reports in a ref so repeated reads within a render
  // cycle don't re-parse JSON from localStorage.
  const cache = useRef<Record<string, Record<string, unknown> | null>>({});

  // Hydrate cache from localStorage on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith(STORAGE_PREFIX)) {
          const systemKey = key.slice(STORAGE_PREFIX.length);
          const raw = localStorage.getItem(key);
          if (raw) {
            cache.current[systemKey] = JSON.parse(raw) as Record<string, unknown>;
          }
        }
      }
    } catch {
      // localStorage may be unavailable (SSR, private browsing quota).
    }
  }, []);

  const saveReport = useCallback(
    (systemKey: string, data: Record<string, unknown>) => {
      cache.current[systemKey] = data;
      try {
        localStorage.setItem(STORAGE_PREFIX + systemKey, JSON.stringify(data));
      } catch {
        // Quota exceeded — silent fail; the in-memory cache still works.
      }
    },
    [],
  );

  const getReport = useCallback((systemKey: string): Record<string, unknown> | null => {
    if (cache.current[systemKey] != null) {
      return cache.current[systemKey];
    }
    // Fallback: try localStorage directly.
    if (typeof window === "undefined") return null;
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + systemKey);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        cache.current[systemKey] = parsed;
        return parsed;
      }
    } catch {
      // Corrupt data — treat as missing.
    }
    return null;
  }, []);

  const getContext = useCallback(
    (systemKey: string | null): ReportContext | null => {
      if (!systemKey) return null;
      const data = getReport(systemKey);
      if (!data) return null;
      return { systemKey, summary: extractSummary(data) };
    },
    [getReport],
  );

  return { saveReport, getReport, getContext };
}
