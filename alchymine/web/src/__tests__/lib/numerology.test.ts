import { calculateLifePathNumber } from "@/lib/numerology";

describe("calculateLifePathNumber", () => {
  // Known reduction examples
  it("reduces 1990-07-15 to 5", () => {
    // 19900715 → 1+9+9+0+0+7+1+5 = 32 → 3+2 = 5
    expect(calculateLifePathNumber("1990-07-15")).toBe(5);
  });

  it("preserves master number 11 for 1985-11-22", () => {
    // 19851122 → 1+9+8+5+1+1+2+2 = 29 → 2+9 = 11 (master, keep)
    expect(calculateLifePathNumber("1985-11-22")).toBe(11);
  });

  it("reduces to 4 for 2000-01-01", () => {
    // 20000101 → 2+0+0+0+0+1+0+1 = 4
    expect(calculateLifePathNumber("2000-01-01")).toBe(4);
  });

  it("preserves master number 11 when first reduction lands on 11", () => {
    // 20000207 → 2+0+0+0+0+2+0+7 = 11 (master, keep as-is)
    expect(calculateLifePathNumber("2000-02-07")).toBe(11);
  });

  it("preserves master number 22 when first reduction lands on 22", () => {
    // 19111009 → 1+9+1+1+1+0+0+9 = 22 (master, keep as-is)
    expect(calculateLifePathNumber("1911-10-09")).toBe(22);
  });

  it("preserves master number 33 when first reduction lands on 33", () => {
    // 19951008 → 1+9+9+5+1+0+0+8 = 33 (master, keep as-is)
    expect(calculateLifePathNumber("1995-10-08")).toBe(33);
  });

  it("reduces normally when total is not a master number", () => {
    // 19800101 → 1+9+8+0+0+1+0+1 = 20 → 2+0 = 2
    expect(calculateLifePathNumber("1980-01-01")).toBe(2);
  });

  it("does not reduce master 11 further to 2", () => {
    // 20000207 → sum = 11, should stay 11 not reduce to 2
    const result = calculateLifePathNumber("2000-02-07");
    expect(result).toBe(11);
    expect(result).not.toBe(2);
  });

  it("does not reduce master 22 further to 4", () => {
    // 19111009 → sum = 22, should stay 22 not reduce to 4
    const result = calculateLifePathNumber("1911-10-09");
    expect(result).toBe(22);
    expect(result).not.toBe(4);
  });

  it("does not reduce master 33 further to 6", () => {
    // 19951008 → sum = 33, should stay 33 not reduce to 6
    const result = calculateLifePathNumber("1995-10-08");
    expect(result).toBe(33);
    expect(result).not.toBe(6);
  });

  it("handles multi-step reduction correctly", () => {
    // 19891231 → 1+9+8+9+1+2+3+1 = 34 → 3+4 = 7
    expect(calculateLifePathNumber("1989-12-31")).toBe(7);
  });
});
