"use client";

/**
 * A quiet invitation back to today's practice protocol.
 *
 * It appears on the logged-in home surface when the user has a protocol
 * today and has not worked through all of it, and it disappears for the
 * rest of that day the moment it is dismissed.
 *
 * Three rules shape everything below.
 *
 * It never degrades the page. While its two reads are in flight, or
 * after either of them fails, it renders nothing at all: no spinner, no
 * skeleton, no error card. A nudge is the least important thing on the
 * screen, and the cost of getting it wrong is a broken dashboard.
 *
 * It never pressures. There is no count of what is left, no streak, no
 * comparison, and no deadline. The register is an invitation the user is
 * free to decline, which is why the dismiss control says what it does
 * and the copy offers rather than asks.
 *
 * It costs nothing once declined. Dismissal is checked before the reads
 * are issued, so a dismissed day makes no requests.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/useApi";
import { localDayKey } from "@/lib/localDay";
import {
  getPracticeToday,
  listPracticeLog,
  type PracticeLogEntry,
  type PracticeLogListResponse,
  type ProtocolItem,
  type TodayResponse,
} from "@/lib/api";

/**
 * The localStorage prefix a dismissal is stored under. The user's local
 * day is appended, so today's dismissal cannot silence tomorrow.
 */
export const NUDGE_DISMISS_PREFIX = "practice_nudge_dismissed_";

/**
 * One page is far more than a day of practice holds. It exists so a log
 * with an unusual day in it cannot pull an unbounded response.
 */
const LOG_PAGE_SIZE = 100;

/** A practice's identity across packs: two packs may share a slug. */
function practiceKey(packId: string, slug: string): string {
  return `${packId}/${slug}`;
}

/**
 * The practices in today's protocol with no completed row today.
 *
 * A skipped row is not a completion. Saying no to a practice is an
 * honest answer the log records, but it is not the same as having done
 * it, so it does not tick the practice off.
 */
export function remainingPractices(
  items: ProtocolItem[],
  log: PracticeLogEntry[],
): ProtocolItem[] {
  const done = new Set(
    log
      .filter((entry) => entry.status === "completed")
      .map((entry) => practiceKey(entry.pack_id, entry.practice_slug)),
  );
  return items.filter((item) => !done.has(practiceKey(item.pack_id, item.slug)));
}

export default function PracticeNudge() {
  // The user's local day, fixed for the life of the component, matching
  // the practice page. It is both the query the reads take and the key
  // the dismissal is filed under.
  const dayKey = useMemo(() => localDayKey(), []);
  const storageKey = `${NUDGE_DISMISS_PREFIX}${dayKey}`;

  // Starts dismissed. localStorage is unreadable during server render,
  // so beginning in the visible state would flash the nudge at a user
  // who already waved it away this morning.
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(storageKey) !== null);
    } catch {
      // Private mode or a blocked origin. Show the nudge and accept
      // that dismissing it will not survive the reload: the alternative
      // is hiding a feature from everyone whose browser is locked down.
      setDismissed(false);
    }
  }, [storageKey]);

  // Both reads hang off `dismissed`, so a dismissed day issues none.
  const today = useApi<TodayResponse>(
    dismissed ? null : (signal) => getPracticeToday(dayKey, { signal }),
    [dayKey, dismissed],
  );

  const log = useApi<PracticeLogListResponse>(
    dismissed
      ? null
      : (signal) =>
          listPracticeLog({
            from: dayKey,
            to: dayKey,
            status: "completed",
            perPage: LOG_PAGE_SIZE,
            signal,
          }),
    [dayKey, dismissed],
  );

  const handleDismiss = useCallback(() => {
    try {
      localStorage.setItem(storageKey, "1");
    } catch {
      // The write failing is not a reason to keep showing something the
      // user has just declined. It comes back tomorrow either way.
    }
    setDismissed(true);
  }, [storageKey]);

  if (dismissed) return null;
  if (today.loading || log.loading) return null;
  if (today.error || log.error) return null;
  if (!today.data || !log.data) return null;

  // More completions than came back means the day already holds plenty.
  // Deciding from one page would be deciding from part of the day.
  if (log.data.total > log.data.entries.length) return null;

  if (today.data.items.length === 0) return null;
  if (remainingPractices(today.data.items, log.data.entries).length === 0) {
    return null;
  }

  return (
    <aside
      aria-labelledby="practice-nudge-heading"
      data-testid="practice-nudge"
      className="rounded-xl border border-primary/20 bg-primary/5 p-4 sm:p-5"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2
            id="practice-nudge-heading"
            className="font-display text-sm font-medium text-primary"
          >
            Today&apos;s practice is ready
          </h2>
          <p className="font-body text-xs text-text/50 mt-0.5 leading-relaxed">
            Your protocol is here whenever you want it. Do what fits and leave
            the rest.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Link
            href="/practice"
            className="touch-target inline-flex items-center gap-1.5 rounded-lg border border-primary/20 px-3 py-1.5 text-xs font-body text-primary transition-colors duration-200 hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Open today&apos;s practice
          </Link>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="Dismiss today's practice invitation"
            className="touch-target inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-body text-text/50 transition-colors duration-200 hover:text-text/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Not now
          </button>
        </div>
      </div>
    </aside>
  );
}
