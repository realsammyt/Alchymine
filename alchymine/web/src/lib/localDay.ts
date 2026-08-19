/**
 * The user's local calendar day, and the labels the rhythm display
 * builds from it.
 *
 * Every practice route takes the day as `YYYY-MM-DD` in the user's own
 * timezone, because only the client knows what that is. The server runs
 * in UTC, so deriving the day there would file an evening practice in
 * Auckland under tomorrow and a late-night one in Los Angeles under
 * yesterday, every single time.
 */

/**
 * Format a `Date` as `YYYY-MM-DD` in the *local* timezone.
 *
 * Deliberately not `toISOString().slice(0, 10)`, which is UTC and is the
 * bug this module exists to avoid.
 */
export function localDayKey(when: Date = new Date()): string {
  const year = when.getFullYear();
  const month = String(when.getMonth() + 1).padStart(2, "0");
  const day = String(when.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Parse a `YYYY-MM-DD` key back into a local-midnight `Date`. */
export function parseDayKey(dayKey: string): Date {
  const [year, month, day] = dayKey.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** The day *offset* days before `dayKey`, as a local-midnight `Date`. */
export function dayKeyMinus(dayKey: string, offset: number): Date {
  const base = parseDayKey(dayKey);
  base.setDate(base.getDate() - offset);
  return base;
}

/**
 * A human day label such as `Tuesday 12 August`, for the rhythm markers'
 * accessible names. Written out in full rather than abbreviated: a
 * screen reader saying "Tue 12 Aug" reads worse than the whole thing.
 */
export function dayLabel(when: Date): string {
  return when.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

/**
 * A compact day label such as `12 Aug`, for chart axes where the full
 * form will not fit. Sighted readers get this; screen readers get
 * `dayLabel` from the per-day description, so nothing is lost to the
 * abbreviation.
 */
export function shortDayLabel(when: Date): string {
  return when.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

/**
 * A day label carrying its year, such as `4 March 2026`.
 *
 * Used for the anchors that reach back past the visible window, where
 * the year is the part that stops "4 March" from being ambiguous.
 */
export function anchorDayLabel(when: Date): string {
  return when.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
