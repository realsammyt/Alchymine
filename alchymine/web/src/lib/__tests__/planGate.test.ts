/**
 * Tests for parsing the two plan-gate refusals.
 *
 * The frontend switches on `detail.code`, never on the status code,
 * because 429 is also the daily art cap and the per-minute chat limit.
 * These tests pin that: a 429 that is not ours must fall through so the
 * caller's existing handling still runs.
 */

import {
  formatAllowanceReset,
  isPlanGateCode,
  planGateFromDetail,
  PlanGateError,
  readPlanGate,
} from "../planGate";

function mockResponse(status: number, body?: unknown): Response {
  const res = {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      if (body === undefined) throw new Error("no body");
      return body;
    },
  };
  return {
    ...res,
    clone: () => res as unknown as Response,
  } as unknown as Response;
}

const UPGRADE_BODY = {
  detail: {
    code: "plan_upgrade_required",
    message: "Coaching chat is part of a paid plan. Upgrade to start a conversation.",
    retry_at: null,
    meter: null,
    plan: "free",
    upgrade_url: "/pricing",
  },
};

const ALLOWANCE_BODY = {
  detail: {
    code: "plan_allowance_reached",
    message: "You've used this month's included coaching. Upgrade to keep going.",
    retry_at: "2026-09-01T00:00:00+00:00",
    meter: "spend_micros_monthly",
    plan: "pro",
    upgrade_url: "/pricing",
  },
};

describe("isPlanGateCode", () => {
  it("accepts the two codes this module owns", () => {
    expect(isPlanGateCode("plan_upgrade_required")).toBe(true);
    expect(isPlanGateCode("plan_allowance_reached")).toBe(true);
  });

  it("rejects the codes other caps use", () => {
    expect(isPlanGateCode("daily_art_cap_reached")).toBe(false);
    expect(isPlanGateCode("llm_temporarily_unavailable")).toBe(false);
    expect(isPlanGateCode(undefined)).toBe(false);
  });
});

describe("planGateFromDetail", () => {
  it("reads an entitlement refusal", () => {
    const error = planGateFromDetail(UPGRADE_BODY.detail);

    expect(error).toBeInstanceOf(PlanGateError);
    expect(error!.code).toBe("plan_upgrade_required");
    expect(error!.plan).toBe("free");
    expect(error!.upgradeUrl).toBe("/pricing");
    // Waiting does not fix an entitlement refusal, so there is no date.
    expect(error!.retryAt).toBeNull();
  });

  it("reads an allowance refusal with its reset moment", () => {
    const error = planGateFromDetail(ALLOWANCE_BODY.detail);

    expect(error!.code).toBe("plan_allowance_reached");
    expect(error!.retryAt).toEqual(new Date("2026-09-01T00:00:00+00:00"));
    expect(error!.plan).toBe("pro");
  });

  it("keeps the server's wording rather than inventing its own", () => {
    expect(planGateFromDetail(ALLOWANCE_BODY.detail)!.message).toBe(
      ALLOWANCE_BODY.detail.message,
    );
  });

  it("falls back to generic wording when the message is missing", () => {
    const error = planGateFromDetail({ code: "plan_upgrade_required" });

    expect(error!.message).toBeTruthy();
  });

  it("ignores an unparseable retry_at instead of rendering Invalid Date", () => {
    const error = planGateFromDetail({
      code: "plan_allowance_reached",
      retry_at: "not-a-date",
    });

    expect(error!.retryAt).toBeNull();
  });

  it("returns null for a refusal it does not own", () => {
    expect(planGateFromDetail({ code: "daily_art_cap_reached" })).toBeNull();
    expect(planGateFromDetail(null)).toBeNull();
    expect(planGateFromDetail("nope")).toBeNull();
  });
});

describe("readPlanGate", () => {
  it("reads a 402", async () => {
    const error = await readPlanGate(mockResponse(402, UPGRADE_BODY));

    expect(error!.code).toBe("plan_upgrade_required");
  });

  it("reads a 429", async () => {
    const error = await readPlanGate(mockResponse(429, ALLOWANCE_BODY));

    expect(error!.code).toBe("plan_allowance_reached");
  });

  it("passes a 429 from a different cap through untouched", async () => {
    const body = { detail: { code: "daily_art_cap_reached" } };

    expect(await readPlanGate(mockResponse(429, body))).toBeNull();
  });

  it("ignores statuses that are not plan refusals", async () => {
    expect(await readPlanGate(mockResponse(503, ALLOWANCE_BODY))).toBeNull();
    expect(await readPlanGate(mockResponse(400, ALLOWANCE_BODY))).toBeNull();
  });

  it("survives a non-JSON body", async () => {
    expect(await readPlanGate(mockResponse(429))).toBeNull();
  });

  it("leaves the original body readable for the caller", async () => {
    // The generic error path reads the body after this returns null, and
    // a Response body can only be consumed once.
    const res = mockResponse(429, { detail: { code: "daily_art_cap_reached" } });

    expect(await readPlanGate(res)).toBeNull();
    await expect(res.json()).resolves.toBeDefined();
  });
});

describe("formatAllowanceReset", () => {
  it("renders the reset date for a person", () => {
    expect(formatAllowanceReset(new Date("2026-09-01T00:00:00Z"))).toBe(
      "September 1",
    );
  });

  it("uses UTC so the month boundary does not slip a day", () => {
    // The allowance is a UTC calendar-month meter. Rendered locally,
    // this instant is August 31 for everyone west of Greenwich.
    expect(formatAllowanceReset(new Date("2026-09-01T00:00:00Z"))).not.toBe(
      "August 31",
    );
  });
});
