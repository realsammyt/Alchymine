"use client";

import { purposeLabel } from "@/components/practice/PracticeCard";

/** The five capacities, in the fixed order the engine returns them. */
const PURPOSES = [
  "self-knowledge",
  "steadiness",
  "stewardship",
  "expression",
  "reframing",
] as const;

interface JourneyBalanceProps {
  byPurpose: Record<string, number>;
  windowDays: number;
}

/**
 * Where the window's practice went, by capacity.
 *
 * Five rows in fixed order, always all five, so a capacity the user has
 * not touched reads as a zero they can see rather than a row that is
 * not there. Every bar carries its own number next to it, so the
 * drawing is a second reading of the figure rather than the only one.
 */
export default function JourneyBalance({
  byPurpose,
  windowDays,
}: JourneyBalanceProps) {
  const counts = PURPOSES.map((purpose) => ({
    purpose,
    count: byPurpose[purpose] ?? 0,
  }));
  const most = counts.reduce((top, row) => Math.max(top, row.count), 0);
  const total = counts.reduce((sum, row) => sum + row.count, 0);

  return (
    <section
      aria-labelledby="journey-balance-heading"
      className="card-surface px-4 py-5 sm:px-6 sm:py-6"
    >
      <h2
        id="journey-balance-heading"
        className="font-display text-base font-medium text-text mb-1"
      >
        Where the practice went
      </h2>
      <p className="font-body text-sm text-text/70 mb-5 max-w-prose">
        {total > 0
          ? `Completions by capacity across these ${windowDays} days. Balance is not the goal; this is only what happened.`
          : `Nothing completed in these ${windowDays} days. The five capacities are here for when there is.`}
      </p>

      <ul className="list-none p-0 m-0 flex flex-col gap-3">
        {counts.map(({ purpose, count }) => (
          <li key={purpose} className="flex items-center gap-3">
            <span className="font-body text-sm text-text/80 w-28 shrink-0">
              {purposeLabel(purpose)}
            </span>
            <span
              aria-hidden="true"
              className="flex-1 h-2 rounded-full bg-white/[0.06] overflow-hidden"
            >
              <span
                className="block h-full rounded-full bg-primary/70"
                style={{ width: `${most > 0 ? (count / most) * 100 : 0}%` }}
              />
            </span>
            <span className="font-mono text-sm text-text/70 w-8 shrink-0 text-right">
              {count}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
