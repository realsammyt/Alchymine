"use client";

import { dayKeyMinus, dayLabel } from "@/lib/localDay";

/**
 * Words and images this surface does not use, exported so the tests on
 * every practice component can assert against one list rather than
 * drifting copies of it.
 *
 * The point is not squeamishness about the word "streak". It is that a
 * counter which resets to zero converts a missed Tuesday into a loss,
 * and a product that helps somebody build a practice cannot also punish
 * them for the days they did not. A record shows what happened. A
 * scoreboard tells them what they failed to keep.
 */
export const LOSS_AVERSION_BANNED = [
  "streak",
  "don't break",
  "dont break",
  "you're about to lose",
  "youre about to lose",
  "about to lose",
  "keep it going",
  "keep the chain",
  "resets in",
  "back to zero",
  "starting over",
  "you lost",
  "missed day",
  "🔥",
  "flame",
  "on fire",
] as const;

interface PracticeRhythmProps {
  /** The user's local day the window ends on, `YYYY-MM-DD`. */
  dayKey: string;
  /** Oldest first: index 0 is six days before `dayKey`, index 6 is it. */
  last7: boolean[];
  daysPracticed: number;
}

/**
 * The seven-day record.
 *
 * Seven markers, one per day, filled where something was completed. The
 * caption is the accessible summary; the markers themselves are
 * decorative and each `<li>` carries the day and its state as its
 * accessible name, so a screen reader hears "Tuesday 12 August:
 * practiced" rather than seven unlabelled bullets.
 */
export default function PracticeRhythm({
  dayKey,
  last7,
  daysPracticed,
}: PracticeRhythmProps) {
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = dayKeyMinus(dayKey, 6 - index);
    return {
      label: dayLabel(date),
      practiced: last7[index] === true,
    };
  });

  const caption =
    daysPracticed > 0
      ? `Practiced ${daysPracticed} of the last 7 days.`
      : "No practice logged in the last 7 days. Start wherever you are.";

  return (
    <section
      aria-labelledby="practice-rhythm-heading"
      className="card-surface px-5 py-4 sm:px-6 sm:py-5"
    >
      <h2
        id="practice-rhythm-heading"
        className="font-display text-sm font-medium text-text/70 mb-3"
      >
        Your last seven days
      </h2>
      <ul className="flex items-center gap-2 sm:gap-3 mb-3 list-none p-0">
        {days.map((day) => (
          <li
            key={day.label}
            aria-label={`${day.label}: ${
              day.practiced ? "practiced" : "no practice logged"
            }`}
            className="flex-1 min-w-0"
          >
            <span
              aria-hidden="true"
              className={`block h-8 rounded-md border ${
                day.practiced
                  ? "bg-primary/30 border-primary/40"
                  : "bg-white/[0.03] border-white/10"
              }`}
            />
          </li>
        ))}
      </ul>
      <p className="text-sm font-body text-text/50">{caption}</p>
    </section>
  );
}
