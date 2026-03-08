"use client";

import { useId, useState } from "react";
import Link from "next/link";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useApi, useIntake } from "@/lib/useApi";
import { useAuth } from "@/lib/AuthContext";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  getOutcomeSummary,
  getJournalStats,
  synthesizeCrossSystems,
  OutcomeSummary,
  JournalStatsResponse,
  BridgeInsightResponse,
} from "@/lib/api";
import QualityGateDisplay from "@/components/shared/QualityGateDisplay";

// ─── System accent config ────────────────────────────────────────────

type SystemKey = "identity" | "healing" | "wealth" | "creative" | "perspective";

const SYSTEM_CONFIG: Record<
  SystemKey,
  {
    label: string;
    accentText: string;
    accentBg: string;
    accentBorder: string;
    progressGradient: string;
    glow: string;
  }
> = {
  identity: {
    label: "Personal Intelligence",
    accentText: "text-primary",
    accentBg: "bg-primary/10",
    accentBorder: "border-primary/20",
    progressGradient: "from-primary-dark to-primary-light",
    glow: "hover:glow-gold",
  },
  healing: {
    label: "Ethical Healing",
    accentText: "text-accent",
    accentBg: "bg-accent/10",
    accentBorder: "border-accent/20",
    progressGradient: "from-accent-dark to-accent-light",
    glow: "hover:glow-teal",
  },
  wealth: {
    label: "Generational Wealth",
    accentText: "text-primary",
    accentBg: "bg-primary/10",
    accentBorder: "border-primary/20",
    progressGradient: "from-primary-dark to-primary-light",
    glow: "hover:glow-gold",
  },
  creative: {
    label: "Creative Forge",
    accentText: "text-secondary-light",
    accentBg: "bg-secondary/10",
    accentBorder: "border-secondary/20",
    progressGradient: "from-secondary-dark to-secondary-light",
    glow: "hover:glow-purple",
  },
  perspective: {
    label: "Perspective Prism",
    accentText: "text-accent",
    accentBg: "bg-accent/10",
    accentBorder: "border-accent/20",
    progressGradient: "from-accent-dark to-accent-light",
    glow: "hover:glow-teal",
  },
};

function getSystemConfig(system: string) {
  return (
    SYSTEM_CONFIG[system as SystemKey] ?? {
      label: system,
      accentText: "text-primary",
      accentBg: "bg-primary/10",
      accentBorder: "border-primary/20",
      progressGradient: "from-primary-dark to-primary-light",
      glow: "hover:glow-gold",
    }
  );
}

// ─── Helper components ───────────────────────────────────────────────

function Spinner() {
  return (
    <div
      className="flex justify-center py-8"
      role="status"
      aria-label="Loading"
    >
      <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
    </div>
  );
}

function StatBlock({
  value,
  label,
}: {
  value: string | number;
  label: string;
}) {
  return (
    <div className="text-center">
      <div className="font-display text-2xl sm:text-3xl font-light text-gradient-gold leading-none mb-1">
        {value}
      </div>
      <div className="text-xs font-body text-text/40 tracking-wide">
        {label}
      </div>
    </div>
  );
}

function ProgressRing({
  value,
  label,
  size = 80,
}: {
  value: number;
  label: string;
  size?: number;
}) {
  const gradientId = useId();
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const clampedValue = Math.round(Math.max(0, Math.min(100, value)));

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#B8860B" />
              <stop offset="50%" stopColor="#DAA520" />
              <stop offset="100%" stopColor="#F0C050" />
            </linearGradient>
          </defs>
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="6"
          />
          {/* Progress */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000"
          />
        </svg>
        {/* Center label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-display text-xl font-light text-gradient-gold">
            {clampedValue}
          </span>
        </div>
      </div>
      <div
        className="text-xs font-body text-text/40 tracking-wide"
        aria-label={`${label}: ${clampedValue} out of 100`}
      >
        {label}
      </div>
      {/* Accessible text for screen readers */}
      <span className="sr-only">
        {label}: {clampedValue}%
      </span>
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
  const cfg = getSystemConfig(system);
  const clampedEngagement = Math.round(Math.max(0, Math.min(100, engagement)));

  return (
    <div className={`card-surface p-4 transition-all duration-300 ${cfg.glow}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className={`font-display text-sm font-medium ${cfg.accentText}`}>
          {cfg.label}
        </h3>
        <span className="text-xs font-body text-text/40">
          {activeDays} active {activeDays === 1 ? "day" : "days"}
        </span>
      </div>

      {/* Engagement bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs font-body text-text/40 mb-1.5">
          <span>Engagement</span>
          <span
            aria-valuenow={clampedEngagement}
            aria-valuemax={100}
            aria-label={`Engagement: ${clampedEngagement}%`}
          >
            {clampedEngagement}%
          </span>
        </div>
        <div
          className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden"
          role="progressbar"
          aria-valuenow={clampedEngagement}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${cfg.label} engagement`}
        >
          <div
            className={`h-full rounded-full bg-gradient-to-r ${cfg.progressGradient} transition-all duration-700`}
            style={{ width: `${clampedEngagement}%` }}
          />
        </div>
      </div>

      {/* Milestones */}
      <div className="flex items-center justify-between text-xs font-body text-text/40">
        <span>Milestones</span>
        <span
          aria-label={`${milestonesCompleted} of ${milestonesTotal} milestones completed`}
        >
          {milestonesCompleted}
          <span className="text-text/25">/{milestonesTotal}</span>
        </span>
      </div>
    </div>
  );
}

// ─── Quick action card ───────────────────────────────────────────────

function QuickActionCard({
  href,
  label,
  description,
  accentText,
  accentBg,
  accentBorder,
  icon,
}: {
  href: string;
  label: string;
  description: string;
  accentText: string;
  accentBg: string;
  accentBorder: string;
  icon: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-label={`${label} — ${description}`}
      className={`group block ${accentBg} border ${accentBorder} rounded-xl p-4 text-center transition-all duration-300 hover:-translate-y-0.5 hover:brightness-110 touch-target`}
    >
      <div
        className={`flex justify-center mb-2 ${accentText} opacity-70 group-hover:opacity-100 transition-opacity`}
      >
        {icon}
      </div>
      <div className={`font-display text-sm font-medium ${accentText}`}>
        {label}
      </div>
      <div className="text-xs font-body text-text/40 mt-0.5">{description}</div>
    </Link>
  );
}

// ─── Stat grid ───────────────────────────────────────────────────────

function StatGrid({
  stats,
}: {
  stats: { value: string | number; label: string }[];
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {stats.map((s) => (
        <StatBlock key={s.label} value={s.value} label={s.label} />
      ))}
    </div>
  );
}

// ─── Healing leaf icon ───────────────────────────────────────────────

function IconLeaf() {
  return (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
      <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}

function IconPalette() {
  return (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
    </svg>
  );
}

// ─── Cross-system insight accent config ──────────────────────────────

function insightAccent(bridgeType: string): {
  accentText: string;
  accentBg: string;
  accentBorder: string;
  href: string;
} {
  const map: Record<
    string,
    { accentText: string; accentBg: string; accentBorder: string; href: string }
  > = {
    "archetype-creative": {
      accentText: "text-secondary-light",
      accentBg: "bg-secondary/[0.08]",
      accentBorder: "border-secondary/[0.15]",
      href: "/creative",
    },
    "shadow-block": {
      accentText: "text-secondary-light",
      accentBg: "bg-secondary/[0.08]",
      accentBorder: "border-secondary/[0.15]",
      href: "/creative",
    },
    "cycle-timing": {
      accentText: "text-primary",
      accentBg: "bg-primary/[0.08]",
      accentBorder: "border-primary/[0.15]",
      href: "/wealth",
    },
    "wealth-creative": {
      accentText: "text-primary",
      accentBg: "bg-primary/[0.08]",
      accentBorder: "border-primary/[0.15]",
      href: "/wealth",
    },
    "healing-perspective": {
      accentText: "text-accent",
      accentBg: "bg-accent/[0.08]",
      accentBorder: "border-accent/[0.15]",
      href: "/healing",
    },
  };
  // Fall back by target system
  const byTarget: Record<
    string,
    { accentText: string; accentBg: string; accentBorder: string; href: string }
  > = {
    healing: {
      accentText: "text-accent",
      accentBg: "bg-accent/[0.08]",
      accentBorder: "border-accent/[0.15]",
      href: "/healing",
    },
    perspective: {
      accentText: "text-accent",
      accentBg: "bg-accent/[0.08]",
      accentBorder: "border-accent/[0.15]",
      href: "/perspective",
    },
    wealth: {
      accentText: "text-primary",
      accentBg: "bg-primary/[0.08]",
      accentBorder: "border-primary/[0.15]",
      href: "/wealth",
    },
    creative: {
      accentText: "text-secondary-light",
      accentBg: "bg-secondary/[0.08]",
      accentBorder: "border-secondary/[0.15]",
      href: "/creative",
    },
  };
  return (
    map[bridgeType] ??
    byTarget["healing"] ?? {
      accentText: "text-primary",
      accentBg: "bg-primary/[0.08]",
      accentBorder: "border-primary/[0.15]",
      href: "/dashboard",
    }
  );
}

function insightTitle(bridgeType: string): string {
  const titles: Record<string, string> = {
    "archetype-creative": "Archetype-Creative Connection",
    "shadow-block": "Shadow-Creativity Link",
    "cycle-timing": "Numerology-Wealth Timing",
    "wealth-creative": "Wealth-Creative Alignment",
    "healing-perspective": "Healing-Perspective Sequence",
  };
  return titles[bridgeType] ?? bridgeType;
}

function CrossInsightCard({ insight }: { insight: BridgeInsightResponse }) {
  const accent = insightAccent(insight.bridge_type);
  return (
    <div
      className={`${accent.accentBg} border ${accent.accentBorder} rounded-xl p-4 flex flex-col gap-2`}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className={`font-display text-sm font-medium ${accent.accentText}`}>
          {insightTitle(insight.bridge_type)}
        </h3>
        <span className="font-body text-[10px] text-text/30 flex-shrink-0 mt-0.5">
          {Math.round(insight.confidence * 100)}% confidence
        </span>
      </div>
      <p className="font-body text-xs text-text/60 leading-relaxed flex-1">
        {insight.insight}
      </p>
      {insight.action && (
        <p className="font-body text-xs text-text/40 italic">
          {insight.action}
        </p>
      )}
      <Link
        href={accent.href}
        className={`font-body text-xs ${accent.accentText} underline underline-offset-2 self-start`}
      >
        Explore {accent.href.replace("/", "")} &rarr;
      </Link>
    </div>
  );
}

// ─── Main Dashboard ──────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const { data: intake, loading: intakeLoading } = useIntake(userId);
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

  const crossInsights = useApi<BridgeInsightResponse[]>(
    intake ? () => synthesizeCrossSystems({}) : null,
    [!!intake],
  );

  // Derive a greeting name from email or use generic fallback
  const displayName = user?.email?.split("@")[0] ?? "Alchemist";

  return (
    <ProtectedRoute>
      {/* Page wrapper — grain + atmosphere */}
      <main id="main-content" className="grain-overlay flex-1">
        <div className="bg-atmosphere min-h-full">
          {intakeLoading ? (
            // ── Loading state while fetching server profile ─────────
            <div className="px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
              <div className="max-w-4xl mx-auto flex flex-col items-center gap-4 py-20">
                <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                <p className="text-text/40 font-body text-sm">Loading your profile&hellip;</p>
              </div>
            </div>
          ) : !intake ? (
            // ── Empty state ─────────────────────────────────────────
            <div className="px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
              <div className="max-w-4xl mx-auto space-y-8">
                <MotionReveal delay={0.1} y={16}>
                  <div className="card-surface-elevated glow-gold text-center px-6 py-16 sm:px-12">
                    {/* Decorative orb */}
                    <div
                      className="w-20 h-20 mx-auto mb-8 rounded-full bg-primary/[0.08] border border-primary/[0.15] flex items-center justify-center"
                      aria-hidden="true"
                    >
                      <svg
                        className="w-9 h-9 text-primary/60"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M12 2L2 7l10 5 10-5-10-5z" />
                        <path d="M2 17l10 5 10-5" />
                        <path d="M2 12l10 5 10-5" />
                      </svg>
                    </div>

                    <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-4">
                      Welcome to Alchymine
                    </p>
                    <h1 className="font-display text-display-md font-light mb-3">
                      Welcome,{" "}
                      <span className="text-gradient-gold">{displayName}</span>
                    </h1>
                    <hr className="rule-gold my-6 max-w-[60px] mx-auto" />
                    <p className="font-body text-text/40 max-w-md mx-auto mb-10 leading-relaxed">
                      Complete your intake assessment to begin tracking your
                      transformation journey across all five Alchymine systems.
                    </p>
                    <Link href="/discover/intake">
                      <Button size="lg">Start Your Journey</Button>
                    </Link>
                  </div>
                </MotionReveal>

                {/* Five system cards */}
                <MotionReveal delay={0.25} y={16}>
                  <div>
                    <p className="text-xs font-body font-medium text-text/30 uppercase tracking-[0.18em] mb-4 text-center">
                      The Five Systems
                    </p>
                    <MotionStagger
                      staggerDelay={0.07}
                      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
                    >
                      {[
                        {
                          href: "/intelligence",
                          label: "Personal Intelligence",
                          description:
                            "Numerology, astrology & personality insights",
                          accentText: "text-primary",
                          accentBg: "bg-primary/[0.07]",
                          accentBorder: "border-primary/[0.15]",
                          icon: (
                            <svg
                              className="w-5 h-5"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden="true"
                            >
                              <circle cx="12" cy="12" r="10" />
                              <path d="M12 16v-4" />
                              <path d="M12 8h.01" />
                            </svg>
                          ),
                        },
                        {
                          href: "/healing",
                          label: "Ethical Healing",
                          description: "Evidence-based modalities & breathwork",
                          accentText: "text-accent",
                          accentBg: "bg-accent/[0.07]",
                          accentBorder: "border-accent/[0.15]",
                          icon: <IconLeaf />,
                        },
                        {
                          href: "/wealth",
                          label: "Generational Wealth",
                          description: "Wealth archetype & financial planning",
                          accentText: "text-primary",
                          accentBg: "bg-primary/[0.07]",
                          accentBorder: "border-primary/[0.15]",
                          icon: <IconChart />,
                        },
                        {
                          href: "/creative",
                          label: "Creative Forge",
                          description: "Guilford assessment & creative DNA",
                          accentText: "text-secondary-light",
                          accentBg: "bg-secondary/[0.07]",
                          accentBorder: "border-secondary/[0.15]",
                          icon: <IconPalette />,
                        },
                        {
                          href: "/perspective",
                          label: "Perspective Prism",
                          description:
                            "Kegan stages & cognitive bias awareness",
                          accentText: "text-accent",
                          accentBg: "bg-accent/[0.07]",
                          accentBorder: "border-accent/[0.15]",
                          icon: (
                            <svg
                              className="w-5 h-5"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden="true"
                            >
                              <circle cx="11" cy="11" r="8" />
                              <path d="m21 21-4.35-4.35" />
                            </svg>
                          ),
                        },
                      ].map((sys) => (
                        <MotionStaggerItem key={sys.href}>
                          <QuickActionCard
                            href={sys.href}
                            label={sys.label}
                            description={sys.description}
                            accentText={sys.accentText}
                            accentBg={sys.accentBg}
                            accentBorder={sys.accentBorder}
                            icon={sys.icon}
                          />
                        </MotionStaggerItem>
                      ))}
                    </MotionStagger>
                  </div>
                </MotionReveal>
              </div>
            </div>
          ) : (
            // ── Main dashboard ──────────────────────────────────────
            <div className="px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
              <div className="max-w-4xl mx-auto space-y-8">
                {/* ── Page Header ──────────────────────────────────── */}
                <MotionReveal delay={0.1} y={16}>
                  <div className="text-center">
                    <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-3">
                      Your Progress
                    </p>
                    <h1 className="font-display text-display-md font-light mb-1">
                      Welcome back,{" "}
                      <span className="text-gradient-gold">{displayName}</span>
                    </h1>
                    <p className="font-body text-text/40 text-sm mt-2">
                      Your journey across all five Alchymine systems
                    </p>
                    <hr className="rule-gold mt-6 max-w-[80px] mx-auto" />
                  </div>
                </MotionReveal>

                {/* ── Tab Navigation ───────────────────────────────── */}
                <MotionReveal delay={0.2} y={12}>
                  <div
                    role="tablist"
                    aria-label="Dashboard sections"
                    className="flex items-center justify-center gap-1 bg-surface/60 border border-white/[0.06] rounded-xl p-1 w-fit mx-auto"
                  >
                    {(["overview", "journal"] as const).map((tab) => {
                      const isActive = activeTab === tab;
                      const tabLabels = {
                        overview: "Overview",
                        journal: "Journal Stats",
                      };
                      return (
                        <button
                          key={tab}
                          role="tab"
                          aria-selected={isActive}
                          aria-controls={`tabpanel-${tab}`}
                          id={`tab-${tab}`}
                          onClick={() => setActiveTab(tab)}
                          className={`relative px-5 py-2.5 rounded-lg font-body text-sm tracking-wide transition-all duration-300 touch-target ${
                            isActive
                              ? "text-primary bg-primary/10"
                              : "text-text/50 hover:text-text/70 hover:bg-white/[0.03]"
                          }`}
                        >
                          {tabLabels[tab]}
                          {/* Gold underline for active tab */}
                          {isActive && (
                            <span
                              aria-hidden="true"
                              className="absolute bottom-1 left-4 right-4 h-px rounded-full"
                              style={{
                                background:
                                  "linear-gradient(90deg, transparent, rgba(218,165,32,0.7), transparent)",
                              }}
                            />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </MotionReveal>

                {/* ── Overview Tab ─────────────────────────────────── */}
                {activeTab === "overview" && (
                  <div
                    id="tabpanel-overview"
                    role="tabpanel"
                    aria-labelledby="tab-overview"
                    className="space-y-6"
                  >
                    {/* Overall Score Card */}
                    <MotionReveal delay={0.25} y={16}>
                      <Card title="Overall Progress">
                        {outcomes.loading ? (
                          <Spinner />
                        ) : outcomes.error ? (
                          <div className="text-center py-8">
                            <p className="font-body text-text/50 mb-2">
                              No outcome data yet — start using the systems!
                            </p>
                            <p className="font-body text-xs text-text/25">
                              Your progress will appear here as you complete
                              milestones and engage with the platform.
                            </p>
                          </div>
                        ) : outcomes.data ? (
                          <div>
                            {/* Progress ring — featured hero metric */}
                            <div className="flex justify-center mb-8">
                              <div className="glow-gold rounded-full p-1">
                                <ProgressRing
                                  value={outcomes.data.overall_score}
                                  label="Overall Score"
                                  size={110}
                                />
                              </div>
                            </div>

                            <hr className="rule-gold mb-6" />

                            {/* Stats grid */}
                            <StatGrid
                              stats={[
                                {
                                  value: outcomes.data.completed_milestones,
                                  label: "Milestones Complete",
                                },
                                {
                                  value: outcomes.data.total_milestones,
                                  label: "Total Milestones",
                                },
                                {
                                  value: outcomes.data.systems.length,
                                  label: "Systems Active",
                                },
                                {
                                  value: outcomes.data.active_plan_day ?? "—",
                                  label: "Plan Day",
                                },
                              ]}
                            />

                            {/* Quality gate — shows after outcomes load */}
                            <div className="flex justify-center pt-4 border-t border-white/5">
                              <QualityGateDisplay
                                checksPassed={5}
                                checksTotal={5}
                              />
                            </div>
                          </div>
                        ) : null}
                      </Card>
                    </MotionReveal>

                    {/* Per-system progress */}
                    {outcomes.data && outcomes.data.systems.length > 0 && (
                      <MotionReveal delay={0.3} y={16}>
                        <Card
                          title="System Progress"
                          subtitle="Engagement and milestones per system"
                        >
                          <MotionStagger
                            staggerDelay={0.08}
                            className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                          >
                            {outcomes.data.systems.map((sys) => (
                              <MotionStaggerItem key={sys.system}>
                                <SystemCard
                                  system={sys.system}
                                  engagement={sys.engagement_score}
                                  milestonesCompleted={sys.milestones_completed}
                                  milestonesTotal={sys.milestones_total}
                                  activeDays={sys.active_days}
                                />
                              </MotionStaggerItem>
                            ))}
                          </MotionStagger>
                        </Card>
                      </MotionReveal>
                    )}

                    {/* Cross-System Insights */}
                    {intake && (
                      <MotionReveal delay={0.33} y={16}>
                        <Card
                          title="Cross-System Insights"
                          subtitle="Connections across your five systems"
                        >
                          <div data-testid="cross-system-insights">
                            {crossInsights.loading ? (
                              <Spinner />
                            ) : crossInsights.error ||
                              !crossInsights.data ||
                              crossInsights.data.length === 0 ? (
                              <p className="font-body text-text/40 text-sm text-center py-4">
                                Complete more system assessments to unlock
                                cross-system insights.
                              </p>
                            ) : (
                              <MotionStagger
                                staggerDelay={0.08}
                                className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                              >
                                {crossInsights.data
                                  .slice(0, 4)
                                  .map((insight, i) => (
                                    <MotionStaggerItem
                                      key={`${insight.bridge_type}-${i}`}
                                    >
                                      <CrossInsightCard insight={insight} />
                                    </MotionStaggerItem>
                                  ))}
                              </MotionStagger>
                            )}
                          </div>
                        </Card>
                      </MotionReveal>
                    )}

                    {/* Quick Actions */}
                    <MotionReveal delay={0.35} y={16}>
                      <Card title="Quick Actions">
                        <MotionStagger
                          staggerDelay={0.1}
                          className="grid grid-cols-1 sm:grid-cols-3 gap-3"
                        >
                          <MotionStaggerItem>
                            <QuickActionCard
                              href="/healing"
                              label="Healing"
                              description="Start a practice session"
                              accentText="text-accent"
                              accentBg="bg-accent/[0.07]"
                              accentBorder="border-accent/[0.15]"
                              icon={<IconLeaf />}
                            />
                          </MotionStaggerItem>
                          <MotionStaggerItem>
                            <QuickActionCard
                              href="/wealth"
                              label="Wealth"
                              description="Review your plan"
                              accentText="text-primary"
                              accentBg="bg-primary/[0.07]"
                              accentBorder="border-primary/[0.15]"
                              icon={<IconChart />}
                            />
                          </MotionStaggerItem>
                          <MotionStaggerItem>
                            <QuickActionCard
                              href="/creative"
                              label="Creative"
                              description="Explore your style"
                              accentText="text-secondary-light"
                              accentBg="bg-secondary/[0.07]"
                              accentBorder="border-secondary/[0.15]"
                              icon={<IconPalette />}
                            />
                          </MotionStaggerItem>
                        </MotionStagger>
                      </Card>
                    </MotionReveal>
                  </div>
                )}

                {/* ── Journal Tab ──────────────────────────────────── */}
                {activeTab === "journal" && (
                  <div
                    id="tabpanel-journal"
                    role="tabpanel"
                    aria-labelledby="tab-journal"
                    className="space-y-6"
                  >
                    <MotionReveal delay={0.25} y={16}>
                      <Card title="Journal Overview">
                        {journalStats.loading ? (
                          <Spinner />
                        ) : journalStats.error ? (
                          <div className="text-center py-8">
                            <p className="font-body text-text/50 mb-2">
                              No journal entries yet — start writing!
                            </p>
                            <p className="font-body text-xs text-text/25">
                              Journal entries help track your reflections,
                              reframes, and progress across all systems.
                            </p>
                          </div>
                        ) : journalStats.data ? (
                          <div className="space-y-6">
                            {/* Stats grid */}
                            <StatGrid
                              stats={[
                                {
                                  value: journalStats.data.total_entries,
                                  label: "Total Entries",
                                },
                                {
                                  value: journalStats.data.streak_days,
                                  label: "Day Streak",
                                },
                                {
                                  value: journalStats.data.average_mood
                                    ? journalStats.data.average_mood.toFixed(1)
                                    : "—",
                                  label: "Avg Mood",
                                },
                                {
                                  value: journalStats.data.tags_used.length,
                                  label: "Tags Used",
                                },
                              ]}
                            />

                            {/* Entries by system */}
                            {Object.keys(journalStats.data.entries_by_system)
                              .length > 0 && (
                              <>
                                <hr className="rule-gold" />
                                <div>
                                  <h3 className="font-body text-xs font-medium text-text/40 uppercase tracking-[0.15em] mb-3">
                                    By System
                                  </h3>
                                  <div className="flex flex-wrap gap-2">
                                    {Object.entries(
                                      journalStats.data.entries_by_system,
                                    ).map(([sys, count]) => (
                                      <span
                                        key={sys}
                                        className="px-3 py-1 bg-primary/[0.08] border border-primary/[0.15] rounded-full text-xs font-body text-primary/80"
                                      >
                                        {sys}: {count}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </>
                            )}

                            {/* Entries by type */}
                            {Object.keys(journalStats.data.entries_by_type)
                              .length > 0 && (
                              <div>
                                <h3 className="font-body text-xs font-medium text-text/40 uppercase tracking-[0.15em] mb-3">
                                  By Type
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(
                                    journalStats.data.entries_by_type,
                                  ).map(([type, count]) => (
                                    <span
                                      key={type}
                                      className="px-3 py-1 bg-secondary/[0.08] border border-secondary/[0.15] rounded-full text-xs font-body text-secondary-light/80"
                                    >
                                      {type}: {count}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Tags */}
                            {journalStats.data.tags_used.length > 0 && (
                              <div>
                                <h3 className="font-body text-xs font-medium text-text/40 uppercase tracking-[0.15em] mb-3">
                                  Tags
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                  {journalStats.data.tags_used.map((tag) => (
                                    <span
                                      key={tag}
                                      className="px-3 py-1 bg-white/[0.04] border border-white/[0.08] rounded-full text-xs font-body text-text/50"
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
                    </MotionReveal>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </ProtectedRoute>
  );
}
