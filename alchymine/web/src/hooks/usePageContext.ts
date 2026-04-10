"use client";

/**
 * usePageContext — derive the Alchymine system key from the current
 * Next.js App Router pathname.
 *
 * Maps top-level route segments (`/healing`, `/wealth`, `/intelligence`,
 * `/creative`, `/perspective`) to the corresponding system key that the
 * backend chat endpoint accepts.  Pages that don't belong to a specific
 * pillar (e.g. `/chat`, `/dashboard`) return `null`, which means the
 * Growth Assistant operates in its general coaching mode.
 *
 * Usage:
 * ```tsx
 * const { systemKey, systemLabel } = usePageContext();
 * <ChatPanel systemKey={systemKey} />
 * ```
 */

import { usePathname } from "next/navigation";
import { useMemo } from "react";

/** Valid system keys accepted by `POST /api/v1/chat`. */
export type SystemKey =
  | "intelligence"
  | "healing"
  | "wealth"
  | "creative"
  | "perspective";

/** Human-readable labels keyed by system. */
const SYSTEM_LABELS: Record<SystemKey, string> = {
  intelligence: "Personal Intelligence",
  healing: "Ethical Healing",
  wealth: "Generational Wealth",
  creative: "Creative Development",
  perspective: "Perspective Enhancement",
};

/** Top-level route segments that map 1-to-1 to system keys. */
const ROUTE_TO_SYSTEM: Record<string, SystemKey> = {
  intelligence: "intelligence",
  healing: "healing",
  wealth: "wealth",
  creative: "creative",
  perspective: "perspective",
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
