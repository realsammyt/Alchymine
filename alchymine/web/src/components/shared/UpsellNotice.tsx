"use client";

/**
 * The banner a user sees when their plan cannot pay for what they asked
 * for.
 *
 * `role="status"` and yellow, never `role="alert"` and red: nothing is
 * broken, and dressing a sales moment as a fault trains people to
 * ignore real faults. `status` is a polite live region, so a screen
 * reader announces it after the current utterance instead of
 * interrupting.
 *
 * Focus is deliberately not moved here. The banner appears in response
 * to something the user just did, the live region announces it, and the
 * upgrade link is reachable in DOM order. Pulling focus to a passive
 * notice would drop the user out of the control they were using.
 */

import Link from "next/link";

import { formatAllowanceReset, PlanGateError } from "@/lib/planGate";

interface Props {
  /** The refusal to render. */
  error: PlanGateError;
  /** Extra classes for page-specific spacing. */
  className?: string;
}

export default function UpsellNotice({ error, className = "" }: Props) {
  const resetsOn = error.retryAt ? formatAllowanceReset(error.retryAt) : null;

  return (
    <div
      role="status"
      className={`rounded-lg border border-yellow-700/30 bg-yellow-900/20 px-4 py-3 text-sm font-body text-yellow-200 ${className}`}
    >
      <p>{error.message}</p>
      {resetsOn && (
        <p className="mt-1 text-yellow-200/70">Resets on {resetsOn}.</p>
      )}
      <Link
        href={error.upgradeUrl}
        className="mt-2 inline-block font-medium text-yellow-100 underline underline-offset-2 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-yellow-300 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      >
        See plans
      </Link>
    </div>
  );
}
