"use client";

import { purposeLabel } from "@/components/practice/PracticeCard";
import { dayLabel, parseDayKey, shortDayLabel } from "@/lib/localDay";
import type { JourneyDay } from "@/lib/api";

/**
 * The band the recorded shift is drawn in.
 *
 * Fixed to the range the self-report accepts rather than derived from
 * the data. A window holding nothing but +1s would otherwise rescale
 * until every dot sat at the top, and the user would read a steady week
 * as their best one.
 */
const SHIFT_MIN = -2;
const SHIFT_MAX = 2;

/** Column geometry. Below this width a bar stops being readable. */
const COLUMN_MIN_PX = 10;
const COLUMN_GAP_PX = 3;

/** The shortest a non-zero bar may be drawn, so a single practice shows. */
const MIN_BAR_PERCENT = 8;

interface JourneyChartProps {
  days: JourneyDay[];
}

/**
 * One day's full description, for the screen reader and for tests.
 *
 * Everything the two drawn rows encode is in this sentence, which is
 * the point: the bars and dots are decorative, and this is the data.
 */
export function describeJourneyDay(day: JourneyDay): string {
  const label = dayLabel(parseDayKey(day.day_key));
  if (day.completed === 0 && day.loops === 0) {
    return `${label}: nothing logged.`;
  }

  const parts: string[] = [];
  if (day.completed > 0) {
    const noun = day.completed === 1 ? "practice" : "practices";
    const capacities = day.purposes.map(purposeLabel).join(", ");
    parts.push(
      capacities
        ? `${day.completed} ${noun} completed (${capacities})`
        : `${day.completed} ${noun} completed`,
    );
  }
  if (day.loops > 0) {
    const noun = day.loops === 1 ? "loop" : "loops";
    parts.push(`${day.loops} ${noun} closed`);
  }
  if (day.average_shift !== null) {
    parts.push(`recorded shift ${formatShift(day.average_shift)}`);
  }
  return `${label}: ${parts.join(", ")}.`;
}

/** A signed shift, so `+1` reads as a direction rather than a count. */
export function formatShift(value: number): string {
  const rounded = Math.round(value * 100) / 100;
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

/** Where a shift sits in the band, as a percentage from the top. */
function shiftOffsetPercent(value: number): number {
  const clamped = Math.min(SHIFT_MAX, Math.max(SHIFT_MIN, value));
  return ((SHIFT_MAX - clamped) / (SHIFT_MAX - SHIFT_MIN)) * 100;
}

/**
 * The journey chart: practices completed per day, and the shift the
 * user recorded when they closed a loop on that day.
 *
 * Two rows over one axis rather than two charts, because the second row
 * only means anything against the first: a dot says what the user made
 * of the practice the bar above it stands for.
 *
 * Nothing here animates. A chart that grew into place on every window
 * change would be motion in service of nothing, and the honest way to
 * respect a reduced-motion preference is to not need one.
 *
 * The drawn rows are hidden from assistive technology and each column
 * carries its own sentence instead. Marking up two positional encodings
 * as a chart would describe the drawing; the sentence describes the
 * day. The same reasoning as the seven-day rhythm strip, which puts the
 * text inside the list item rather than in a label on it, because
 * browse-mode readers commonly read a list item's contents and these
 * items are otherwise empty.
 */
export default function JourneyChart({ days }: JourneyChartProps) {
  const maxCompleted = days.reduce(
    (most, day) => Math.max(most, day.completed),
    0,
  );
  const trackWidth =
    days.length * COLUMN_MIN_PX + Math.max(days.length - 1, 0) * COLUMN_GAP_PX;

  const first = days[0];
  const last = days[days.length - 1];
  const middle = days[Math.floor(days.length / 2)];

  return (
    <section
      aria-labelledby="journey-chart-heading"
      className="card-surface px-4 py-5 sm:px-6 sm:py-6"
    >
      <h2
        id="journey-chart-heading"
        className="font-display text-base font-medium text-text mb-1"
      >
        Practice and integration
      </h2>
      <p className="font-body text-sm text-text/70 mb-5 max-w-prose">
        Each column is a day. The bar is how many practices you completed. The
        dot is the shift you recorded when you closed a loop, from {SHIFT_MIN}{" "}
        at the bottom to +{SHIFT_MAX} at the top, against the line at 0.
      </p>

      {/* The window can be ninety columns wide. It scrolls inside this
          box so the page itself never does. */}
      <div className="overflow-x-auto -mx-1 px-1 pb-1">
        <div style={{ minWidth: `${trackWidth}px` }}>
          <ul
            className="flex items-stretch list-none p-0 m-0"
            style={{ gap: `${COLUMN_GAP_PX}px` }}
          >
            {days.map((day) => (
              <li
                key={day.day_key}
                className="flex-1 flex flex-col"
                style={{ minWidth: `${COLUMN_MIN_PX}px` }}
              >
                <span className="sr-only">{describeJourneyDay(day)}</span>

                {/* Completions. A day with nothing on it keeps a dashed
                    stub at the baseline rather than vanishing, so the
                    gap is visible as a gap. Fill and border style both
                    differ, so the two states do not rely on colour. */}
                <span aria-hidden="true" className="flex h-16 items-end w-full">
                  <span
                    className={
                      day.completed > 0
                        ? "block w-full rounded-sm border border-primary bg-primary/70"
                        : "block w-full h-[3px] rounded-sm border-t-2 border-dashed border-white/40"
                    }
                    style={
                      day.completed > 0
                        ? {
                            height: `${Math.max(
                              MIN_BAR_PERCENT,
                              (day.completed / Math.max(maxCompleted, 1)) * 100,
                            )}%`,
                          }
                        : undefined
                    }
                  />
                </span>

                {/* Recorded shift, positioned in a fixed band. Position
                    carries the value; the dot is one colour throughout. */}
                <span
                  aria-hidden="true"
                  className="relative block h-10 mt-2 border-t border-white/[0.08]"
                >
                  {/* The dot's position is read against this line, so
                      it is a graphical object that has to carry 3:1
                      rather than a hairline that can sit at 1.9:1. */}
                  <span className="absolute inset-x-0 top-1/2 h-px bg-white/40" />
                  {day.average_shift !== null && (
                    <span
                      className="absolute w-[7px] h-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent ring-1 ring-accent-light/60"
                      style={{
                        left: "50%",
                        top: `${shiftOffsetPercent(day.average_shift)}%`,
                      }}
                    />
                  )}
                </span>
              </li>
            ))}
          </ul>

          {/* Three anchors rather than a label per column: at ninety days
              a column is ten pixels wide and no date fits in one. The
              exact day of every column is in its description above. */}
          <div
            aria-hidden="true"
            className="flex justify-between mt-2 font-mono text-[11px] text-text/60"
          >
            <span>{shortDayLabel(parseDayKey(first.day_key))}</span>
            {days.length > 2 && (
              <span>{shortDayLabel(parseDayKey(middle.day_key))}</span>
            )}
            <span>{shortDayLabel(parseDayKey(last.day_key))}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
