/**
 * starterPrompts — unit tests.
 *
 * Verifies that each system key returns exactly 3 prompts with the
 * required shape, and that unknown / null keys fall back to general.
 */

import { getStarterPrompts } from "@/lib/starterPrompts";

describe("getStarterPrompts", () => {
  const systems = [
    "intelligence",
    "healing",
    "wealth",
    "creative",
    "perspective",
  ];

  it.each(systems)("returns 3 prompts for %s", (key) => {
    const prompts = getStarterPrompts(key);
    expect(prompts).toHaveLength(3);
    for (const p of prompts) {
      expect(typeof p.label).toBe("string");
      expect(p.label.length).toBeGreaterThan(0);
      expect(typeof p.message).toBe("string");
      expect(p.message.length).toBeGreaterThan(0);
    }
  });

  it("returns general prompts when systemKey is null", () => {
    const prompts = getStarterPrompts(null);
    expect(prompts).toHaveLength(3);
    // General prompts should mention "journey" or "profile" or "pillars".
    const allLabels = prompts.map((p) => p.label).join(" ");
    expect(allLabels.length).toBeGreaterThan(0);
  });

  it("returns general prompts for an unknown system key", () => {
    const prompts = getStarterPrompts("unknown-system");
    expect(prompts).toHaveLength(3);
  });

  it("each system has unique prompts", () => {
    const allMessages = new Set<string>();
    for (const key of systems) {
      for (const p of getStarterPrompts(key)) {
        expect(allMessages.has(p.message)).toBe(false);
        allMessages.add(p.message);
      }
    }
  });
});
