/**
 * `request()` splits plan refusals out of its generic error path.
 *
 * Two reasons it has to. The envelope's `detail` is an object, and the
 * generic path does `body.detail || \`HTTP ${status}\``, which hands an
 * object to `new ApiError(...)` and renders "[object Object]" at the
 * user. And a plan refusal is not a fault, so it carries its own type
 * and gets a yellow upsell rather than a red error.
 *
 * `createReport` is the caller that matters here: it is the report
 * chokepoint, and it passes `allow202` so its success path is a 202.
 */

import { ApiError, createReport, getMe, IntakePayload } from "@/lib/api";
import { PlanGateError } from "@/lib/planGate";

const INTAKE: IntakePayload = {
  full_name: "Maria Elena Vasquez",
  birth_date: "1992-03-15",
  intention: "family",
  assessment_responses: {},
};

const UPGRADE_DETAIL = {
  code: "plan_upgrade_required",
  message: "Full reports are part of a paid plan. Upgrade to generate yours.",
  retry_at: null,
  meter: null,
  plan: "free",
  upgrade_url: "/pricing",
};

const ALLOWANCE_DETAIL = {
  code: "plan_allowance_reached",
  message: "You've used this month's included reports. Upgrade to keep going.",
  retry_at: "2026-09-01T00:00:00+00:00",
  meter: "spend_micros_monthly",
  plan: "pro",
  upgrade_url: "/pricing",
};

function mockResponse(status: number, body: unknown): Response {
  // `clone` is load-bearing: readPlanGate clones so the generic path
  // still has an unconsumed body. Without it every refusal would fall
  // through to ApiError and these tests would pass for the wrong reason.
  const res = {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
  return {
    ...res,
    clone: () => res as unknown as Response,
  } as unknown as Response;
}

const realFetch = global.fetch;

afterEach(() => {
  global.fetch = realFetch;
  jest.restoreAllMocks();
});

describe("request() plan refusals", () => {
  it("throws PlanGateError on a 402 rather than ApiError", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(402, { detail: UPGRADE_DETAIL }));

    const error = await createReport(INTAKE).catch((e) => e);

    expect(error).toBeInstanceOf(PlanGateError);
    expect(error.code).toBe("plan_upgrade_required");
    expect(error.upgradeUrl).toBe("/pricing");
    expect(error.plan).toBe("free");
  });

  it("throws PlanGateError on a plan 429, with the reset moment", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(429, { detail: ALLOWANCE_DETAIL }));

    const error = await createReport(INTAKE).catch((e) => e);

    expect(error).toBeInstanceOf(PlanGateError);
    expect(error.code).toBe("plan_allowance_reached");
    expect(error.retryAt).toEqual(new Date("2026-09-01T00:00:00+00:00"));
  });

  it("carries the server's wording, not a stringified object", async () => {
    // The regression this guards: `body.detail` is an object here, so
    // the generic path would produce "[object Object]".
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(402, { detail: UPGRADE_DETAIL }));

    const error = await createReport(INTAKE).catch((e) => e);

    expect(error.message).toBe(UPGRADE_DETAIL.message);
    expect(error.message).not.toContain("object Object");
  });

  it("leaves a non-plan failure as an ApiError", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(422, { detail: "birth_date is required" }));

    const error = await createReport(INTAKE).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).not.toBeInstanceOf(PlanGateError);
    expect(error.message).toBe("birth_date is required");
  });

  it("does not mistake a 429 from another cap for a plan refusal", async () => {
    // The report route also carries a per-user guardrail that 429s with
    // a plain string detail.
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(429, { detail: "Too many reports this hour" }));

    const error = await createReport(INTAKE).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).not.toBeInstanceOf(PlanGateError);
    expect(error.message).toBe("Too many reports this hour");
  });

  it("applies to every caller of request(), not just reports", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(402, { detail: UPGRADE_DETAIL }));

    await expect(getMe()).rejects.toBeInstanceOf(PlanGateError);
  });

  it("still returns the body on success", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(mockResponse(202, { id: "rep-1", status: "pending" }));

    await expect(createReport(INTAKE)).resolves.toMatchObject({ id: "rep-1" });
  });
});
