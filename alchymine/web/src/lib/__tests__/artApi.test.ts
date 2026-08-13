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
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => {
      if (body === undefined) throw new Error("no body");
      return body;
    },
    text: async () => JSON.stringify(body ?? ""),
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
