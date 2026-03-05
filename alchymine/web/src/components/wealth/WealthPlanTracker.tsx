"use client";

import { useState, useEffect, useCallback } from "react";
import ProgressBar from "@/components/shared/ProgressBar";
import type { WealthPlanResponse } from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────

function getPlanDay(planStartKey: string): number {
  if (typeof window === "undefined") return 1;
  const stored = localStorage.getItem(planStartKey);
  if (!stored) {
    // First visit — record today as day 1
    localStorage.setItem(planStartKey, String(Date.now()));
    return 1;
  }
  const msPerDay = 1000 * 60 * 60 * 24;
  const elapsed = Math.floor((Date.now() - Number(stored)) / msPerDay);
  return Math.min(elapsed + 1, 90);
}

function getCheckedHabits(storageKey: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(storageKey);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveCheckedHabits(storageKey: string, checked: Set<string>): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(storageKey, JSON.stringify([...checked]));
}

function isWeeklyReviewDay(day: number): boolean {
  return day > 0 && day % 7 === 0;
}

const PHASE_COLORS: Record<
  number,
  { variant: "gold" | "purple" | "teal"; text: string; badge: string }
> = {
  0: {
    variant: "gold",
    text: "text-primary",
    badge: "bg-primary/20 text-primary",
  },
  1: {
    variant: "purple",
    text: "text-secondary",
    badge: "bg-secondary/20 text-secondary",
  },
  2: {
    variant: "teal",
    text: "text-accent",
    badge: "bg-accent/20 text-accent",
  },
};

// ── Demo plan used when API has no data ────────────────────────────

const DEMO_PLAN: WealthPlanResponse = {
  wealth_archetype: "The Builder",
  phases: [
    {
      name: "Foundation",
      days: [1, 30],
      focus_lever: "EARN",
      actions: [
        "Audit all income sources",
        "Calculate your hourly rate",
        "Identify one salary negotiation opportunity",
      ],
      milestones: ["Income audit complete", "Rate established"],
    },
    {
      name: "Building",
      days: [31, 60],
      focus_lever: "KEEP",
      actions: [
        "Create a zero-based budget",
        "Automate savings transfers",
        "Eliminate highest-interest debt first",
      ],
      milestones: ["Budget live", "Auto-save active"],
    },
    {
      name: "Acceleration",
      days: [61, 90],
      focus_lever: "GROW",
      actions: [
        "Open or increase investment account",
        "Review index fund allocation",
        "Set 1-year wealth milestone",
      ],
      milestones: ["Investments active", "12-month goal set"],
    },
  ],
  daily_habits: [
    "Review your spending from yesterday",
    "Track one wealth metric",
    "Read 10 minutes of financial content",
  ],
  weekly_reviews: [
    "Review budget vs. actual spending",
    "Assess progress toward debt payoff",
    "Reflect on wealth mindset shifts",
  ],
};

const WEEKLY_PROMPTS = [
  "What financial win did you have this week, no matter how small?",
  "Where did unexpected spending occur? What can you do differently?",
  "Are you on track with your top wealth lever? What would accelerate it?",
  "What one habit would make the biggest difference in the next 7 days?",
];

// ── Main Component ─────────────────────────────────────────────────

interface WealthPlanTrackerProps {
  plan?: WealthPlanResponse | null;
  storagePrefix?: string;
}

export default function WealthPlanTracker({
  plan,
  storagePrefix = "alchymine_wealthplan",
}: WealthPlanTrackerProps) {
  const activePlan = plan ?? DEMO_PLAN;

  const [currentDay, setCurrentDay] = useState(1);
  const [checkedHabits, setCheckedHabits] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);

  const planStartKey = `${storagePrefix}_start`;
  const habitsKey = `${storagePrefix}_habits`;

  useEffect(() => {
    setCurrentDay(getPlanDay(planStartKey));
    setCheckedHabits(getCheckedHabits(habitsKey));
    setMounted(true);
  }, [planStartKey, habitsKey]);

  const toggleHabit = useCallback(
    (habitKey: string) => {
      setCheckedHabits((prev) => {
        const next = new Set(prev);
        if (next.has(habitKey)) {
          next.delete(habitKey);
        } else {
          next.add(habitKey);
        }
        saveCheckedHabits(habitsKey, next);
        return next;
      });
    },
    [habitsKey],
  );

  // Determine which phase is active
  const activePhaseIdx = activePlan.phases.findIndex(
    (p) => currentDay >= p.days[0] && currentDay <= p.days[1],
  );
  const activePhase = activePlan.phases[activePhaseIdx] ?? activePlan.phases[0];

  const overallProgress = Math.round((currentDay / 90) * 100);

  const showWeeklyReview = mounted && isWeeklyReviewDay(currentDay);
  const weekNumber = Math.floor(currentDay / 7);
  const weeklyPrompt = WEEKLY_PROMPTS[weekNumber % WEEKLY_PROMPTS.length];

  // Habits for today — use daily_habits from plan, keyed by today's date
  const today = mounted ? new Date().toISOString().split("T")[0] : "0000-00-00";

  return (
    <div data-testid="wealth-plan-tracker">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display text-lg font-medium text-text">
          90-Day Activation Plan
        </h3>
        <span className="font-body text-xs text-text/40 px-3 py-1 bg-white/5 rounded-full">
          Day {currentDay} of 90
        </span>
      </div>

      {/* Overall progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between font-body text-xs text-text/40 mb-2">
          <span>Overall progress</span>
          <span>{overallProgress}%</span>
        </div>
        <ProgressBar
          value={overallProgress}
          variant="gold"
          size="sm"
          aria-label={`Overall plan progress: ${overallProgress}%`}
        />
      </div>

      {/* Phase progress bars */}
      <div className="space-y-4 mb-6">
        {activePlan.phases.map((phase, idx) => {
          const colors = PHASE_COLORS[idx] ?? PHASE_COLORS[0];
          const isActive = idx === activePhaseIdx;

          // Calculate phase progress
          let phaseProgress = 0;
          if (currentDay > phase.days[1]) {
            phaseProgress = 100;
          } else if (currentDay >= phase.days[0]) {
            const daysIn = currentDay - phase.days[0] + 1;
            const totalDays = phase.days[1] - phase.days[0] + 1;
            phaseProgress = Math.round((daysIn / totalDays) * 100);
          }

          return (
            <div key={phase.name}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-body text-sm text-text/60">
                    Phase {idx + 1}: {phase.name} (Days {phase.days[0]}–
                    {phase.days[1]})
                  </span>
                  {isActive && (
                    <span
                      className={`px-2 py-0.5 rounded-full font-body text-[10px] font-medium ${colors.badge}`}
                    >
                      Active
                    </span>
                  )}
                </div>
                <span
                  className={`font-body text-xs font-medium ${colors.text}`}
                >
                  {phase.focus_lever}
                </span>
              </div>
              <ProgressBar
                value={phaseProgress}
                variant={colors.variant}
                size="sm"
                aria-label={`Phase ${idx + 1} ${phase.name}: ${phaseProgress}% complete`}
              />
            </div>
          );
        })}
      </div>

      {/* Weekly review prompt */}
      {showWeeklyReview && (
        <div className="mb-6 p-4 bg-secondary/[0.08] border border-secondary/20 rounded-xl">
          <div className="flex items-start gap-3">
            <span className="text-lg mt-0.5" aria-hidden="true">
              {"\u{1F4DD}"}
            </span>
            <div>
              <h4 className="font-display text-sm font-medium text-secondary mb-1">
                Week {weekNumber} Review
              </h4>
              <p className="font-body text-sm text-text/60">{weeklyPrompt}</p>
            </div>
          </div>
        </div>
      )}

      {/* Daily habits */}
      <div className="mb-5">
        <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-3">
          Today&apos;s Habits
        </h4>
        <div className="space-y-2">
          {activePlan.daily_habits.map((habit, idx) => {
            const habitKey = `${today}-habit-${idx}`;
            const isChecked = checkedHabits.has(habitKey);
            return (
              <label
                key={habitKey}
                className="flex items-center gap-3 cursor-pointer group"
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleHabit(habitKey)}
                  className="sr-only"
                  aria-label={habit}
                />
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center border transition-all flex-shrink-0 ${
                    isChecked
                      ? "bg-primary border-primary"
                      : "border-white/20 group-hover:border-primary/40"
                  }`}
                  aria-hidden="true"
                >
                  {isChecked && (
                    <svg
                      className="w-3 h-3 text-black"
                      viewBox="0 0 12 12"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        d="M10 3L4.5 8.5 2 6"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>
                <span
                  className={`font-body text-sm transition-colors ${
                    isChecked ? "text-text/30 line-through" : "text-text/70"
                  }`}
                >
                  {habit}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Active phase actions */}
      {activePhase && (
        <div className="pt-4 border-t border-white/5">
          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-3">
            Phase {activePhaseIdx + 1} Actions
          </h4>
          <div className="space-y-2">
            {activePhase.actions.map((action) => (
              <div key={action} className="flex items-center gap-2 text-sm">
                <span
                  className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0"
                  aria-hidden="true"
                />
                <span className="font-body text-text/60">{action}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
