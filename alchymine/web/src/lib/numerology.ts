/**
 * Numerology calculations — pure, deterministic, no LLM.
 */

const MASTER_NUMBERS = new Set([11, 22, 33]);

function reduceToSingleDigit(n: number): number {
  while (n > 9 && !MASTER_NUMBERS.has(n)) {
    n = String(n)
      .split("")
      .reduce((sum, digit) => sum + parseInt(digit, 10), 0);
  }
  return n;
}

/**
 * Calculate the Life Path Number from a birth date string (YYYY-MM-DD).
 * Reduces all digits of the full date to a single digit, preserving master
 * numbers 11, 22, and 33.
 */
export function calculateLifePathNumber(birthDate: string): number {
  const digits = birthDate.replace(/-/g, "").split("").map(Number);
  const total = digits.reduce((sum, d) => sum + d, 0);
  return reduceToSingleDigit(total);
}
