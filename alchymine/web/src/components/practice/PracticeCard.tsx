"use client";

import type { ReactNode } from "react";
import type { ProtocolItem } from "@/lib/api";

/** What the card is doing right now, from the user's point of view. */
export type PracticeCardState = "idle" | "saving" | "completed" | "skipped";

interface PracticeCardProps {
  item: ProtocolItem;
  /** This slot's prompt. The same practice reads differently at 7am and 10pm. */
  prompt: string;
  state: PracticeCardState;
  onComplete: () => void;
  onSkip: () => void;
  error?: string | null;
  /** The self-check and integration follow-ups, once there are any. */
  children?: ReactNode;
}

/**
 * `self-knowledge` reads badly on a chip; `Self-knowledge` reads fine.
 * The hyphen stays because the purpose key is the hyphenated form and
 * the chip should be recognisable as the same thing.
 */
export function purposeLabel(purpose: string): string {
  return purpose.charAt(0).toUpperCase() + purpose.slice(1);
}

export default function PracticeCard({
  item,
  prompt,
  state,
  onComplete,
  onSkip,
  error = null,
  children,
}: PracticeCardProps) {
  const busy = state === "saving";
  const settled = state === "completed" || state === "skipped";

  return (
    <article
      role="group"
      aria-label={item.title}
      className="card-surface px-5 py-4 sm:px-6 sm:py-5 flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="font-display text-base font-medium text-text">
          {item.title}
        </h3>
        <span className="text-[11px] font-body px-2 py-0.5 rounded-full bg-white/[0.06] text-text/50">
          {item.duration_minutes} min
        </span>
        <span className="text-[11px] font-body px-2 py-0.5 rounded-full bg-primary/10 text-primary">
          {purposeLabel(item.purpose)}
        </span>
      </div>

      <p className="text-sm font-body text-text/60 leading-relaxed">
        {item.summary}
      </p>
      <p className="text-sm font-body text-text/80 leading-relaxed">{prompt}</p>
      <p className="text-xs font-body text-text/35 italic">{item.reason}</p>

      {settled ? (
        <p className="text-sm font-body text-text/50">
          {state === "completed" ? "Done today." : "Not today. That's fine."}
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onComplete}
            disabled={busy}
            aria-busy={busy}
            className="touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 hover:bg-primary/25 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {/* The label does not change while saving. A control that
                renames itself under the pointer is harder to use, and it
                breaks the accessible name a screen-reader user just
                heard. `aria-busy` carries the state instead. */}
            Done
          </button>
          <button
            type="button"
            onClick={onSkip}
            disabled={busy}
            className="touch-target px-4 py-2 rounded-lg text-sm font-body text-text/50 border border-white/10 transition-colors duration-200 hover:text-text/70 hover:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Not today
          </button>
        </div>
      )}

      {/* Polite, not an alert: a failed save is worth telling the user
          about, and is not worth interrupting a screen reader mid-word. */}
      <p role="status" aria-live="polite" className="text-xs font-body text-text/50">
        {error}
      </p>

      {children}
    </article>
  );
}
