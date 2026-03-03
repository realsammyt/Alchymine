"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import Button from "@/components/shared/Button";
import Card from "@/components/shared/Card";
import ProgressBar from "@/components/shared/ProgressBar";
import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
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
    { name: "Housing", amount: 1600, color: "#6366f1" },
    { name: "Food", amount: 650, color: "#10b981" },
    { name: "Transport", amount: 350, color: "#f59e0b" },
    { name: "Debt Payments", amount: 850, color: "#ef4444" },
    { name: "Savings", amount: 700, color: "#22c55e" },
    { name: "Utilities", amount: 280, color: "#8b5cf6" },
    { name: "Other", amount: 370, color: "#6b7280" },
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
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Debt Payoff Timeline</h3>
        <span className="text-xs text-text/40 px-3 py-1 bg-white/5 rounded-full">
          Avalanche Method (highest rate first)
        </span>
      </div>
      <div className="space-y-4">
        {sorted.map((debt) => {
          const paidPct = ((debt.total - debt.balance) / debt.total) * 100;
          const timelinePct = (debt.monthsRemaining / maxMonths) * 100;
          return (
            <div key={debt.name}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text/80">
                    {debt.name}
                  </span>
                  <span className="text-xs text-red-400/70">
                    {debt.rate}% APR
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-text/40">
                    {debt.monthsRemaining} mo left
                  </span>
                  <span className="text-sm font-medium text-primary">
                    {formatCurrency(debt.balance)}
                  </span>
                </div>
              </div>
              {/* Payoff progress bar */}
              <div className="h-3 bg-surface rounded-full overflow-hidden relative">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-green-600 to-green-400 transition-all duration-700"
                  style={{ width: `${paidPct}%` }}
                />
                {/* Remaining portion indicator */}
                <div
                  className="absolute top-0 h-full bg-red-500/20 rounded-r-full"
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
      <div className="mt-4 flex items-center justify-between text-xs text-text/40">
        <span>
          Total remaining:{" "}
          {formatCurrency(debts.reduce((sum, d) => sum + d.balance, 0))}
        </span>
        <span>
          Paid off:{" "}
          {formatCurrency(
            debts.reduce((sum, d) => sum + (d.total - d.balance), 0),
          )}
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
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Budget Breakdown</h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text/40">Monthly Income:</span>
          <span className="text-sm font-bold text-primary">
            {formatCurrency(income)}
          </span>
        </div>
      </div>

      {/* Stacked bar */}
      <div
        className="h-8 rounded-full overflow-hidden flex mb-4"
        role="img"
        aria-label="Budget allocation bar"
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
              backgroundColor: "#374151",
            }}
          />
        )}
      </div>

      {/* Category breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {categories.map((cat) => {
          const pct = (cat.amount / income) * 100;
          return (
            <div key={cat.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: cat.color }}
              />
              <div className="min-w-0">
                <div className="text-xs text-text/60 truncate">{cat.name}</div>
                <div className="text-xs font-medium text-text/80">
                  {formatCurrency(cat.amount)}{" "}
                  <span className="text-text/40">({pct.toFixed(0)}%)</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Savings rate highlight */}
      <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-green-400 text-lg">{"\u{1F4B0}"}</span>
          <span className="text-sm text-text/60">Savings Rate</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-24 h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-green-400 transition-all duration-500"
              style={{ width: `${Math.min(savingsRate, 100)}%` }}
            />
          </div>
          <span className="text-sm font-bold text-green-400">
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

  return (
    <div data-testid="net-worth-tracker">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Net Worth Summary</h3>
        <div className="text-right">
          <div className="text-xs text-text/40">Net Worth</div>
          <div
            className={`text-xl font-bold ${netWorth >= 0 ? "text-green-400" : "text-red-400"}`}
          >
            {formatCurrency(netWorth)}
          </div>
        </div>
      </div>

      {/* Visual comparison bars */}
      <div className="space-y-3 mb-4">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-green-400/80">Assets</span>
            <span className="text-text/60">{formatCurrency(totalAssets)}</span>
          </div>
          <div className="h-6 bg-surface rounded-lg overflow-hidden">
            <div
              className="h-full rounded-lg bg-gradient-to-r from-green-600/60 to-green-400/60 transition-all duration-700 flex items-center px-2"
              style={{ width: `${(totalAssets / maxValue) * 100}%` }}
            >
              <span className="text-[10px] text-white/70 font-medium whitespace-nowrap">
                {formatCurrency(totalAssets)}
              </span>
            </div>
          </div>
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-red-400/80">Liabilities</span>
            <span className="text-text/60">
              {formatCurrency(totalLiabilities)}
            </span>
          </div>
          <div className="h-6 bg-surface rounded-lg overflow-hidden">
            <div
              className="h-full rounded-lg bg-gradient-to-r from-red-600/60 to-red-400/60 transition-all duration-700 flex items-center px-2"
              style={{ width: `${(totalLiabilities / maxValue) * 100}%` }}
            >
              <span className="text-[10px] text-white/70 font-medium whitespace-nowrap">
                {formatCurrency(totalLiabilities)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown grid */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs uppercase tracking-wider text-text/40 mb-2">
            Assets
          </h4>
          <div className="space-y-2">
            {assets.map((a) => (
              <div
                key={a.name}
                className="flex justify-between items-center text-sm"
              >
                <span className="text-text/60">{a.name}</span>
                <span className="text-green-400/80 font-medium">
                  {formatCurrency(a.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h4 className="text-xs uppercase tracking-wider text-text/40 mb-2">
            Liabilities
          </h4>
          <div className="space-y-2">
            {liabilities.map((l) => (
              <div
                key={l.name}
                className="flex justify-between items-center text-sm"
              >
                <span className="text-text/60">{l.name}</span>
                <span className="text-red-400/80 font-medium">
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
  const leverColors = ["#f59e0b", "#6366f1", "#10b981", "#ec4899", "#8b5cf6"];

  return (
    <div data-testid="lever-priority">
      <h3 className="text-lg font-semibold mb-4">Your Lever Priority</h3>
      <div className="flex flex-col gap-3">
        {levers.map((lever, i) => {
          const leverData = WEALTH_LEVERS.find((l) => l.name === lever);
          const barWidth = 100 - i * 15;
          const color = leverColors[i] || "#6b7280";
          return (
            <div key={lever} className="flex items-center gap-3">
              <div
                className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                style={{ background: `${color}22`, color }}
              >
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{leverData?.icon}</span>
                    <span className="text-sm font-medium text-text/80">
                      {lever}
                    </span>
                  </div>
                  <span className="text-xs text-text/40">
                    {i === 0 ? "Top Priority" : `Priority ${i + 1}`}
                  </span>
                </div>
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${barWidth}%`,
                      background: `linear-gradient(90deg, ${color}88, ${color})`,
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
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Generational Wealth</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Five-lever generational wealth strategy. All calculations are
            deterministic — no AI guesswork with your finances.
          </p>
          <div className="mt-4 inline-block bg-surface/50 border border-primary/20 rounded-full px-4 py-2">
            <span className="text-xs text-text/40">
              Not financial advice. All strategies require professional review.
            </span>
          </div>
        </header>

        {/* Personalized Wealth Profile */}
        {hasIntake && (
          <section className="mb-12" aria-labelledby="your-wealth-heading">
            <h2
              id="your-wealth-heading"
              className="text-2xl font-bold mb-6 flex items-center gap-3"
            >
              <span
                className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{2728}"}
              </span>
              Your Wealth Profile
            </h2>
            <ApiStateView
              loading={wealthProfile.loading}
              error={wealthProfile.error}
              empty={!wealthProfile.data}
              loadingText="Analyzing your wealth archetype..."
              emptyText="Complete the full assessment to discover your wealth archetype and personalized strategies."
              onRetry={wealthProfile.refetch}
            >
              {wealthProfile.data && (
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
                      <h3 className="text-xl font-bold text-primary">
                        {wealthProfile.data.wealth_archetype}
                      </h3>
                      <p className="text-sm text-text/50">
                        {wealthProfile.data.description}
                      </p>
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                    <div>
                      <h4 className="text-xs uppercase tracking-wider text-text/40 mb-2">
                        Strengths
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {wealthProfile.data.strengths.map((s) => (
                          <span
                            key={s}
                            className="px-3 py-1 bg-primary/10 text-primary text-xs rounded-full"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs uppercase tracking-wider text-text/40 mb-2">
                        Blind Spots
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {wealthProfile.data.blind_spots.map((b) => (
                          <span
                            key={b}
                            className="px-3 py-1 bg-white/5 text-text/50 text-xs rounded-full"
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
              )}
            </ApiStateView>
          </section>
        )}

        {/* Financial Dashboard Cards */}
        <section
          className="mb-12"
          aria-labelledby="financial-dashboard-heading"
        >
          <h2
            id="financial-dashboard-heading"
            className="text-2xl font-bold mb-6 flex items-center gap-3"
          >
            <span
              className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
              aria-hidden="true"
            >
              {"\u{1F4CA}"}
            </span>
            Financial Dashboard
          </h2>
          <p className="text-text/50 text-sm mb-6">
            Sample visualizations showing how your financial data will be
            displayed. All calculations use standard deterministic formulas.
          </p>

          <div className="space-y-6">
            {/* Debt Payoff Timeline */}
            <Card title="">
              <DebtPayoffTimeline debts={DEMO_DEBTS} />
            </Card>

            {/* Budget Breakdown */}
            <Card title="">
              <BudgetBreakdown
                income={DEMO_BUDGET.income}
                categories={DEMO_BUDGET.categories}
              />
            </Card>

            {/* Net Worth Tracker */}
            <Card title="">
              <NetWorthTracker
                assets={DEMO_NET_WORTH.assets}
                liabilities={DEMO_NET_WORTH.liabilities}
              />
            </Card>
          </div>
        </section>

        {/* Five Wealth Levers */}
        <section className="mb-12" aria-labelledby="levers-heading">
          <h2 id="levers-heading" className="text-2xl font-bold mb-6">
            Five Wealth Levers
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            {WEALTH_LEVERS.map((lever) => (
              <button
                key={lever.name}
                onClick={() =>
                  setSelectedLever(
                    selectedLever === lever.name ? null : lever.name,
                  )
                }
                aria-pressed={selectedLever === lever.name}
                className={`card-surface p-4 text-left transition-all ${
                  selectedLever === lever.name
                    ? "glow-gold ring-1 ring-primary/30"
                    : "hover:glow-gold"
                }`}
              >
                <div className="text-3xl mb-2" aria-hidden="true">
                  {lever.icon}
                </div>
                <h3 className="font-bold text-sm mb-1">{lever.name}</h3>
                <p className="text-text/40 text-xs">{lever.description}</p>
              </button>
            ))}
          </div>

          {selectedLever && (
            <div className="card-surface p-6 mb-6 animate-fade-in">
              <h3 className="text-xl font-bold text-primary mb-4">
                {WEALTH_LEVERS.find((l) => l.name === selectedLever)?.icon}{" "}
                {selectedLever} Strategies
              </h3>
              <div className="grid sm:grid-cols-2 gap-3">
                {WEALTH_LEVERS.find(
                  (l) => l.name === selectedLever,
                )?.examples.map((ex) => (
                  <div
                    key={ex}
                    className="flex items-center gap-2 text-text/70 text-sm"
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
          )}
        </section>

        {/* Wealth Archetypes Preview */}
        <section className="mb-12" aria-labelledby="archetypes-heading">
          <h2 id="archetypes-heading" className="text-2xl font-bold mb-3">
            Wealth Archetypes
          </h2>
          <p className="text-text/50 mb-6 text-sm">
            Your wealth archetype is derived from your numerology Life Path and
            Jungian archetype. Complete your profile to discover yours.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {WEALTH_ARCHETYPES_PREVIEW.map((archetype) => (
              <div key={archetype.name} className="card-surface p-4">
                <div className="text-2xl mb-2" aria-hidden="true">
                  {archetype.icon}
                </div>
                <h3 className="font-semibold text-sm text-primary">
                  {archetype.name}
                </h3>
                <p className="text-text/40 text-xs mt-1">
                  {archetype.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* 90-Day Plan Section */}
        <section className="mb-12" aria-labelledby="plan-heading">
          <h2 id="plan-heading" className="text-2xl font-bold mb-6">
            90-Day Activation Plan
          </h2>
          <Card
            title="Your Personalized Roadmap"
            subtitle="Three-phase wealth-building activation plan"
            badge="Phase 2"
          >
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text/60">
                    Phase 1: Foundation (Days 1-30)
                  </span>
                  <span className="text-primary">EARN</span>
                </div>
                <ProgressBar value={100} variant="gold" size="sm" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text/60">
                    Phase 2: Building (Days 31-60)
                  </span>
                  <span className="text-secondary">KEEP</span>
                </div>
                <ProgressBar value={60} variant="purple" size="sm" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-text/60">
                    Phase 3: Acceleration (Days 61-90)
                  </span>
                  <span className="text-accent">GROW</span>
                </div>
                <ProgressBar value={20} variant="teal" size="sm" />
              </div>
            </div>
          </Card>
        </section>

        {/* Methodology Panel */}
        <section className="mb-12">
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
        </section>

        {/* CTA */}
        <div className="text-center">
          <Link href="/discover/intake">
            <Button variant="primary" size="lg">
              {hasIntake
                ? "Update Your Wealth Profile"
                : "Discover Your Wealth Archetype"}
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
