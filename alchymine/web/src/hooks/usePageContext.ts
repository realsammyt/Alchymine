"use client";

/**
 * usePageContext — derive the Alchymine system key from the current
 * Next.js App Router pathname.
 *
 * Maps top-level route segments (`/healing`, `/wealth`, `/intelligence`,
 * `/creative`, `/perspective`, `/practice`) to the corresponding system
 * key that the backend chat endpoint accepts.  Pages that don't belong
 * to a specific scope (e.g. `/chat`, `/dashboard`) return `null`, which
 * means the Growth Assistant operates in its general coaching mode.
 *
 * Usage:
 * ```tsx
 * const { systemKey, systemLabel } = usePageContext();
 * <ChatPanel systemKey={systemKey} />
 * ```
 */

import { usePathname } from "next/navigation";
import { useMemo } from "react";

/**
 * Valid system keys accepted by `POST /api/v1/chat`.
 *
 * Must match `_VALID_SYSTEM_KEYS` in `alchymine/api/routers/chat.py`.
 * Every map below is a `Record<SystemKey, ...>`, so adding a key here
 * without filling them in is a type error rather than a runtime gap.
 *
 * This array is the single enumeration on the web side: code that needs
 * the keys at runtime (query-param validation, test cases) imports it
 * rather than retyping the list, and `SystemKey` is derived from it so
 * the two can't drift.
 */
export const SYSTEM_KEYS = [
  "intelligence",
  "healing",
  "wealth",
  "creative",
  "perspective",
  "practice",
] as const;

export type SystemKey = (typeof SYSTEM_KEYS)[number];

/** Human-readable labels keyed by system. */
const SYSTEM_LABELS: Record<SystemKey, string> = {
  intelligence: "Personal Intelligence",
  healing: "Ethical Healing",
  wealth: "Generational Wealth",
  creative: "Creative Development",
  perspective: "Perspective Enhancement",
  practice: "Practice Integration",
};

/** Top-level route segments that map 1-to-1 to system keys. */
const ROUTE_TO_SYSTEM: Record<string, SystemKey> = {
  intelligence: "intelligence",
  healing: "healing",
  wealth: "wealth",
  creative: "creative",
  perspective: "perspective",
  practice: "practice",
};

export interface PageContext {
  /** System key for the current page, or `null` for general coaching. */
  systemKey: SystemKey | null;
  /** Human-readable label, or `null` when no system is active. */
  systemLabel: string | null;
  /** The raw pathname from Next.js. */
  pathname: string;
}

/**
 * Derive the system context from the current route.
 *
 * The first non-empty segment of the pathname is matched against the
 * known pillar routes.  Sub-routes (e.g. `/healing/breathwork`) still
 * resolve to their parent system.
 */
export function usePageContext(): PageContext {
  const pathname = usePathname();

  return useMemo(() => {
    // Extract the first non-empty path segment.
    const segments = pathname.split("/").filter(Boolean);
    const first = segments[0] ?? "";
    const systemKey = ROUTE_TO_SYSTEM[first] ?? null;
    const systemLabel = systemKey ? SYSTEM_LABELS[systemKey] : null;

    return { systemKey, systemLabel, pathname };
  }, [pathname]);
}
