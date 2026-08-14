"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import ApiStateView from "@/components/shared/ApiStateView";
import SystemCoachBanner from "@/components/chat/SystemCoachBanner";
import DailyProtocol from "@/components/practice/DailyProtocol";
import PracticeRhythm from "@/components/practice/PracticeRhythm";
import { useApi } from "@/lib/useApi";
import { localDayKey } from "@/lib/localDay";
import {
  createIntegration,
  getPracticeSummary,
  getPracticeToday,
  listPractices,
  logPractice,
  type IntegrationCreate,
  type PracticeDefinition,
  type PracticeLogCreate,
  type PracticeResponse,
  type PracticeSummaryResponse,
  type TodayResponse,
} from "@/lib/api";

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
          loading={today.loading}
          error={today.error}
          loadingText="Putting today's practice together..."
          onRetry={today.refetch}
        >
          {today.data && (
            <DailyProtocol
              today={today.data}
              lookup={lookup}
              onLog={handleLog}
              onIntegrate={handleIntegrate}
              onLogged={handleLogged}
            />
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
