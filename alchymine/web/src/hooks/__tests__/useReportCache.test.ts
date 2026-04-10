/**
 * useReportCache — unit tests.
 *
 * Verifies localStorage persistence and context extraction.
 */

import { act, renderHook } from "@testing-library/react";

import { useReportCache } from "@/hooks/useReportCache";

beforeEach(() => {
  localStorage.clear();
});

describe("useReportCache", () => {
  it("saves and retrieves a report", () => {
    const { result } = renderHook(() => useReportCache());

    act(() => {
      result.current.saveReport("healing", { summary: "breathwork plan" });
    });

    expect(result.current.getReport("healing")).toEqual({
      summary: "breathwork plan",
    });

    // Also persisted to localStorage.
    expect(localStorage.getItem("alchymine:report:healing")).toBeTruthy();
  });

  it("returns null for unknown system keys", () => {
    const { result } = renderHook(() => useReportCache());
    expect(result.current.getReport("nonexistent")).toBeNull();
  });

  it("builds context from a cached report with summary field", () => {
    const { result } = renderHook(() => useReportCache());

    act(() => {
      result.current.saveReport("wealth", {
        summary: "budget review complete",
        details: { income: 5000, expenses: 3000 },
      });
    });

    const ctx = result.current.getContext("wealth");
    expect(ctx).not.toBeNull();
    expect(ctx!.systemKey).toBe("wealth");
    expect(ctx!.summary).toContain("budget review complete");
  });

  it("returns null context when systemKey is null", () => {
    const { result } = renderHook(() => useReportCache());
    expect(result.current.getContext(null)).toBeNull();
  });

  it("returns null context when no report is cached", () => {
    const { result } = renderHook(() => useReportCache());
    expect(result.current.getContext("creative")).toBeNull();
  });

  it("hydrates from localStorage on mount", () => {
    // Pre-populate localStorage.
    localStorage.setItem(
      "alchymine:report:intelligence",
      JSON.stringify({ profile: { life_path: 7 } }),
    );

    const { result } = renderHook(() => useReportCache());

    // After mount, the hook should pick up the stored data.
    const report = result.current.getReport("intelligence");
    expect(report).toEqual({ profile: { life_path: 7 } });
  });

  it("extracts fallback context when no summary key exists", () => {
    const { result } = renderHook(() => useReportCache());

    act(() => {
      result.current.saveReport("perspective", {
        reframe_count: 5,
        last_session: "2026-04-01",
      });
    });

    const ctx = result.current.getContext("perspective");
    expect(ctx).not.toBeNull();
    expect(ctx!.summary).toContain("Report fields:");
    expect(ctx!.summary).toContain("reframe_count");
  });
});
