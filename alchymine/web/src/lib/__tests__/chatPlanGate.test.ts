/**
 * Chat transport: plan refusals arrive before the stream opens.
 *
 * The gate runs as a route dependency, so a refused turn is a real 402
 * or 429 with a JSON body rather than an `event: error` frame inside a
 * 200 event-stream. That distinction is the whole reason the check sits
 * in the endpoint: once the stream is open there is no status left to
 * set, and a quota state buried in a frame reads as success to
 * everything above the SSE parser.
 */

import { ChatError, ChatUpsellError, streamChat } from "../chat";

function jsonResponse(status: number, body: unknown): Response {
  const res = {
    status,
    ok: false,
    body: null,
    json: async () => body,
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

async function drain(): Promise<string[]> {
  const chunks: string[] = [];
  for await (const chunk of streamChat({ message: "hi", system_key: null })) {
    chunks.push(chunk);
  }
  return chunks;
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe("streamChat plan refusals", () => {
  it("throws a typed upsell on 402", async () => {
    global.fetch = jest.fn().mockResolvedValue(jsonResponse(402, UPGRADE_BODY));

    const error = (await drain().catch((e) => e)) as ChatUpsellError;

    expect(error).toBeInstanceOf(ChatUpsellError);
    expect(error.gate.code).toBe("plan_upgrade_required");
    expect(error.status).toBe(402);
  });

  it("throws a typed upsell on 429 with the reset date", async () => {
    global.fetch = jest.fn().mockResolvedValue(jsonResponse(429, ALLOWANCE_BODY));

    const error = (await drain().catch((e) => e)) as ChatUpsellError;

    expect(error).toBeInstanceOf(ChatUpsellError);
    expect(error.gate.code).toBe("plan_allowance_reached");
    expect(error.gate.retryAt).toEqual(new Date("2026-09-01T00:00:00+00:00"));
    expect(error.gate.upgradeUrl).toBe("/pricing");
  });

  it("yields nothing before refusing", async () => {
    // No partial reply should reach the UI: the refusal happens before
    // the model is called at all.
    global.fetch = jest.fn().mockResolvedValue(jsonResponse(402, UPGRADE_BODY));

    const chunks: string[] = [];
    try {
      for await (const chunk of streamChat({ message: "hi", system_key: null })) {
        chunks.push(chunk);
      }
    } catch {
      // expected
    }

    expect(chunks).toEqual([]);
  });

  it("still reports a plain ChatError for other failures", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(jsonResponse(400, { detail: "Blocked by safety filter" }));

    const error = (await drain().catch((e) => e)) as ChatError;

    expect(error).toBeInstanceOf(ChatError);
    expect(error).not.toBeInstanceOf(ChatUpsellError);
    expect(error.message).toBe("Blocked by safety filter");
  });

  it("does not mistake the per-minute rate limit for a plan refusal", async () => {
    // The chat endpoint's own 10-message limit is also a 429, and it is
    // a plain-string detail rather than the structured envelope.
    global.fetch = jest
      .fn()
      .mockResolvedValue(jsonResponse(429, { detail: "Too many messages" }));

    const error = (await drain().catch((e) => e)) as ChatError;

    expect(error).not.toBeInstanceOf(ChatUpsellError);
    expect(error.message).toBe("Too many messages");
  });
});
