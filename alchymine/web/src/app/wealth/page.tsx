"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import Button from "@/components/shared/Button";
import Card from "@/components/shared/Card";
import ProgressBar from "@/components/shared/ProgressBar";
import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  getWealthProfile,
  getWealthLevers,
  WealthProfileResponse,
  LeverResponse,
} from "@/lib/api";
import { useApi, getStoredIntake } from "@/lib/useApi";

// ── Constants ─────────────────────────────────────────────────────

const WEALTH_LEVERS = [
  {
    name: "EARN",
    icon: "\u{1F4BC}",
    description: "Optimize active and passive income streams",
    color: "gold" as const,
    examples: [
      "Salary negotiation",
      "Side income",
      "Freelancing",
      "Content monetization",
    ],
  },
  {
    name: "KEEP",
    icon: "\u{1F6E1}\u{FE0F}",
    description: "Reduce expenses and protect against wealth erosion",
    color: "teal" as const,
    examples: [
      "Tax optimization",
      "Expense audit",
      "Insurance review",
      "Debt management",
    ],
  },
  {
    name: "GROW",
    icon: "\u{1F4C8}",
    description: "Invest and compound your wealth over time",
    color: "gold" as const,
    examples: [
      "Index investing",
      "Real estate",
      "Business equity",
      "Skill investment",
    ],
  },
  {
    name: "PROTECT",
    icon: "\u{1F3F0}",
    description: "Safeguard wealth from risks and unexpected events",
    color: "purple" as const,
    examples: [
      "Emergency fund",
      "Estate planning",
      "Asset protection",
      "Insurance",
    ],
  },
  {
    name: "TRANSFER",
    icon: "\u{1F91D}",
    description: "Build and share generational wealth",
    color: "teal" as const,
    examples: [
      "Trust structures",
      "Education funds",
      "Family governance",
      "Charitable giving",
    ],
  },
];

// Design-system color palette for levers — gold, teal, purple, gold-light, teal-light, purple-light
const LEVER_PALETTE = [
  { bg: "rgba(218,165,32,0.12)", text: "#DAA520", bar: "#DAA520" },
  { bg: "rgba(32,178,170,0.12)", text: "#20B2AA", bar: "#20B2AA" },
  { bg: "rgba(123,45,142,0.12)", text: "#9B4DCA", bar: "#9B4DCA" },
  { bg: "rgba(240,192,80,0.12)", text: "#F0C050", bar: "#F0C050" },
  { bg: "rgba(92,214,208,0.12)", text: "#5CD6D0", bar: "#5CD6D0" },
];

// Budget category colors — design palette cycle
const BUDGET_PALETTE = [
  "#DAA520", // primary gold
  "#20B2AA", // accent teal
  "#7B2D8E", // secondary purple
  "#F0C050", // primary-light gold
  "#5CD6D0", // accent-light teal
  "#9B4DCA", // secondary-light purple
  "#B8860B", // primary-dark gold
];

const WEALTH_ARCHETYPES_PREVIEW = [
  {
    name: "The Builder",
    description:
      "Systematic wealth accumulation through structure and discipline",
    icon: "\u{1F3D7}\u{FE0F}",
  },
  {
    name: "The Innovator",
    description: "Creative wealth generation through new ideas and ventures",
    icon: "\u{1F4A1}",
  },
  {
    name: "The Sage Investor",
    description: "Evidence-based wealth growth through deep research",
    icon: "\u{1F4DA}",
  },
  {
    name: "The Connector",
    description: "Relationship-driven wealth through networks and community",
    icon: "\u{1F91D}",
  },
  {
    name: "The Warrior",
    description: "Ambitious wealth building through decisive action",
    icon: "\u{2694}\u{FE0F}",
  },
  {
    name: "The Mystic Trader",
    description: "Intuition-guided wealth with impact investing focus",
    icon: "\u{1F52E}",
  },
];

// ── Demo data for visualizations (deterministic) ─────────────────

interface DebtItem {
  name: string;
  balance: number;
  total: number;
  rate: number;
  monthsRemaining: number;
}

const DEMO_DEBTS: DebtItem[] = [
  {
    name: "Student Loans",
    balance: 12400,
    total: 35000,
    rate: 5.5,
    monthsRemaining: 36,
  },
  {
    name: "Credit Card",
    balance: 2800,
    total: 8000,
    rate: 19.9,
    monthsRemaining: 8,
  },
  {
    name: "Car Loan",
    balance: 8200,
    total: 18000,
    rate: 4.2,
    monthsRemaining: 24,
  },
  {
    name: "Personal Loan",
    balance: 1200,
    total: 5000,
    rate: 7.8,
    monthsRemaining: 4,
  },
];

interface BudgetCategory {
  name: string;
  amount: number;
  color: string;
}

const DEMO_BUDGET: { income: number; categories: BudgetCategory[] } = {
  income: 5800,
  categories: [
    { name: "Housing", amount: 1600, color: BUDGET_PALETTE[0] },
    { name: "Food", amount: 650, color: BUDGET_PALETTE[1] },
    { name: "Transport", amount: 350, color: BUDGET_PALETTE[2] },
    { name: "Debt Payments", amount: 850, color: BUDGET_PALETTE[3] },
    { name: "Savings", amount: 700, color: BUDGET_PALETTE[4] },
    { name: "Utilities", amount: 280, color: BUDGET_PALETTE[5] },
    { name: "Other", amount: 370, color: BUDGET_PALETTE[6] },
  ],
};

const DEMO_NET_WORTH = {
  assets: [
    { name: "Savings Account", value: 8500 },
    { name: "Investment Portfolio", value: 15200 },
    { name: "Retirement (401k)", value: 22300 },
    { name: "Vehicle", value: 12000 },
  ],
  liabilities: [
    { name: "Student Loans", value: 12400 },
    { name: "Credit Card", value: 2800 },
    { name: "Car Loan", value: 8200 },
    { name: "Personal Loan", value: 1200 },
  ],
};

// ── Helper: Format currency ───────────────────────────────────────

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

// ── Sub-components ────────────────────────────────────────────────

function DebtPayoffTimeline({ debts }: { debts: DebtItem[] }) {
  const sorted = [...debts].sort((a, b) => b.rate - a.rate); // Avalanche order
  const maxMonths = Math.max(...sorted.map((d) => d.monthsRemaining));

  return (
    <div data-testid="debt-payoff-timeline">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display text-lg font-medium text-text">
          Debt Payoff Timeline
        </h3>
        <span className="text-xs font-body text-text/40 px-3 py-1 bg-white/5 rounded-full">
          Avalanche Method (highest rate first)
        </span>
      </div>
      <div className="space-y-5">
        {sorted.map((debt) => {
          const paidPct = ((debt.total - debt.balance) / debt.total) * 100;
          const timelinePct = (debt.monthsRemaining / maxMonths) * 100;
          return (
            <div key={debt.name}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-body text-sm font-medium text-text/80">
                    {debt.name}
                  </span>
                  {/* Rate label — primary-dark gold instead of red to avoid crisis framing */}
                  <span
                    className="text-xs font-body text-primary-dark"
                    aria-label={`${debt.rate}% annual percentage rate`}
                  >
                    {debt.rate}% APR
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-body text-xs text-text/40">
                    {debt.monthsRemaining} mo left
                  </span>
                  <span
                    className="font-display text-sm font-medium text-primary"
                    aria-label={`Balance: ${formatCurrency(debt.balance)}`}
                  >
                    {formatCurrency(debt.balance)}
                  </span>
                </div>
              </div>
              {/* Payoff progress bar — paid portion in teal (positive growth), remaining in primary-dark (attention) */}
              <div
                className="h-3 bg-surface rounded-full overflow-hidden relative"
                role="progressbar"
                aria-valuenow={Math.round(paidPct)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${debt.name} paid off: ${Math.round(paidPct)}%`}
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-dark to-accent transition-all duration-700"
                  style={{ width: `${paidPct}%` }}
                />
                {/* Remaining portion — warm gold tint, not alarming red */}
                <div
                  className="absolute top-0 h-full bg-primary-dark/15 rounded-r-full"
                  style={{ left: `${paidPct}%`, width: `${100 - paidPct}%` }}
                />
              </div>
              {/* Timeline bar underneath */}
              <div className="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary/30"
                  style={{ width: `${timelinePct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-5 flex items-center justify-between font-body text-xs text-text/40">
        <span>
          Total remaining:{" "}
          <span
            className="font-display text-primary-dark"
            aria-label={`Total remaining debt: ${formatCurrency(debts.reduce((sum, d) => sum + d.balance, 0))}`}
          >
            {formatCurrency(debts.reduce((sum, d) => sum + d.balance, 0))}
          </span>
        </span>
        <span>
          Paid off:{" "}
          <span
            className="font-display text-accent"
            aria-label={`Total paid off: ${formatCurrency(debts.reduce((sum, d) => sum + (d.total - d.balance), 0))}`}
          >
            {formatCurrency(
              debts.reduce((sum, d) => sum + (d.total - d.balance), 0),
            )}
          </span>
        </span>
      </div>
    </div>
  );
}

function BudgetBreakdown({
  income,
  categories,
}: {
  income: number;
  categories: BudgetCategory[];
}) {
  const totalExpenses = categories.reduce((sum, c) => sum + c.amount, 0);
  const savingsCategory = categories.find((c) => c.name === "Savings");
  const savingsRate = savingsCategory
    ? (savingsCategory.amount / income) * 100
    : 0;
  const remaining = income - totalExpenses;

  return (
    <div data-testid="budget-breakdown">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display text-lg font-medium text-text">
          Budget Breakdown
        </h3>
        <div className="flex items-center gap-3">
          <span className="font-body text-xs text-text/40">
            Monthly Income:
          </span>
          <span
            className="font-display text-sm font-medium text-primary"
            aria-label={`Monthly income: ${formatCurrency(income)}`}
          >
            {formatCurrency(income)}
          </span>
        </div>
      </div>

      {/* Stacked bar — design palette colors */}
      <div
        className="h-8 rounded-full overflow-hidden flex mb-5"
        role="img"
        aria-label="Budget allocation bar showing spending categories as proportional segments"
      >
        {categories.map((cat) => {
          const pct = (cat.amount / income) * 100;
          return (
            <div
              key={cat.name}
              title={`${cat.name}: ${formatCurrency(cat.amount)} (${pct.toFixed(0)}%)`}
              style={{
                width: `${pct}%`,
                backgroundColor: cat.color,
                transition: "width 0.5s ease",
                minWidth: pct > 3 ? undefined : 4,
              }}
            />
          );
        })}
        {remaining > 0 && (
          <div
            title={`Unallocated: ${formatCurrency(remaining)}`}
            style={{
              width: `${(remaining / income) * 100}%`,
              backgroundColor: "rgba(255,255,255,0.06)",
            }}
          />
        )}
      </div>

      {/* Category breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {categories.map((cat) => {
          const pct = (cat.amount / income) * 100;
          return (
            <div key={cat.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: cat.color }}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <div className="font-body text-xs text-text/60 truncate">
                  {cat.name}
                </div>
                <div className="font-display text-xs font-medium text-text/80">
                  {formatCurrency(cat.amount)}{" "}
                  <span className="font-body text-text/40">
                    ({pct.toFixed(0)}%)
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Savings rate highlight — teal for positive growth, not arbitrary green */}
      <div className="bg-accent/[0.08] border border-accent/20 rounded-xl p-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-accent text-lg" aria-hidden="true">
            {"\u{1F4B0}"}
          </span>
          <span className="font-body text-sm text-text/60">Savings Rate</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-24 h-2 bg-white/5 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round(savingsRate)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Savings rate: ${savingsRate.toFixed(0)}%`}
          >
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: `${Math.min(savingsRate, 100)}%` }}
            />
          </div>
          <span
            className="font-display text-sm font-medium text-accent"
            aria-hidden="true"
          >
            {savingsRate.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
}

function NetWorthTracker({
  assets,
  liabilities,
}: {
  assets: { name: string; value: number }[];
  liabilities: { name: string; value: number }[];
}) {
  const totalAssets = assets.reduce((sum, a) => sum + a.value, 0);
  const totalLiabilities = liabilities.reduce((sum, l) => sum + l.value, 0);
  const netWorth = totalAssets - totalLiabilities;
  const maxValue = Math.max(totalAssets, totalLiabilities);

  // Positive net worth: teal (growth). Attention-needed: primary-dark gold (not red — not a crisis)
  const netWorthColor = netWorth >= 0 ? "text-accent" : "text-primary-dark";
  const netWorthLabel =
    netWorth >= 0
      ? `Positive net worth: ${formatCurrency(netWorth)}`
      : `Net worth: ${formatCurrency(netWorth)} — needs attention`;

  return (
    <div data-testid="net-worth-tracker">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display text-lg font-medium text-text">
          Net Worth Summary
        </h3>
        <div className="text-right">
          <div className="font-body text-xs text-text/40">Net Worth</div>
          <div
            className={`font-display text-xl font-light ${netWorthColor}`}
            aria-label={netWorthLabel}
          >
            {formatCurrency(netWorth)}
          </div>
        </div>
      </div>

      {/* Visual comparison bars */}
      <div className="space-y-3 mb-5">
        <div>
          <div className="flex justify-between font-body text-xs mb-1.5">
            <span className="text-accent/80">Assets</span>
            <span className="text-text/60">{formatCurrency(totalAssets)}</span>
          </div>
          <div
            className="h-6 bg-surface rounded-lg overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round((totalAssets / maxValue) * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Assets: ${formatCurrency(totalAssets)}`}
          >
            <div
              className="h-full rounded-lg bg-gradient-to-r from-accent-dark/60 to-accent/60 transition-all duration-700 flex items-center px-2"
              style={{ width: `${(totalAssets / maxValue) * 100}%` }}
            >
              <span className="font-display text-[10px] text-white/70 font-medium whitespace-nowrap">
                {formatCurrency(totalAssets)}
              </span>
            </div>
          </div>
        </div>
        <div>
          <div className="flex justify-between font-body text-xs mb-1.5">
            <span className="text-primary-dark/80">Liabilities</span>
            <span className="text-text/60">
              {formatCurrency(totalLiabilities)}
            </span>
          </div>
          <div
            className="h-6 bg-surface rounded-lg overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round((totalLiabilities / maxValue) * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Liabilities: ${formatCurrency(totalLiabilities)}`}
          >
            <div
              className="h-full rounded-lg bg-gradient-to-r from-primary-dark/50 to-primary/40 transition-all duration-700 flex items-center px-2"
              style={{ width: `${(totalLiabilities / maxValue) * 100}%` }}
            >
              <span className="font-display text-[10px] text-white/70 font-medium whitespace-nowrap">
                {formatCurrency(totalLiabilities)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown grid */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
            Assets
          </h4>
          <div className="space-y-2">
            {assets.map((a) => (
              <div
                key={a.name}
                className="flex justify-between items-center text-sm"
              >
                <span className="font-body text-text/60">{a.name}</span>
                <span
                  className="font-display text-accent/80 font-medium"
                  aria-label={`${a.name}: ${formatCurrency(a.value)}`}
                >
                  {formatCurrency(a.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
            Liabilities
          </h4>
          <div className="space-y-2">
            {liabilities.map((l) => (
              <div
                key={l.name}
                className="flex justify-between items-center text-sm"
              >
                <span className="font-body text-text/60">{l.name}</span>
                <span
                  className="font-display text-primary-dark/80 font-medium"
                  aria-label={`${l.name}: ${formatCurrency(l.value)}`}
                >
                  -{formatCurrency(l.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function LeverPriorityDisplay({ levers }: { levers: string[] }) {
  return (
    <div data-testid="lever-priority">
      <h3 className="font-display text-lg font-medium text-text mb-4">
        Your Lever Priority
      </h3>
      <div className="flex flex-col gap-3">
        {levers.map((lever, i) => {
          const leverData = WEALTH_LEVERS.find((l) => l.name === lever);
          const barWidth = 100 - i * 15;
          const palette = LEVER_PALETTE[i % LEVER_PALETTE.length];
          return (
            <div key={lever} className="flex items-center gap-3">
              <div
                className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-display text-sm font-medium"
                style={{ background: palette.bg, color: palette.text }}
                aria-hidden="true"
              >
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm" aria-hidden="true">
                      {leverData?.icon}
                    </span>
                    <span className="font-body text-sm font-medium text-text/80">
                      {lever}
                    </span>
                  </div>
                  <span className="font-body text-xs text-text/40">
                    {i === 0 ? "Top Priority" : `Priority ${i + 1}`}
                  </span>
                </div>
                <div
                  className="h-2 bg-surface rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={barWidth}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${lever} priority: ${i === 0 ? "top" : `${i + 1}`}`}
                >
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${barWidth}%`,
                      background: `linear-gradient(90deg, ${palette.bar}55, ${palette.bar})`,
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────

export default function WealthPage() {
  const [selectedLever, setSelectedLever] = useState<string | null>(null);
  const intake = useMemo(() => getStoredIntake(), []);
  const hasIntake = !!intake?.intention;

  const wealthProfile = useApi<WealthProfileResponse>(
    hasIntake ? () => getWealthProfile({ intention: intake!.intention }) : null,
    [intake?.intention],
  );

  const levers = useApi<LeverResponse>(
    hasIntake ? () => getWealthLevers({ intention: intake!.intention }) : null,
    [intake?.intention],
  );

  return (
    <div className="grain-overlay bg-atmosphere min-h-screen">
      <MotionReveal>
        <main className="px-4 sm:px-6 lg:px-8 py-8">
          <div className="max-w-5xl mx-auto">
            {/* ── Page Header ─────────────────────────────────────────── */}
            <header className="mb-10">
              <MotionReveal delay={0.05} y={16}>
                <h1 className="font-display text-display-md font-light mb-3">
                  <span className="text-gradient-gold">
                    Generational Wealth
                  </span>
                </h1>
              </MotionReveal>
              <MotionReveal delay={0.15} y={12}>
                <p className="font-body text-text/40 text-base max-w-2xl">
                  Five-lever generational wealth strategy. All calculations are
                  deterministic — no AI guesswork with your finances.
                </p>
              </MotionReveal>
              <MotionReveal delay={0.22} y={8}>
                <div className="mt-4 inline-block bg-surface/50 border border-primary/20 rounded-full px-4 py-2">
                  <span className="font-body text-xs text-text/40">
                    Not financial advice. All strategies require professional
                    review.
                  </span>
                </div>
              </MotionReveal>
            </header>

            {/* ── Personalized Wealth Profile ──────────────────────────── */}
            {hasIntake && (
              <section className="mb-12" aria-labelledby="your-wealth-heading">
                <MotionReveal delay={0.1}>
                  <h2
                    id="your-wealth-heading"
                    className="section-heading-sm mb-6 flex items-center gap-3"
                  >
                    <span
                      className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                      aria-hidden="true"
                    >
                      {"\u{2728}"}
                    </span>
                    Your Wealth Profile
                  </h2>
                </MotionReveal>
                <ApiStateView
                  loading={wealthProfile.loading}
                  error={wealthProfile.error}
                  empty={!wealthProfile.data}
                  loadingText="Analyzing your wealth archetype..."
                  emptyText="Complete the full assessment to discover your wealth archetype and personalized strategies."
                  onRetry={wealthProfile.refetch}
                >
                  {wealthProfile.data && (
                    <MotionReveal delay={0.15}>
                      <div className="card-surface p-6 space-y-4">
                        <div className="flex items-center gap-4">
                          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-3xl">
                            {WEALTH_ARCHETYPES_PREVIEW.find((a) =>
                              a.name
                                .toLowerCase()
                                .includes(
                                  wealthProfile.data!.wealth_archetype.toLowerCase(),
                                ),
                            )?.icon ?? "\u{1F4B0}"}
                          </div>
                          <div>
                            <h3 className="font-display text-xl font-light text-primary">
                              {wealthProfile.data.wealth_archetype}
                            </h3>
                            <p className="font-body text-sm text-text/50">
                              {wealthProfile.data.description}
                            </p>
                          </div>
                        </div>

                        <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                          <div>
                            <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                              Strengths
                            </h4>
                            <div className="flex flex-wrap gap-2">
                              {wealthProfile.data.strengths.map((s) => (
                                <span
                                  key={s}
                                  className="px-3 py-1 bg-primary/10 text-primary font-body text-xs rounded-full"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                              Blind Spots
                            </h4>
                            <div className="flex flex-wrap gap-2">
                              {wealthProfile.data.blind_spots.map((b) => (
                                <span
                                  key={b}
                                  className="px-3 py-1 bg-white/5 text-text/50 font-body text-xs rounded-full"
                                >
                                  {b}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        {levers.data && (
                          <div className="pt-4 border-t border-white/5">
                            <LeverPriorityDisplay levers={levers.data.levers} />
                          </div>
                        )}
                      </div>
                    </MotionReveal>
                  )}
                </ApiStateView>
              </section>
            )}

            {/* ── Financial Dashboard Cards ────────────────────────────── */}
            <section
              className="mb-12"
              aria-labelledby="financial-dashboard-heading"
            >
              <MotionReveal delay={0.05}>
                <h2
                  id="financial-dashboard-heading"
                  className="section-heading-sm mb-3 flex items-center gap-3"
                >
                  <span
                    className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                    aria-hidden="true"
                  >
                    {"\u{1F4CA}"}
                  </span>
                  Financial Dashboard
                </h2>
                <hr className="rule-gold my-5 max-w-[60px]" />
                <p className="font-body text-text/40 text-sm mb-6">
                  Sample visualizations showing how your financial data will be
                  displayed. All calculations use standard deterministic
                  formulas.
                </p>
              </MotionReveal>

              <MotionStagger staggerDelay={0.12} className="space-y-6">
                {/* Debt Payoff Timeline */}
                <MotionStaggerItem>
                  <Card title="">
                    <DebtPayoffTimeline debts={DEMO_DEBTS} />
                  </Card>
                </MotionStaggerItem>

                {/* Budget Breakdown */}
                <MotionStaggerItem>
                  <Card title="">
                    <BudgetBreakdown
                      income={DEMO_BUDGET.income}
                      categories={DEMO_BUDGET.categories}
                    />
                  </Card>
                </MotionStaggerItem>

                {/* Net Worth Tracker */}
                <MotionStaggerItem>
                  <Card title="">
                    <NetWorthTracker
                      assets={DEMO_NET_WORTH.assets}
                      liabilities={DEMO_NET_WORTH.liabilities}
                    />
                  </Card>
                </MotionStaggerItem>
              </MotionStagger>
            </section>

            {/* ── Five Wealth Levers ───────────────────────────────────── */}
            <section className="mb-12" aria-labelledby="levers-heading">
              <MotionReveal delay={0.05}>
                <h2 id="levers-heading" className="section-heading-sm mb-2">
                  Five Wealth Levers
                </h2>
                <hr className="rule-gold my-5 max-w-[60px]" />
              </MotionReveal>

              <MotionStagger
                staggerDelay={0.09}
                className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6"
              >
                {WEALTH_LEVERS.map((lever) => (
                  <MotionStaggerItem key={lever.name}>
                    <button
                      onClick={() =>
                        setSelectedLever(
                          selectedLever === lever.name ? null : lever.name,
                        )
                      }
                      aria-pressed={selectedLever === lever.name}
                      className={`card-surface p-4 text-left w-full transition-all duration-300 hover:-translate-y-1 touch-target ${
                        selectedLever === lever.name
                          ? "glow-gold ring-1 ring-primary/30"
                          : "hover:glow-gold"
                      }`}
                    >
                      <div className="text-3xl mb-2" aria-hidden="true">
                        {lever.icon}
                      </div>
                      <h3 className="font-display font-medium text-sm mb-1">
                        {lever.name}
                      </h3>
                      <p className="font-body text-text/40 text-xs">
                        {lever.description}
                      </p>
                    </button>
                  </MotionStaggerItem>
                ))}
              </MotionStagger>

              {selectedLever && (
                <MotionReveal duration={0.4}>
                  <div className="card-surface-elevated p-6 mb-6 animate-fade-in">
                    <h3 className="font-display text-xl font-light text-primary mb-4">
                      {
                        WEALTH_LEVERS.find((l) => l.name === selectedLever)
                          ?.icon
                      }{" "}
                      {selectedLever} Strategies
                    </h3>
                    <div className="grid sm:grid-cols-2 gap-3">
                      {WEALTH_LEVERS.find(
                        (l) => l.name === selectedLever,
                      )?.examples.map((ex) => (
                        <div
                          key={ex}
                          className="flex items-center gap-2 font-body text-text/70 text-sm"
                        >
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-primary"
                            aria-hidden="true"
                          />
                          {ex}
                        </div>
                      ))}
                    </div>
                  </div>
                </MotionReveal>
              )}
            </section>

            {/* ── Wealth Archetypes Preview ────────────────────────────── */}
            <section className="mb-12" aria-labelledby="archetypes-heading">
              <MotionReveal delay={0.05}>
                <h2 id="archetypes-heading" className="section-heading-sm mb-2">
                  Wealth Archetypes
                </h2>
                <hr className="rule-gold my-5 max-w-[60px]" />
                <p className="font-body text-text/40 mb-6 text-sm">
                  Your wealth archetype is derived from your numerology Life
                  Path and Jungian archetype. Complete your profile to discover
                  yours.
                </p>
              </MotionReveal>

              <MotionStagger
                staggerDelay={0.08}
                className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"
              >
                {WEALTH_ARCHETYPES_PREVIEW.map((archetype) => (
                  <MotionStaggerItem key={archetype.name}>
                    <div className="card-surface p-4 h-full transition-all duration-300 hover:glow-gold hover:-translate-y-1">
                      <div className="text-2xl mb-2" aria-hidden="true">
                        {archetype.icon}
                      </div>
                      <h3 className="font-display font-medium text-sm text-primary">
                        {archetype.name}
                      </h3>
                      <p className="font-body text-text/40 text-xs mt-1">
                        {archetype.description}
                      </p>
                    </div>
                  </MotionStaggerItem>
                ))}
              </MotionStagger>
            </section>

            {/* ── 90-Day Activation Plan ───────────────────────────────── */}
            <section className="mb-12" aria-labelledby="plan-heading">
              <MotionReveal delay={0.05}>
                <h2 id="plan-heading" className="section-heading-sm mb-2">
                  90-Day Activation Plan
                </h2>
                <hr className="rule-gold my-5 max-w-[60px]" />
              </MotionReveal>

              <MotionReveal delay={0.12}>
                <div className="card-surface-elevated p-6">
                  <div className="flex items-start justify-between mb-6">
                    <div>
                      <h3 className="font-display text-lg font-light text-text">
                        Your Personalized Roadmap
                      </h3>
                      <p className="font-body text-sm text-text/50 mt-1">
                        Three-phase wealth-building activation plan
                      </p>
                    </div>
                    <span className="px-3 py-1 rounded-full font-body text-[0.7rem] font-medium tracking-wider uppercase bg-primary/20 text-primary">
                      Phase 2
                    </span>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between font-body text-sm mb-1.5">
                        <span className="text-text/60">
                          Phase 1: Foundation (Days 1–30)
                        </span>
                        <span className="text-primary font-medium">EARN</span>
                      </div>
                      <ProgressBar
                        value={100}
                        variant="gold"
                        size="sm"
                        aria-label="Phase 1 Foundation: 100% complete"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between font-body text-sm mb-1.5">
                        <span className="text-text/60">
                          Phase 2: Building (Days 31–60)
                        </span>
                        <span className="text-secondary font-medium">KEEP</span>
                      </div>
                      <ProgressBar
                        value={60}
                        variant="purple"
                        size="sm"
                        aria-label="Phase 2 Building: 60% complete"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between font-body text-sm mb-1.5">
                        <span className="text-text/60">
                          Phase 3: Acceleration (Days 61–90)
                        </span>
                        <span className="text-accent font-medium">GROW</span>
                      </div>
                      <ProgressBar
                        value={20}
                        variant="teal"
                        size="sm"
                        aria-label="Phase 3 Acceleration: 20% complete"
                      />
                    </div>
                  </div>
                </div>
              </MotionReveal>
            </section>

            {/* ── Methodology Panel ────────────────────────────────────── */}
            <section className="mb-12">
              <MotionReveal delay={0.05}>
                <MethodologyPanel
                  title="Wealth Engine"
                  methodology="All financial calculations in the Wealth Engine use deterministic mathematical formulas. Debt payoff uses the avalanche method (highest interest first) or snowball method (lowest balance first) with standard amortization formulas. Compound growth projections use the formula A = P(1 + r/n)^(nt). Wealth archetype mapping is derived from numerology Life Path numbers cross-referenced with Jungian archetype theory. No financial data is ever sent to an LLM."
                  evidenceLevel="strong"
                  calculationType="deterministic"
                  sources={[
                    "Standard amortization and compound interest formulas (mathematical constants)",
                    'Avalanche vs. Snowball debt payoff methods - Gathergood (2012) "Self-control, financial literacy and consumer over-indebtedness"',
                    "Five Wealth Levers framework adapted from Kiyosaki, Ramsey, and Sethi personal finance methodologies",
                    "Financial data classification: Sensitive (encrypted, isolated, never sent to LLM) per ADR-002",
                  ]}
                />
              </MotionReveal>
            </section>

            {/* ── CTA ─────────────────────────────────────────────────── */}
            <MotionReveal delay={0.05}>
              <div className="text-center">
                <Link href="/discover/intake">
                  <Button variant="primary" size="lg">
                    {hasIntake
                      ? "Update Your Wealth Profile"
                      : "Discover Your Wealth Archetype"}
                  </Button>
                </Link>
              </div>
            </MotionReveal>
          </div>
        </main>
      </MotionReveal>
    </div>
  );
}
