"use client";

import { useState } from "react";
import Link from "next/link";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useApi, getStoredIntake } from "@/lib/useApi";
import {
  getOutcomeSummary,
  getJournalStats,
  OutcomeSummary,
  JournalStatsResponse,
} from "@/lib/api";

// ─── Helper components ──────────────────────────────────────────────

function ProgressRing({
  value,
  label,
  size = 80,
}: {
  value: number;
  label: string;
  size?: number;
}) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#gold-gradient)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000"
        />
        <defs>
          <linearGradient id="gold-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#c4a04a" />
            <stop offset="100%" stopColor="#d4b45a" />
          </linearGradient>
        </defs>
      </svg>
      <div className="text-center -mt-14">
        <div className="text-xl font-bold text-gradient-gold">
          {Math.round(value)}
        </div>
      </div>
      <div className="text-xs text-text/50 mt-4">{label}</div>
    </div>
  );
}

function SystemCard({
  system,
  engagement,
  milestonesCompleted,
  milestonesTotal,
  activeDays,
}: {
  system: string;
  engagement: number;
  milestonesCompleted: number;
  milestonesTotal: number;
  activeDays: number;
}) {
  const systemLabels: Record<string, string> = {
    identity: "Personal Intelligence",
    healing: "Ethical Healing",
    wealth: "Generational Wealth",
    creative: "Creative Forge",
    perspective: "Perspective Prism",
  };

  const systemColors: Record<string, string> = {
    identity: "text-primary",
    healing: "text-green-400",
    wealth: "text-yellow-400",
    creative: "text-purple-400",
    perspective: "text-blue-400",
  };

  return (
    <div className="bg-surface/50 border border-white/5 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h4
          className={`font-semibold capitalize ${systemColors[system] || "text-text"}`}
        >
          {systemLabels[system] || system}
        </h4>
        <span className="text-xs text-text/40">{activeDays} active days</span>
      </div>

      {/* Engagement bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-xs text-text/50 mb-1">
          <span>Engagement</span>
          <span>{Math.round(engagement)}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-700"
            style={{ width: `${engagement}%` }}
          />
        </div>
      </div>

      {/* Milestones */}
      <div className="flex items-center justify-between text-xs text-text/50">
        <span>Milestones</span>
        <span>
          {milestonesCompleted}/{milestonesTotal}
        </span>
      </div>
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────

export default function DashboardPage() {
  const intake = getStoredIntake();
  const userId = intake ? "current-user" : null;
  const [activeTab, setActiveTab] = useState<"overview" | "journal">(
    "overview",
  );

  const outcomes = useApi<OutcomeSummary>(
    () =>
      userId ? getOutcomeSummary(userId) : Promise.reject(new Error("No user")),
    [userId],
  );

  const journalStats = useApi<JournalStatsResponse>(
    () =>
      userId ? getJournalStats(userId) : Promise.reject(new Error("No user")),
    [userId],
  );

  if (!intake) {
    return (
      <div className="flex-1 px-6 py-12">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm uppercase tracking-[0.2em] text-primary mb-3">
            Dashboard
          </p>
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-gradient-gold">Your Progress</span>
          </h1>
          <p className="text-text/50 max-w-xl mx-auto mb-8">
            Complete your intake assessment to start tracking your journey
            across all five Alchymine systems.
          </p>
          <Link href="/discover/intake">
            <Button>Start Your Journey</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
    <div className="flex-1 px-6 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <p className="text-sm uppercase tracking-[0.2em] text-primary mb-3">
            Dashboard
          </p>
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">
            <span className="text-gradient-gold">Progress Tracker</span>
          </h1>
          <p className="text-text/50">
            Your journey across all five Alchymine systems
          </p>
        </div>

        {/* Tab navigation */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "overview"
                ? "bg-primary/20 text-primary border border-primary/30"
                : "text-text/50 hover:text-text/70"
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab("journal")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === "journal"
                ? "bg-primary/20 text-primary border border-primary/30"
                : "text-text/50 hover:text-text/70"
            }`}
          >
            Journal Stats
          </button>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Overall Score */}
            <Card title="Overall Progress">
              {outcomes.loading ? (
                <div className="flex justify-center py-6">
                  <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                </div>
              ) : outcomes.error ? (
                <div className="text-center py-8">
                  <p className="text-text/50 mb-2">
                    No outcome data yet — start using the systems!
                  </p>
                  <p className="text-xs text-text/30">
                    Your progress will appear here as you complete milestones
                    and engage with the platform.
                  </p>
                </div>
              ) : outcomes.data ? (
                <div>
                  <div className="flex items-center justify-center mb-6">
                    <ProgressRing
                      value={outcomes.data.overall_score}
                      label="Overall Score"
                      size={100}
                    />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {outcomes.data.completed_milestones}
                      </div>
                      <div className="text-xs text-text/50">
                        Milestones Complete
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {outcomes.data.total_milestones}
                      </div>
                      <div className="text-xs text-text/50">
                        Total Milestones
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {outcomes.data.systems.length}
                      </div>
                      <div className="text-xs text-text/50">Systems Active</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {outcomes.data.active_plan_day ?? "—"}
                      </div>
                      <div className="text-xs text-text/50">Plan Day</div>
                    </div>
                  </div>
                </div>
              ) : null}
            </Card>

            {/* Per-system progress */}
            {outcomes.data && outcomes.data.systems.length > 0 && (
              <Card
                title="System Progress"
                subtitle="Engagement and milestones per system"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {outcomes.data.systems.map((sys) => (
                    <SystemCard
                      key={sys.system}
                      system={sys.system}
                      engagement={sys.engagement_score}
                      milestonesCompleted={sys.milestones_completed}
                      milestonesTotal={sys.milestones_total}
                      activeDays={sys.active_days}
                    />
                  ))}
                </div>
              </Card>
            )}

            {/* Quick actions */}
            <Card title="Quick Actions">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Link href="/healing">
                  <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center hover:bg-green-500/15 transition cursor-pointer">
                    <div className="text-green-400 font-medium">Healing</div>
                    <div className="text-xs text-text/40 mt-1">
                      Start a practice session
                    </div>
                  </div>
                </Link>
                <Link href="/wealth">
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-center hover:bg-yellow-500/15 transition cursor-pointer">
                    <div className="text-yellow-400 font-medium">Wealth</div>
                    <div className="text-xs text-text/40 mt-1">
                      Review your plan
                    </div>
                  </div>
                </Link>
                <Link href="/creative">
                  <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4 text-center hover:bg-purple-500/15 transition cursor-pointer">
                    <div className="text-purple-400 font-medium">Creative</div>
                    <div className="text-xs text-text/40 mt-1">
                      Explore your style
                    </div>
                  </div>
                </Link>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "journal" && (
          <div className="space-y-6">
            <Card title="Journal Overview">
              {journalStats.loading ? (
                <div className="flex justify-center py-6">
                  <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                </div>
              ) : journalStats.error ? (
                <div className="text-center py-8">
                  <p className="text-text/50 mb-2">
                    No journal entries yet — start writing!
                  </p>
                  <p className="text-xs text-text/30">
                    Journal entries help track your reflections, reframes, and
                    progress across all systems.
                  </p>
                </div>
              ) : journalStats.data ? (
                <div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center mb-6">
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {journalStats.data.total_entries}
                      </div>
                      <div className="text-xs text-text/50">Total Entries</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {journalStats.data.streak_days}
                      </div>
                      <div className="text-xs text-text/50">Day Streak</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {journalStats.data.average_mood
                          ? journalStats.data.average_mood.toFixed(1)
                          : "—"}
                      </div>
                      <div className="text-xs text-text/50">Avg Mood</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-primary">
                        {journalStats.data.tags_used.length}
                      </div>
                      <div className="text-xs text-text/50">Tags Used</div>
                    </div>
                  </div>

                  {/* Entries by system */}
                  {Object.keys(journalStats.data.entries_by_system).length >
                    0 && (
                    <div className="mb-4">
                      <h4 className="text-sm text-text/50 mb-2">By System</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(
                          journalStats.data.entries_by_system,
                        ).map(([sys, count]) => (
                          <span
                            key={sys}
                            className="px-3 py-1 bg-primary/10 border border-primary/20 rounded-full text-xs text-primary"
                          >
                            {sys}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Entries by type */}
                  {Object.keys(journalStats.data.entries_by_type).length >
                    0 && (
                    <div className="mb-4">
                      <h4 className="text-sm text-text/50 mb-2">By Type</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(journalStats.data.entries_by_type).map(
                          ([type, count]) => (
                            <span
                              key={type}
                              className="px-3 py-1 bg-secondary/10 border border-secondary/20 rounded-full text-xs text-secondary"
                            >
                              {type}: {count}
                            </span>
                          ),
                        )}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {journalStats.data.tags_used.length > 0 && (
                    <div>
                      <h4 className="text-sm text-text/50 mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-2">
                        {journalStats.data.tags_used.map((tag) => (
                          <span
                            key={tag}
                            className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-text/60"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </Card>
          </div>
        )}
      </div>
    </div>
    </ProtectedRoute>
  );
}
