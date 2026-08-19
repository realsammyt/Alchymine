"use client";

import { useId, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import ApiStateView from "@/components/shared/ApiStateView";
import JourneyBalance from "@/components/journey/JourneyBalance";
import JourneyChart from "@/components/journey/JourneyChart";
import JourneyEmpty from "@/components/journey/JourneyEmpty";
import { useApi } from "@/lib/useApi";
import { anchorDayLabel, localDayKey, parseDayKey } from "@/lib/localDay";
import {
  getJourneyTimeseries,
  JOURNEY_WINDOWS,
  type JourneyTimeseriesResponse,
  type JourneyWindow,
} from "@/lib/api";

/** The window the page opens on. Long enough to have a shape, short
 *  enough to still read a column at a time on a phone. */
const DEFAULT_WINDOW: JourneyWindow = 30;

interface StatProps {
  value: number;
  label: string;
}

function Stat({ value, label }: StatProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="font-body text-xs uppercase tracking-wider text-text/60 order-2">
        {label}
      </dt>
      <dd className="font-display text-2xl font-light text-text order-1 m-0">
        {value}
      </dd>
    </div>
  );
}

function JourneyBody() {
  // The user's local day, fixed for the life of the page. Recomputing it
  // per render would move the window under the reader for anyone who
  // leaves the tab open across midnight, and a page open that long can
  // be reloaded.
  const dayKey = useMemo(() => localDayKey(), []);
  const [windowDays, setWindowDays] = useState<JourneyWindow>(DEFAULT_WINDOW);
  const windowGroupId = useId();

  const journey = useApi<JourneyTimeseriesResponse>(
    (signal) => getJourneyTimeseries(dayKey, windowDays, signal),
    [dayKey, windowDays],
  );

  const data = journey.data;
  // Never having practiced is a different state from a quiet month. The
  // first has nothing to draw; the second is a real, readable window of
  // zeros that still belongs to somebody who has been at this a while.
  const neverPracticed =
    data !== null && data.totals.first_practice_day === null;

  return (
    <main
      id="main-content"
      className="min-h-screen px-4 sm:px-6 lg:px-8 py-8 sm:py-12"
    >
      <div className="max-w-3xl mx-auto flex flex-col gap-8">
        <header className="flex flex-col gap-2">
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-text">
            Your journey
          </h1>
          <p className="font-body text-sm text-text/70 leading-relaxed max-w-prose">
            What you have actually done, day by day. Nothing here is a target
            and nothing resets.
          </p>
          <Link
            href="/dashboard"
            className="touch-target inline-flex items-center self-start text-sm font-body text-primary underline underline-offset-4 transition-colors duration-200 hover:text-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
          >
            Back to dashboard
          </Link>
        </header>

        {/* Three windows, one choice: a radio group rather than three
            buttons, so arrow keys move between them and the current
            window is announced as the selected option. */}
        <fieldset className="border-0 p-0 m-0">
          <legend className="font-body text-xs uppercase tracking-wider text-text/60 mb-2">
            Window
          </legend>
          <div className="flex flex-wrap gap-2">
            {JOURNEY_WINDOWS.map((option) => (
              <div key={option}>
                <input
                  type="radio"
                  id={`${windowGroupId}-${option}`}
                  name={windowGroupId}
                  className="sr-only peer"
                  checked={windowDays === option}
                  onChange={() => setWindowDays(option)}
                />
                <label
                  htmlFor={`${windowGroupId}-${option}`}
                  className="touch-target inline-flex items-center px-4 py-2 rounded-lg cursor-pointer font-body text-sm border border-white/10 text-text/70 transition-colors duration-200 hover:text-text hover:border-white/20 peer-checked:border-primary peer-checked:bg-primary/15 peer-checked:text-primary peer-focus-visible:ring-2 peer-focus-visible:ring-primary peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-bg"
                >
                  {option} days
                </label>
              </div>
            ))}
          </div>
        </fieldset>

        <ApiStateView
          loading={journey.loading}
          error={journey.error}
          loadingText="Loading your journey..."
          onRetry={journey.refetch}
        >
          {data && neverPracticed && <JourneyEmpty />}

          {data && !neverPracticed && (
            <div className="flex flex-col gap-8">
              <section
                aria-labelledby="journey-totals-heading"
                className="card-surface px-4 py-5 sm:px-6 sm:py-6"
              >
                <h2
                  id="journey-totals-heading"
                  className="font-display text-base font-medium text-text mb-4"
                >
                  These {data.window_days} days
                </h2>
                <dl className="grid grid-cols-3 gap-4 mb-4">
                  <Stat value={data.totals.completed} label="Practices" />
                  <Stat
                    value={data.totals.days_practiced}
                    label="Days practiced"
                  />
                  <Stat value={data.totals.loops_closed} label="Loops closed" />
                </dl>
                <p className="font-body text-sm text-text/70 leading-relaxed max-w-prose">
                  {data.totals.first_practice_day && (
                    <>
                      Practicing since{" "}
                      {anchorDayLabel(
                        parseDayKey(data.totals.first_practice_day),
                      )}
                      .{" "}
                    </>
                  )}
                  {data.totals.first_loop_day
                    ? `First loop closed on ${anchorDayLabel(
                        parseDayKey(data.totals.first_loop_day),
                      )}.`
                    : "No loops closed yet. Closing one records what a practice changed, in your own words."}
                </p>
              </section>

              <JourneyChart days={data.days} />

              <JourneyBalance
                byPurpose={data.by_purpose}
                windowDays={data.window_days}
              />
            </div>
          )}
        </ApiStateView>
      </div>
    </main>
  );
}

export default function JourneyPage() {
  return (
    <ProtectedRoute>
      <JourneyBody />
    </ProtectedRoute>
  );
}
