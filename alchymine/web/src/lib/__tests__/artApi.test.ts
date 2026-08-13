/**
 * Tests for the cost-state handling in the generative art API wrappers.
 *
 * A spent daily cap (429) and a tripped global spend breaker (503) are
 * both "come back later" states, not faults. They must arrive as a typed
 * error carrying the server's wording and the reset time, so callers can
 * render a wait state instead of printing a status code at the user.
 */

import {
  ArtUnavailableError,
  generateArt,
  generateBrandLogo,
} from "../artApi";

function mockResponse(status: number, body?: unknown): Response {
  // `clone` is not optional here. readPlanGate clones before reading, so
  // that the generic path still has a body to consume, and a mock
  // without it would make every plan refusal fall through to the
  // fallback wording while the tests still went green.
  const res = {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      if (body === undefined) throw new Error("no body");
      return body;
    },
    text: async () => JSON.stringify(body ?? ""),
  };
  return {
    ...res,
    clone: () => res as unknown as Response,
  } as unknown as Response;
}

const CAP_BODY = {
  detail: {
    code: "daily_art_cap_reached",
    message:
      "That's all of today's image generations. Your next one unlocks at midnight UTC.",
    retry_at: "2099-01-01T00:00:00+00:00",
  },
};

const BREAKER_BODY = {
  detail: {
    code: "llm_temporarily_unavailable",
    message:
      "This feature is taking a short break while we catch up on demand. Please try again later.",
    retry_at: "2099-01-01T00:00:00+00:00",
  },
};

describe("generateArt cost states", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("throws a typed error when the daily cap is spent", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(429, CAP_BODY));

    await expect(generateArt()).rejects.toBeInstanceOf(ArtUnavailableError);
  });

  it("carries the cap code and reset time", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(429, CAP_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error).toBeInstanceOf(ArtUnavailableError);
    expect(error.code).toBe("daily_art_cap_reached");
    expect(error.retryAt?.toISOString()).toBe("2099-01-01T00:00:00.000Z");
  });

  it("uses the server's wording so the user sees one voice", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(429, CAP_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error.message).toBe(CAP_BODY.detail.message);
    expect(error.message).not.toContain("429");
  });

  it("treats a tripped spend breaker as the same kind of wait state", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(503, BREAKER_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error).toBeInstanceOf(ArtUnavailableError);
    expect(error.code).toBe("llm_temporarily_unavailable");
  });

  it("still produces a usable wait state when the body is not JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(503));

    const error = await generateArt().catch((e) => e);

    expect(error).toBeInstanceOf(ArtUnavailableError);
    expect(error.message.length).toBeGreaterThan(0);
    expect(error.retryAt).toBeNull();
  });

  it("leaves 204 and success paths alone", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(204));
    await expect(generateArt()).resolves.toBeNull();

    global.fetch = jest.fn().mockResolvedValue(
      mockResponse(201, { image_id: "img-1", url: "/api/v1/art/img-1", prompt: "p" }),
    );
    await expect(generateArt()).resolves.toEqual({
      image_id: "img-1",
      url: "/api/v1/art/img-1",
      prompt: "p",
    });
  });

  it("keeps other failures as plain errors", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(400, { detail: "bad preset" }));

    const error = await generateArt().catch((e) => e);

    expect(error).not.toBeInstanceOf(ArtUnavailableError);
    expect(error.message).toContain("400");
  });
});

describe("generateBrandLogo cost states", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("surfaces a tripped spend breaker as a wait state", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(503, BREAKER_BODY));

    await expect(generateBrandLogo()).rejects.toBeInstanceOf(
      ArtUnavailableError,
    );
  });
});

describe("plan refusals in the art wrappers", () => {
  const UPGRADE_BODY = {
    detail: {
      code: "plan_upgrade_required",
      message: "Image generation is part of a paid plan. Upgrade to make yours.",
      retry_at: null,
      meter: null,
      plan: "free",
      upgrade_url: "/pricing",
    },
  };

  const ALLOWANCE_BODY = {
    detail: {
      code: "plan_allowance_reached",
      message: "You've used this month's included images. Upgrade to keep going.",
      retry_at: "2026-09-01T00:00:00+00:00",
      meter: "spend_micros_monthly",
      plan: "pro",
      upgrade_url: "/pricing",
    },
  };

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("turns a 402 into an upsell carrying somewhere to go", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(402, UPGRADE_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error).toBeInstanceOf(ArtUnavailableError);
    expect(error.code).toBe("plan_upgrade_required");
    expect(error.upgradeUrl).toBe("/pricing");
    expect(error.message).toBe(UPGRADE_BODY.detail.message);
    // Waiting does not fix an entitlement refusal.
    expect(error.retryAt).toBeNull();
  });

  it("turns a plan 429 into an upsell with the reset moment", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(429, ALLOWANCE_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error.code).toBe("plan_allowance_reached");
    expect(error.upgradeUrl).toBe("/pricing");
    expect(error.retryAt).toEqual(new Date("2026-09-01T00:00:00+00:00"));
  });

  it("leaves the daily cap without an upgrade pitch", async () => {
    // Same 429 status, different cause. The cap clears at midnight on
    // its own, so offering an upgrade for it would sell a fix for
    // something that is already fixing itself.
    global.fetch = jest.fn().mockResolvedValue(mockResponse(429, CAP_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error.code).toBe("daily_art_cap_reached");
    expect(error.upgradeUrl).toBeNull();
  });

  it("leaves the global breaker without one either", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(503, BREAKER_BODY));

    const error = await generateArt().catch((e) => e);

    expect(error.code).toBe("llm_temporarily_unavailable");
    expect(error.upgradeUrl).toBeNull();
  });

  it("refuses the logo route the same way", async () => {
    global.fetch = jest.fn().mockResolvedValue(mockResponse(402, UPGRADE_BODY));

    const error = await generateBrandLogo().catch((e) => e);

    expect(error).toBeInstanceOf(ArtUnavailableError);
    expect(error.code).toBe("plan_upgrade_required");
    expect(error.upgradeUrl).toBe("/pricing");
  });
});
