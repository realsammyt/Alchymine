import { localDayKey, parseDayKey, dayKeyMinus, dayLabel } from "../localDay";

describe("localDayKey", () => {
  it("formats a date as YYYY-MM-DD", () => {
    expect(localDayKey(new Date(2026, 7, 14, 9, 30))).toBe("2026-08-14");
  });

  it("pads single-digit months and days", () => {
    expect(localDayKey(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  it("uses the local day, not the UTC one", () => {
    // 14 August at 23:30 local. In any timezone ahead of UTC this is
    // still the 14th locally while toISOString() has already rolled to
    // the 15th, which is the bug this helper exists to avoid.
    const lateEvening = new Date(2026, 7, 14, 23, 30);
    expect(localDayKey(lateEvening)).toBe("2026-08-14");
    expect(localDayKey(lateEvening)).toBe(
      `${lateEvening.getFullYear()}-08-14`,
    );
  });

  it("defaults to now", () => {
    expect(localDayKey()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("parseDayKey", () => {
  it("round-trips through localDayKey", () => {
    expect(localDayKey(parseDayKey("2026-02-28"))).toBe("2026-02-28");
  });

  it("parses to local midnight, not UTC midnight", () => {
    expect(parseDayKey("2026-08-14").getHours()).toBe(0);
    expect(parseDayKey("2026-08-14").getDate()).toBe(14);
  });
});

describe("dayKeyMinus", () => {
  it("walks back within a month", () => {
    expect(localDayKey(dayKeyMinus("2026-08-14", 6))).toBe("2026-08-08");
  });

  it("crosses a month boundary", () => {
    expect(localDayKey(dayKeyMinus("2026-03-02", 6))).toBe("2026-02-24");
  });

  it("returns the same day for an offset of zero", () => {
    expect(localDayKey(dayKeyMinus("2026-08-14", 0))).toBe("2026-08-14");
  });
});

describe("dayLabel", () => {
  it("spells the weekday and month out in full", () => {
    expect(dayLabel(parseDayKey("2026-08-14"))).toBe("Friday 14 August");
  });
});
