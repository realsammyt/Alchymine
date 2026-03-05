"use client";

import { useState, useCallback, useMemo } from "react";

// ── Types ──────────────────────────────────────────────────────────

export interface DebtEntry {
  id: string;
  name: string;
  balance: number;
  apr: number;
  minimumPayment: number;
}

interface PayoffResult {
  months: number;
  totalInterest: number;
  totalCost: number;
}

// ── Math ───────────────────────────────────────────────────────────

function calculatePayoff(
  debts: DebtEntry[],
  extraMonthly: number,
  strategy: "avalanche" | "snowball",
): PayoffResult {
  if (debts.length === 0) {
    return { months: 0, totalInterest: 0, totalCost: 0 };
  }

  // Deep copy working balances
  type WorkDebt = DebtEntry & { remaining: number; paid: boolean };
  const working: WorkDebt[] = debts.map((d) => ({
    ...d,
    remaining: d.balance,
    paid: false,
  }));

  // Sort order for priority
  const sorted = [...working].sort((a, b) => {
    if (strategy === "avalanche") return b.apr - a.apr;
    return a.balance - b.balance;
  });

  let totalInterest = 0;
  let months = 0;
  const MAX_MONTHS = 600; // 50 year safety cap

  while (months < MAX_MONTHS) {
    const active = working.filter((d) => !d.paid);
    if (active.length === 0) break;

    months++;

    // 1. Accrue interest on all active debts
    for (const debt of active) {
      const interest = debt.remaining * (debt.apr / 100 / 12);
      debt.remaining += interest;
      totalInterest += interest;
    }

    // 2. Apply minimum payments
    for (const debt of active) {
      const payment = Math.min(debt.minimumPayment, debt.remaining);
      debt.remaining -= payment;
      if (debt.remaining <= 0.005) {
        debt.remaining = 0;
        debt.paid = true;
      }
    }

    // 3. Apply extra payment to priority debt (first unpaid in sorted order)
    let remainingExtra = extraMonthly;
    for (const priorityDebt of sorted) {
      const target = working.find((d) => d.id === priorityDebt.id);
      if (!target || target.paid) continue;
      const payment = Math.min(remainingExtra, target.remaining);
      target.remaining -= payment;
      remainingExtra -= payment;
      if (target.remaining <= 0.005) {
        target.remaining = 0;
        target.paid = true;
        // Roll freed minimum payment into extra for next priority
        remainingExtra += target.minimumPayment;
      }
      if (remainingExtra <= 0) break;
    }
  }

  const totalDebt = debts.reduce((sum, d) => sum + d.balance, 0);
  return {
    months,
    totalInterest: Math.round(totalInterest),
    totalCost: Math.round(totalDebt + totalInterest),
  };
}

// ── Demo data ──────────────────────────────────────────────────────

export const DEMO_DEBT_ENTRIES: DebtEntry[] = [
  {
    id: "student-loans",
    name: "Student Loans",
    balance: 12400,
    apr: 5.5,
    minimumPayment: 130,
  },
  {
    id: "credit-card",
    name: "Credit Card",
    balance: 2800,
    apr: 19.9,
    minimumPayment: 84,
  },
  {
    id: "car-loan",
    name: "Car Loan",
    balance: 8200,
    apr: 4.2,
    minimumPayment: 180,
  },
  {
    id: "personal-loan",
    name: "Personal Loan",
    balance: 1200,
    apr: 7.8,
    minimumPayment: 60,
  },
];

// ── Helpers ────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatMonths(months: number): string {
  if (months === 0) return "Paid off";
  const y = Math.floor(months / 12);
  const m = months % 12;
  if (y === 0) return `${m} mo`;
  if (m === 0) return `${y} yr`;
  return `${y} yr ${m} mo`;
}

let nextId = 1;

function newDebt(): DebtEntry {
  return {
    id: `debt-${nextId++}`,
    name: "",
    balance: 0,
    apr: 0,
    minimumPayment: 0,
  };
}

// ── Sub-components ─────────────────────────────────────────────────

function ResultCard({
  label,
  result,
  colorClass,
}: {
  label: string;
  result: PayoffResult;
  colorClass: string;
}) {
  return (
    <div className="card-surface p-4 space-y-3">
      <h4 className={`font-display text-sm font-medium ${colorClass}`}>
        {label}
      </h4>
      <div className="space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="font-body text-text/50">Time to payoff</span>
          <span className={`font-display font-medium ${colorClass}`}>
            {formatMonths(result.months)}
          </span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="font-body text-text/50">Total interest</span>
          <span className="font-display font-medium text-text/80">
            {formatCurrency(result.totalInterest)}
          </span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="font-body text-text/50">Total cost</span>
          <span className="font-display font-medium text-text/80">
            {formatCurrency(result.totalCost)}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────

interface DebtCalculatorProps {
  initialDebts?: DebtEntry[];
}

export default function DebtCalculator({
  initialDebts,
}: DebtCalculatorProps) {
  const [debts, setDebts] = useState<DebtEntry[]>(
    initialDebts ?? [newDebt()],
  );
  const [extraPayment, setExtraPayment] = useState(0);

  const avalanche = useMemo(
    () => calculatePayoff(debts, extraPayment, "avalanche"),
    [debts, extraPayment],
  );

  const snowball = useMemo(
    () => calculatePayoff(debts, extraPayment, "snowball"),
    [debts, extraPayment],
  );

  const interestSaved = Math.max(
    0,
    snowball.totalInterest - avalanche.totalInterest,
  );

  const addDebt = useCallback(() => {
    setDebts((prev) => [...prev, newDebt()]);
  }, []);

  const removeDebt = useCallback((id: string) => {
    setDebts((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const updateDebt = useCallback(
    (id: string, field: keyof Omit<DebtEntry, "id">, raw: string) => {
      setDebts((prev) =>
        prev.map((d) => {
          if (d.id !== id) return d;
          if (field === "name") return { ...d, name: raw };
          const num = parseFloat(raw);
          return { ...d, [field]: isNaN(num) ? 0 : num };
        }),
      );
    },
    [],
  );

  const hasValidDebts = debts.some((d) => d.balance > 0 && d.minimumPayment > 0);

  return (
    <div data-testid="debt-calculator">
      {/* Section header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display text-lg font-medium text-text">
          Debt Payoff Calculator
        </h3>
        <button
          onClick={addDebt}
          className="flex items-center gap-1.5 text-xs font-body text-primary hover:text-primary/80 transition-colors px-3 py-1.5 bg-primary/10 hover:bg-primary/15 rounded-full min-h-[36px]"
          aria-label="Add a debt"
        >
          <span aria-hidden="true">+</span> Add Debt
        </button>
      </div>

      {/* Debt rows */}
      <div className="space-y-3 mb-5" role="list" aria-label="Debt entries">
        {debts.map((debt, idx) => (
          <div
            key={debt.id}
            role="listitem"
            className="grid grid-cols-12 gap-2 items-end"
          >
            {/* Name */}
            <div className="col-span-12 sm:col-span-4">
              {idx === 0 && (
                <label className="font-body text-xs text-text/40 mb-1 block">
                  Debt name
                </label>
              )}
              <input
                type="text"
                value={debt.name}
                onChange={(e) => updateDebt(debt.id, "name", e.target.value)}
                placeholder="e.g. Credit Card"
                className="w-full bg-surface border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder-text/20 focus:outline-none focus:ring-1 focus:ring-primary/40 min-h-[44px]"
                aria-label={`Debt name for entry ${idx + 1}`}
              />
            </div>

            {/* Balance */}
            <div className="col-span-4 sm:col-span-2">
              {idx === 0 && (
                <label className="font-body text-xs text-text/40 mb-1 block">
                  Balance ($)
                </label>
              )}
              <input
                type="number"
                min="0"
                step="100"
                value={debt.balance || ""}
                onChange={(e) =>
                  updateDebt(debt.id, "balance", e.target.value)
                }
                placeholder="0"
                className="w-full bg-surface border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder-text/20 focus:outline-none focus:ring-1 focus:ring-primary/40 min-h-[44px]"
                aria-label={`Balance for ${debt.name || `entry ${idx + 1}`}`}
              />
            </div>

            {/* APR */}
            <div className="col-span-4 sm:col-span-2">
              {idx === 0 && (
                <label className="font-body text-xs text-text/40 mb-1 block">
                  APR (%)
                </label>
              )}
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={debt.apr || ""}
                onChange={(e) => updateDebt(debt.id, "apr", e.target.value)}
                placeholder="0"
                className="w-full bg-surface border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder-text/20 focus:outline-none focus:ring-1 focus:ring-primary/40 min-h-[44px]"
                aria-label={`APR for ${debt.name || `entry ${idx + 1}`}`}
              />
            </div>

            {/* Minimum payment */}
            <div className="col-span-3 sm:col-span-3">
              {idx === 0 && (
                <label className="font-body text-xs text-text/40 mb-1 block">
                  Min. payment ($)
                </label>
              )}
              <input
                type="number"
                min="0"
                step="10"
                value={debt.minimumPayment || ""}
                onChange={(e) =>
                  updateDebt(debt.id, "minimumPayment", e.target.value)
                }
                placeholder="0"
                className="w-full bg-surface border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder-text/20 focus:outline-none focus:ring-1 focus:ring-primary/40 min-h-[44px]"
                aria-label={`Minimum payment for ${debt.name || `entry ${idx + 1}`}`}
              />
            </div>

            {/* Remove */}
            <div className="col-span-1 flex items-end pb-0">
              {debts.length > 1 && (
                <button
                  onClick={() => removeDebt(debt.id)}
                  className="w-9 h-[44px] flex items-center justify-center text-text/30 hover:text-text/60 hover:bg-white/5 rounded-lg transition-colors"
                  aria-label={`Remove ${debt.name || `debt entry ${idx + 1}`}`}
                >
                  <svg
                    className="w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Extra payment slider */}
      <div className="mb-6 p-4 bg-surface/50 rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <label
            htmlFor="extra-payment-slider"
            className="font-body text-sm text-text/70"
          >
            Extra monthly payment
          </label>
          <span className="font-display text-sm font-medium text-primary">
            {formatCurrency(extraPayment)}
          </span>
        </div>
        <input
          id="extra-payment-slider"
          type="range"
          min="0"
          max="500"
          step="25"
          value={extraPayment}
          onChange={(e) => setExtraPayment(Number(e.target.value))}
          className="w-full accent-[#DAA520] h-2 rounded-full cursor-pointer"
          aria-label={`Extra monthly payment: ${formatCurrency(extraPayment)}`}
        />
        <div className="flex justify-between font-body text-xs text-text/30 mt-1">
          <span>$0</span>
          <span>$500</span>
        </div>
      </div>

      {/* Strategy comparison */}
      {hasValidDebts && (
        <>
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <ResultCard
              label="Avalanche (highest rate first)"
              result={avalanche}
              colorClass="text-primary"
            />
            <ResultCard
              label="Snowball (lowest balance first)"
              result={snowball}
              colorClass="text-accent"
            />
          </div>

          {interestSaved > 0 && (
            <div className="flex items-center justify-between bg-primary/[0.08] border border-primary/20 rounded-xl p-3">
              <span className="font-body text-sm text-text/60">
                Interest saved with Avalanche method
              </span>
              <span className="font-display text-sm font-medium text-primary">
                {formatCurrency(interestSaved)}
              </span>
            </div>
          )}
        </>
      )}

      {/* Disclaimer */}
      <div className="mt-4 text-center">
        <p className="font-body text-xs text-text/30">
          Calculations are estimates only. Consult a financial professional before making decisions.
        </p>
      </div>
    </div>
  );
}
