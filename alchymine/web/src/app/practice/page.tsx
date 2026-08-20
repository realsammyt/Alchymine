"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import ApiStateView from "@/components/shared/ApiStateView";
import Button from "@/components/shared/Button";
import SystemCoachBanner from "@/components/chat/SystemCoachBanner";
import DailyProtocol from "@/components/practice/DailyProtocol";
import PracticeRhythm from "@/components/practice/PracticeRhythm";
import ProtocolSettings from "@/components/practice/ProtocolSettings";
import { useApi } from "@/lib/useApi";
import { localDayKey } from "@/lib/localDay";
import {
  createIntegration,
  getPracticeSummary,
  getPracticeToday,
  listPracticeLog,
  listPractices,
  logPractice,
  type IntegrationCreate,
  type PracticeDefinition,
  type PracticeLogCreate,
  type PracticeLogListResponse,
  type PracticeResponse,
  type PracticeSummaryResponse,
  type TodayResponse,
} from "@/lib/api";

/**
 * One page is far more than a day of practice holds. It bounds the
 * read rather than paging it: a day with more rows than this is not a
 * day whose cards can be drawn from one page anyway.
 */
const LOG_PAGE_SIZE = 100;

function PracticeInner() {
  // The user's local day, fixed for the life of the page. Recomputing it
  // per render would swap the key under an in-flight write for anyone
  // who leaves the tab open across midnight, and a page that has been
  // open that long can be reloaded.
  const dayKey = useMemo(() => localDayKey(), []);

  // Bumped when the user asks for a different set, so the recommender
  // recomputes instead of replaying today's stored protocol.
  const [refreshNonce, setRefreshNonce] = useState(0);
  // Bumped after every logged practice, so the rhythm below reflects it.
  const [logNonce, setLogNonce] = useState(0);

  const today = useApi<TodayResponse>(
    (signal) =>
      getPracticeToday(dayKey, { refresh: refreshNonce > 0, signal }),
    [dayKey, refreshNonce],
  );

  const summary = useApi<PracticeSummaryResponse>(
    (signal) => getPracticeSummary(dayKey, signal),
    [dayKey, logNonce],
  );

  const library = useApi<PracticeResponse[]>(
    (signal) => listPractices({ signal }),
    [],
  );

  // What the user has already done today. Completion is optimistic and
  // lives in component state, so without this read a reload handed back
  // a day of untouched cards while the rows sat in the log (#312).
  //
  // One unfiltered read rather than one per status: the cards show both
  // what was done and what was waved off, and the route takes a single
  // status per call. It is not tied to `logNonce`; a write the page
  // already knows about does not need reading back.
  const logToday = useApi<PracticeLogListResponse>(
    (signal) =>
      listPracticeLog({
        from: dayKey,
        to: dayKey,
        perPage: LOG_PAGE_SIZE,
        signal,
      }),
    [dayKey],
  );

  // More rows match than came back means this page is a fragment of the
  // day, and cards filled from a fragment would be guesswork. They fall
  // back to un-hydrated, which is what they were before this read.
  const loggedToday = useMemo(() => {
    const data = logToday.data;
    if (!data) return null;
    if (data.total > data.entries.length) return null;
    return data.entries;
  }, [logToday.data]);

  // True once the day's log has settled, whether it came back or failed.
  const [logSettled, setLogSettled] = useState(false);
  useEffect(() => {
    if (!logToday.loading) setLogSettled(true);
  }, [logToday.loading]);

  // The protocol waits for the log the first time, so the cards mount in
  // the state they are already in. It waits only that once.
  //
  // A second read is a retry from the notice below, and taking the page
  // back to a spinner for it would unmount the protocol and throw away
  // every card with it: a completion the user has just tapped whose
  // write is still in flight, anything typed into a prompt, every
  // dismissal. The retried log merges into the cards in place instead,
  // which is what DailyProtocol's merge was built for.
  //
  // If the protocol itself failed there is nothing left to wait for, and
  // waiting would only hold a spinner over an error.
  const protocolLoading =
    today.loading || (logToday.loading && !logSettled && !today.error);

  // The protocol carries a title and a summary but not the practice's
  // self-check question, so the library index supplies it. One request
  // for the whole library beats one per card.
  const definitions = useMemo(() => {
    const index = new Map<string, PracticeDefinition>();
    for (const entry of library.data ?? []) {
      index.set(`${entry.pack_id}/${entry.practice.slug}`, entry.practice);
    }
    return index;
  }, [library.data]);

  const lookup = useCallback(
    (packId: string, slug: string) => definitions.get(`${packId}/${slug}`),
    [definitions],
  );

  const handleLog = useCallback(
    (entry: PracticeLogCreate) => logPractice(entry),
    [],
  );

  const handleIntegrate = useCallback(
    (entry: IntegrationCreate) => createIntegration(entry),
    [],
  );

  const handleLogged = useCallback(() => setLogNonce((n) => n + 1), []);

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <div className="max-w-3xl mx-auto flex flex-col gap-8">
        <header className="flex flex-col gap-2">
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-text">
            Today&apos;s practice
          </h1>
          <p className="text-sm font-body text-text/50 leading-relaxed max-w-prose">
            A few practices, balanced across the five capacities. Do what fits
            and leave the rest.
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-1">
            <Link
              href="/practice/library"
              className="touch-target inline-flex items-center text-sm font-body text-primary underline underline-offset-4 transition-colors duration-200 hover:text-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
            >
              Browse the library
            </Link>
            <button
              type="button"
              onClick={() => setRefreshNonce((n) => n + 1)}
              className="touch-target px-3 py-1.5 rounded-lg text-sm font-body text-text/50 border border-white/10 transition-colors duration-200 hover:text-text/70 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              Show me different practices
            </button>
          </div>
        </header>

        {/* Under the header rather than in it: the settings belong with
            the other affordances above the practices, and keeping the
            toggle next to its own panel keeps the focus order sane.
            A saved change clears the stored protocol server-side, so
            reading today again is what makes the setting visible now
            rather than tomorrow. */}
        <ProtocolSettings onSaved={today.refetch} />

        <SystemCoachBanner systemKey="practice" />

        <ApiStateView
          loading={summary.loading}
          error={summary.error}
          loadingText="Loading your last seven days..."
          onRetry={summary.refetch}
        >
          {summary.data && (
            <PracticeRhythm
              dayKey={summary.data.day_key}
              last7={summary.data.last_7}
              daysPracticed={summary.data.days_practiced_last_7}
            />
          )}
        </ApiStateView>

        <ApiStateView
          loading={protocolLoading}
          error={today.error}
          loadingText="Putting today's practice together..."
          onRetry={today.refetch}
        >
          {today.data && (
            <div className="flex flex-col gap-4">
              {/* The protocol is the page, so a log that will not load
                  costs the reader the read-back and nothing else. Saying
                  so beats letting them find out by logging a practice
                  twice. DRAFT copy, awaiting Tyler's sign-off. */}
              {logToday.error && (
                <div
                  role="status"
                  className="card-surface px-5 py-4 flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <p className="text-sm font-body text-text/60 leading-relaxed">
                    We couldn&apos;t check what you logged earlier today, so
                    these cards may look untouched. Nothing you logged is lost.
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={logToday.refetch}
                    className="shrink-0 touch-target"
                  >
                    Try again
                  </Button>
                </div>
              )}
              <DailyProtocol
                today={today.data}
                loggedToday={loggedToday}
                lookup={lookup}
                onLog={handleLog}
                onIntegrate={handleIntegrate}
                onLogged={handleLogged}
              />
            </div>
          )}
        </ApiStateView>
      </div>
    </main>
  );
}

export default function PracticePage() {
  return (
    <ProtectedRoute>
      <PracticeInner />
    </ProtectedRoute>
  );
}
