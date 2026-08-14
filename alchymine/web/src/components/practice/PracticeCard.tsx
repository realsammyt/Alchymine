"use client";

import { useId, type ReactNode } from "react";
import { useFocusOnEnter } from "@/hooks/useFocusOnEnter";
import type { ProtocolItem } from "@/lib/api";

/**
 * What the card is doing right now, from the user's point of view.
 *
 * There is no `saving`. Completion is optimistic, so the card goes
 * straight from `idle` to the outcome and the write happens underneath.
 * The in-flight window is carried by the separate `pending` prop, which
 * is what `aria-busy` reports.
 */
export type PracticeCardState = "idle" | "completed" | "skipped";

interface PracticeCardProps {
  item: ProtocolItem;
  /** This slot's prompt. The same practice reads differently at 7am and 10pm. */
  prompt: string;
  state: PracticeCardState;
  /** True while the write behind an optimistic state is still in flight. */
  pending?: boolean;
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
  pending = false,
  onComplete,
  onSkip,
  error = null,
  children,
}: PracticeCardProps) {
  const titleId = useId();
  const settled = state === "completed" || state === "skipped";

  // Two focus targets, one per direction. Completing moves focus onto
  // the outcome; a failed write moves it back to the control the user
  // was standing on, so a rollback does not silently strand them.
  const statusRef = useFocusOnEnter<HTMLParagraphElement>(settled);
  const completeRef = useFocusOnEnter<HTMLButtonElement>(!settled);

  const settledText =
    state === "completed"
      ? "Done today."
      : state === "skipped"
        ? "Not today. That's fine."
        : "";

  return (
    <article
      aria-labelledby={titleId}
      className="card-surface px-5 py-4 sm:px-6 sm:py-5 flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 id={titleId} className="font-display text-base font-medium text-text">
          {item.title}
        </h3>
        <span className="text-[11px] font-body px-2 py-0.5 rounded-full bg-white/[0.06] text-text/60">
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
      {/* The reason carries content, not ornament, so it takes a
          readable weight rather than the repo's decorative /35. */}
      <p className="text-xs font-body text-text/60 italic">{item.reason}</p>

      {!settled && (
        <div className="flex flex-wrap gap-2">
          <button
            ref={completeRef}
            type="button"
            onClick={onComplete}
            className="touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 hover:bg-primary/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Done
          </button>
          <button
            type="button"
            onClick={onSkip}
            className="touch-target px-4 py-2 rounded-lg text-sm font-body text-text/60 border border-white/10 transition-colors duration-200 hover:text-text/80 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Not today
          </button>
        </div>
      )}

      {/* One live region for both the outcome and any failure, primed
          empty on mount so the first thing written to it is announced.
          Polite rather than an alert: neither a completion nor a failed
          save is worth interrupting a screen reader mid-word.

          It is also the focus target for a completion, which is why it
          carries tabIndex={-1}. `aria-busy` marks the window where the
          optimistic text is showing but the write has not landed yet. */}
      <p
        ref={statusRef}
        role="status"
        aria-live="polite"
        aria-busy={pending}
        tabIndex={-1}
        className={`font-body text-text/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded ${
          settled && !error ? "text-sm" : "text-xs"
        }`}
      >
        {error ?? settledText}
      </p>

      {children}
    </article>
  );
}
