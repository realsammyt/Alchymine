/**
 * Plan gate responses: the two ways the backend says "your plan cannot
 * pay for this".
 *
 * - **402 `plan_upgrade_required`** the plan does not include this
 *   surface at all. Waiting changes nothing; upgrading does.
 * - **429 `plan_allowance_reached`** the plan includes it but this
 *   month's spend allowance is gone. Waiting *does* fix it, at the
 *   first of next month, so that date is part of the answer.
 *
 * Neither is a fault, so both render as the yellow `role="status"` wait
 * state rather than the red `role="alert"` error state. Clients switch
 * on `detail.code`, never on the status code, because the same 429 also
 * carries the daily art cap and the per-minute rate limit.
 */

/** The two codes this module owns. */
export type PlanGateCode = "plan_upgrade_required" | "plan_allowance_reached";

export const PLAN_GATE_CODES: readonly PlanGateCode[] = [
  "plan_upgrade_required",
  "plan_allowance_reached",
];

/** Structured `detail` body shared by both refusals. */
export interface PlanGateDetail {
  code?: unknown;
  message?: unknown;
  retry_at?: unknown;
  meter?: unknown;
  plan?: unknown;
  upgrade_url?: unknown;
}

const DEFAULT_UPGRADE_URL = "/pricing";

const FALLBACK_MESSAGE: Record<PlanGateCode, string> = {
  plan_upgrade_required: "This feature is part of a paid plan.",
  plan_allowance_reached: "You've used this month's included usage.",
};

/**
 * A refusal the user can act on by upgrading.
 *
 * Carries the server's own wording rather than inventing a second
 * phrasing for the same state, plus the reset date when there is one.
 */
export class PlanGateError extends Error {
  readonly code: PlanGateCode;
  readonly retryAt: Date | null;
  readonly plan: string | null;
  readonly upgradeUrl: string;

  constructor(
    code: PlanGateCode,
    message: string,
    retryAt: Date | null = null,
    plan: string | null = null,
    upgradeUrl: string = DEFAULT_UPGRADE_URL,
  ) {
    super(message);
    this.name = "PlanGateError";
    this.code = code;
    this.retryAt = retryAt;
    this.plan = plan;
    this.upgradeUrl = upgradeUrl;
  }
}

export function isPlanGateCode(value: unknown): value is PlanGateCode {
  return (
    typeof value === "string" &&
    (PLAN_GATE_CODES as readonly string[]).includes(value)
  );
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

/**
 * Build a `PlanGateError` from a parsed `detail` object, or `null` when
 * the body is some other refusal (the daily art cap, a rate limit, the
 * global spend breaker) that this module does not own.
 */
export function planGateFromDetail(detail: unknown): PlanGateError | null {
  if (typeof detail !== "object" || detail === null) return null;
  const body = detail as PlanGateDetail;
  if (!isPlanGateCode(body.code)) return null;

  const parsed = asString(body.retry_at);
  const retryAt = parsed ? new Date(parsed) : null;

  return new PlanGateError(
    body.code,
    asString(body.message) ?? FALLBACK_MESSAGE[body.code],
    retryAt && !Number.isNaN(retryAt.getTime()) ? retryAt : null,
    asString(body.plan),
    asString(body.upgrade_url) ?? DEFAULT_UPGRADE_URL,
  );
}

/**
 * Read a fetch `Response` as a plan refusal.
 *
 * Returns `null` for any status other than 402/429, and for a 429 whose
 * body belongs to a different cap, so callers can fall through to their
 * existing handling.
 *
 * Consumes the body only when the status could plausibly be ours, since
 * a `Response` body can be read once.
 */
export async function readPlanGate(
  res: Response,
): Promise<PlanGateError | null> {
  if (res.status !== 402 && res.status !== 429) return null;

  try {
    const body = (await res.clone().json()) as { detail?: unknown };
    return planGateFromDetail(body?.detail);
  } catch {
    // A non-JSON body cannot be a plan refusal; those are always
    // structured. Let the caller's generic path have it.
    return null;
  }
}

/**
 * Render the reset moment for a person.
 *
 * Formatted in UTC on purpose: the allowance is a UTC calendar-month
 * meter, so the first of the month is the boundary that actually
 * governs, and a local rendering would show the previous day for
 * anyone west of Greenwich.
 */
export function formatAllowanceReset(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
