"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import Button from "@/components/shared/Button";
import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
import BreathworkTimer, {
  BreathworkCompletionData,
} from "@/components/shared/BreathworkTimer";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  getHealingModalities,
  getHealingMatch,
  getOutcomeSummary,
  logActivity,
  ModalityListResponse,
  HealingMatchListResponse,
  OutcomeSummary,
} from "@/lib/api";
import { useApi, getStoredIntake } from "@/lib/useApi";
import { useAuth } from "@/lib/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { DEMO_ACCOUNT_EMAIL } from "@/lib/constants";
import EvidenceBadge from "@/components/shared/EvidenceBadge";

// ── Constants ─────────────────────────────────────────────────────

interface BreathworkPhase {
  label: string;
  duration: number;
  color: string;
}

const BOX_BREATHING: BreathworkPhase[] = [
  { label: "Inhale", duration: 4, color: "text-accent" },
  { label: "Hold", duration: 4, color: "text-primary" },
  { label: "Exhale", duration: 4, color: "text-secondary" },
  { label: "Hold", duration: 4, color: "text-primary" },
];

const COHERENCE: BreathworkPhase[] = [
  { label: "Inhale", duration: 5.5, color: "text-accent" },
  { label: "Exhale", duration: 5.5, color: "text-secondary" },
];

const RELAXING_478: BreathworkPhase[] = [
  { label: "Inhale", duration: 4, color: "text-accent" },
  { label: "Hold", duration: 7, color: "text-primary" },
  { label: "Exhale", duration: 8, color: "text-secondary" },
];

const PATTERNS: Record<
  string,
  {
    name: string;
    phases: BreathworkPhase[];
    cycles: number;
    description: string;
  }
> = {
  box: {
    name: "Box Breathing",
    phases: BOX_BREATHING,
    cycles: 6,
    description:
      "Equal inhale-hold-exhale-hold. Used by Navy SEALs for focus and calm.",
  },
  coherence: {
    name: "Coherence Breathing",
    phases: COHERENCE,
    cycles: 10,
    description:
      "5.5-second rhythm synchronizes heart and breath for nervous system coherence.",
  },
  relaxing: {
    name: "4-7-8 Relaxing Breath",
    phases: RELAXING_478,
    cycles: 4,
    description:
      "Dr. Andrew Weil's technique for deep relaxation and sleep preparation.",
  },
};

const MODALITY_ICONS: Record<string, string> = {
  breathwork: "\u{1F32C}\u{FE0F}",
  meditation: "\u{1F9D8}",
  language: "\u{1F4DD}",
  resilience: "\u{1F4AA}",
  sound: "\u{1F514}",
  somatic: "\u{1FAC0}",
  nature: "\u{1F332}",
  sleep: "\u{1F319}",
};

const CRISIS_RESOURCES = [
  {
    name: "988 Suicide & Crisis Lifeline",
    contact: "Call or text 988",
    description: "Free, confidential 24/7 support for anyone in crisis.",
  },
  {
    name: "Crisis Text Line",
    contact: "Text HOME to 741741",
    description: "Free crisis counseling via text message, 24/7.",
  },
  {
    name: "SAMHSA National Helpline",
    contact: "1-800-662-4357",
    description:
      "Free referral service for substance abuse and mental health, 24/7.",
  },
];

// ── Demo data for modality progress ──────────────────────────────

interface ModalityProgress {
  name: string;
  sessionsCompleted: number;
  totalSessions: number;
  lastPracticed: string;
  streak: number;
}

const DEMO_MODALITY_PROGRESS: ModalityProgress[] = [
  {
    name: "Breathwork",
    sessionsCompleted: 18,
    totalSessions: 30,
    lastPracticed: "2026-02-28",
    streak: 5,
  },
  {
    name: "Meditation",
    sessionsCompleted: 12,
    totalSessions: 30,
    lastPracticed: "2026-02-27",
    streak: 3,
  },
  {
    name: "Sound Healing",
    sessionsCompleted: 6,
    totalSessions: 15,
    lastPracticed: "2026-02-25",
    streak: 0,
  },
  {
    name: "Somatic Practice",
    sessionsCompleted: 8,
    totalSessions: 20,
    lastPracticed: "2026-02-28",
    streak: 2,
  },
  {
    name: "Nature Healing",
    sessionsCompleted: 4,
    totalSessions: 12,
    lastPracticed: "2026-02-23",
    streak: 0,
  },
  {
    name: "Sleep Healing",
    sessionsCompleted: 14,
    totalSessions: 30,
    lastPracticed: "2026-02-28",
    streak: 7,
  },
];

// ── Helper ────────────────────────────────────────────────────────

function getModalityIcon(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, icon] of Object.entries(MODALITY_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return "\u{2728}";
}

// ── Streak level helpers ──────────────────────────────────────────

function getStreakLevel(days: number): string {
  if (days >= 30) return "Legendary";
  if (days >= 14) return "Committed";
  if (days >= 7) return "Building";
  if (days >= 3) return "Starting";
  return "Begin";
}

function getStreakMotivation(days: number): string {
  if (days === 0) return "Start your first session to begin your streak!";
  if (days < 7) return "Keep going! Consistency builds transformation.";
  if (days < 30) return "You are building a powerful habit. Stay with it.";
  return "Incredible dedication. Your practice is becoming part of you.";
}

// ── Sub-components ────────────────────────────────────────────────

function PracticeStreakCounter({ streakDays }: { streakDays: number }) {
  const streakLevel = getStreakLevel(streakDays);

  // Show last 7 days (demo: assume current streak is consecutive ending today)
  const days = Array.from({ length: 7 }, (_, i) => {
    const dayOffset = 6 - i;
    return {
      label: ["S", "M", "T", "W", "T", "F", "S"][
        (new Date().getDay() - dayOffset + 7) % 7
      ],
      active: dayOffset < streakDays,
    };
  });

  return (
    <div data-testid="practice-streak" className="card-surface p-6 glow-teal">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-lg font-light text-text/80">
          Practice Streak
        </h3>
        <span className="font-body text-[0.7rem] tracking-wider uppercase px-3 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
          {streakLevel}
        </span>
      </div>

      {/* Big streak number */}
      <div className="text-center mb-5">
        <div
          className="font-display font-light text-gradient-teal"
          style={{ fontSize: "clamp(3rem, 8vw, 4.5rem)", lineHeight: 1 }}
          aria-label={`${streakDays} day streak`}
        >
          {streakDays}
        </div>
        <div className="font-body text-sm text-text/40 mt-2">days in a row</div>
      </div>

      {/* Week view */}
      <div
        className="flex justify-center gap-2"
        role="group"
        aria-label="Last 7 days practice history"
      >
        {days.map((day, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-body transition-all duration-300 ${
                day.active
                  ? "bg-accent/20 border-2 border-accent text-accent"
                  : "bg-white/5 border border-white/10 text-text/30"
              }`}
              aria-label={`${day.label}: ${day.active ? "practiced" : "not practiced"}`}
            >
              {day.active ? "\u{2713}" : ""}
            </div>
            <span className="font-body text-[10px] text-text/30">
              {day.label}
            </span>
          </div>
        ))}
      </div>

      {/* Motivation line */}
      <p className="font-body text-center text-xs text-text/40 mt-4">
        {getStreakMotivation(streakDays)}
      </p>
    </div>
  );
}

function ModalityProgressCards({
  modalities,
}: {
  modalities: ModalityProgress[];
}) {
  return (
    <div data-testid="modality-progress">
      <h3 className="font-display text-xl font-light text-text/80 mb-5">
        Modality Progress
      </h3>
      <MotionStagger className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modalities.map((mod) => {
          const pct = (mod.sessionsCompleted / mod.totalSessions) * 100;
          const icon = getModalityIcon(mod.name);
          return (
            <MotionStaggerItem key={mod.name}>
              <div className="card-surface p-4 hover:glow-teal hover:-translate-y-1 transition-all duration-500 h-full">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xl" aria-hidden="true">
                      {icon}
                    </span>
                    <h4 className="font-body text-sm font-medium text-text/80">
                      {mod.name}
                    </h4>
                  </div>
                  {mod.streak > 0 && (
                    <span
                      className="font-body text-[0.7rem] tracking-wider uppercase text-accent flex items-center gap-1"
                      aria-label={`${mod.streak} day streak`}
                    >
                      {"\u{1F525}"} {mod.streak}d
                    </span>
                  )}
                </div>

                {/* Session progress bar */}
                <div className="mb-2">
                  <div className="flex justify-between font-body text-xs text-text/40 mb-1">
                    <span>Sessions</span>
                    <span>
                      {mod.sessionsCompleted}/{mod.totalSessions}
                    </span>
                  </div>
                  <div
                    className="h-1.5 bg-white/5 rounded-full overflow-hidden"
                    role="progressbar"
                    aria-valuenow={mod.sessionsCompleted}
                    aria-valuemin={0}
                    aria-valuemax={mod.totalSessions}
                    aria-label={`${mod.name} progress`}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${pct}%`,
                        background:
                          "linear-gradient(90deg, #008080, #20b2aa, #5cd6d0)",
                      }}
                    />
                  </div>
                </div>

                <div className="font-body text-[10px] text-text/25">
                  Last: {mod.lastPracticed}
                </div>
              </div>
            </MotionStaggerItem>
          );
        })}
      </MotionStagger>
    </div>
  );
}

// ── Healing Progress Dashboard ────────────────────────────────────

function HealingProgressDashboard({ summary }: { summary: OutcomeSummary }) {
  const healingSystem = summary.systems.find((s) => s.system === "healing");
  const activeDays = healingSystem?.active_days ?? 0;
  const engagementScore = healingSystem
    ? Math.round(healingSystem.engagement_score)
    : 0;
  const milestonesCompleted = healingSystem?.milestones_completed ?? 0;
  const milestonesTotal = healingSystem?.milestones_total ?? 0;

  // Derive "sessions this week" from active_days (capped at 7)
  const sessionsThisWeek = Math.min(activeDays, 7);

  // Suggested next modality: cycle through based on what they may not have tried
  const MODALITY_ORDER = [
    "Breathwork",
    "Meditation",
    "Sound Healing",
    "Somatic Practice",
    "Nature Healing",
    "Sleep Healing",
  ];
  const nextModality =
    MODALITY_ORDER[milestonesCompleted % MODALITY_ORDER.length] ??
    MODALITY_ORDER[0];

  return (
    <div
      data-testid="healing-progress-dashboard"
      className="card-surface p-6 glow-teal"
    >
      <h3 className="font-display text-lg font-light text-text/80 mb-5">
        Your Healing Progress
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div
            className="font-display font-light text-gradient-teal"
            style={{ fontSize: "clamp(1.5rem, 3.5vw, 2rem)" }}
            aria-label={`${activeDays} total active days`}
          >
            {activeDays}
          </div>
          <div className="font-body text-xs text-text/40 mt-1">Active Days</div>
        </div>
        <div className="text-center">
          <div
            className="font-display font-light text-gradient-teal"
            style={{ fontSize: "clamp(1.5rem, 3.5vw, 2rem)" }}
            aria-label={`${sessionsThisWeek} sessions this week`}
          >
            {sessionsThisWeek}
          </div>
          <div className="font-body text-xs text-text/40 mt-1">This Week</div>
        </div>
        <div className="text-center">
          <div
            className="font-display font-light text-gradient-teal"
            style={{ fontSize: "clamp(1.5rem, 3.5vw, 2rem)" }}
            aria-label={`${engagementScore} engagement score`}
          >
            {engagementScore}
          </div>
          <div className="font-body text-xs text-text/40 mt-1">
            Engagement
          </div>
        </div>
        <div className="text-center">
          <div
            className="font-display font-light text-gradient-teal"
            style={{ fontSize: "clamp(1.5rem, 3.5vw, 2rem)" }}
            aria-label={`${milestonesCompleted} of ${milestonesTotal} milestones`}
          >
            {milestonesCompleted}/{milestonesTotal}
          </div>
          <div className="font-body text-xs text-text/40 mt-1">Milestones</div>
        </div>
      </div>

      {/* Recommended next */}
      <div className="bg-white/[0.03] border border-accent/10 rounded-xl p-4 flex items-center justify-between gap-4">
        <div>
          <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
            Recommended Next
          </p>
          <p className="font-body text-sm font-medium text-text/80">
            {getModalityIcon(nextModality)}{" "}
            <span className="ml-1">{nextModality}</span>
          </p>
        </div>
        <a
          href="#breathwork"
          className="font-body text-xs text-accent hover:text-accent-light transition-colors duration-200 whitespace-nowrap"
        >
          Start &rarr;
        </a>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────

export default function HealingPage() {
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);
  const { user } = useAuth();
  const isDemoUser = user?.email === DEMO_ACCOUNT_EMAIL;
  const intake = useMemo(() => getStoredIntake(), []);
  const hasIntake = !!(intake?.intentions?.length || intake?.intention);

  // Fetch modalities from API
  const modalities = useApi<ModalityListResponse>(
    () => getHealingModalities(),
    [],
  );

  // Fetch personalized matches if user has intake data
  const intakeIntentions =
    intake?.intentions ?? (intake?.intention ? [intake.intention] : []);
  const matches = useApi<HealingMatchListResponse>(
    hasIntake ? () => getHealingMatch({ intentions: intakeIntentions }) : null,
    [intakeIntentions.join(",")],
  );

  // Fetch outcomes summary for progress dashboard (non-demo users)
  const outcomeSummary = useApi<OutcomeSummary>(
    user?.id && !isDemoUser
      ? () => getOutcomeSummary(user.id)
      : null,
    [user?.id ?? ""],
  );

  // Use API modalities if available, otherwise show hardcoded list
  const modalityList = modalities.data?.modalities ?? [];

  // Demo streak (would come from API in production)
  const demoStreak = 5;

  return (
    <ProtectedRoute>
      <main id="main-content" className="min-h-screen grain-overlay bg-atmosphere px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-5xl mx-auto">
          {/* Crisis Resources — ALWAYS visible, prominent, at top */}
          <MotionReveal duration={0.5}>
            <section className="mb-10" aria-labelledby="crisis-heading">
              <div className="card-surface border border-accent/10 p-5">
                <h2
                  id="crisis-heading"
                  className="font-display text-lg font-light text-text/80 mb-2 flex items-center gap-3"
                >
                  <span
                    className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0"
                    aria-hidden="true"
                  >
                    <svg
                      className="w-4 h-4 text-accent"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
                      <path d="M12 8v4" />
                      <path d="M12 16h.01" />
                    </svg>
                  </span>
                  Crisis Resources
                </h2>
                <p className="font-body text-text/40 text-sm mb-4 ml-11">
                  If you or someone you know is in crisis, these resources are
                  available 24/7. You are not alone.
                </p>
                <div className="grid sm:grid-cols-3 gap-3">
                  {CRISIS_RESOURCES.map((resource) => (
                    <div
                      key={resource.name}
                      className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4"
                    >
                      <h3 className="font-body text-sm font-medium text-text/80 mb-1">
                        {resource.name}
                      </h3>
                      <p className="font-body text-accent font-medium text-sm mb-1">
                        {resource.contact}
                      </p>
                      <p className="font-body text-xs text-text/40">
                        {resource.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </MotionReveal>

          {/* Page Header */}
          <MotionReveal delay={0.05}>
            <header className="mb-10">
              <h1 className="font-display text-display-md font-light mb-3">
                <span className="text-gradient-teal">Ethical Healing</span>
              </h1>
              <hr className="rule-gold mb-4" aria-hidden="true" />
              <p className="font-body text-text/40 text-base max-w-2xl">
                Personalized modalities matched to your unique profile.
                Evidence-informed, culturally sensitive, with full safety
                protocols.
              </p>
            </header>
          </MotionReveal>

          {/* Practice Streak + Stats Row — demo data only */}
          {isDemoUser && (
            <MotionReveal delay={0.1}>
              <section
                className="mb-12 grid md:grid-cols-2 gap-6"
                aria-labelledby="streak-heading"
              >
                <div>
                  <h2 id="streak-heading" className="sr-only">
                    Practice Streak
                  </h2>
                  <PracticeStreakCounter streakDays={demoStreak} />
                </div>

                {/* Quick stats */}
                <div className="card-surface p-6">
                  <h3 className="font-display text-lg font-light text-text/80 mb-5">
                    Healing Summary
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <div
                        className="font-display font-light text-gradient-teal"
                        style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}
                        aria-label="62 total sessions"
                      >
                        62
                      </div>
                      <div className="font-body text-xs text-text/40 mt-1">
                        Total Sessions
                      </div>
                    </div>
                    <div className="text-center">
                      <div
                        className="font-display font-light text-gradient-teal"
                        style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}
                        aria-label="6 modalities used"
                      >
                        6
                      </div>
                      <div className="font-body text-xs text-text/40 mt-1">
                        Modalities Used
                      </div>
                    </div>
                    <div className="text-center">
                      <div
                        className="font-display font-light text-gradient-teal"
                        style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}
                        aria-label="4.2 hours this week"
                      >
                        4.2h
                      </div>
                      <div className="font-body text-xs text-text/40 mt-1">
                        This Week
                      </div>
                    </div>
                    <div className="text-center">
                      <div
                        className="font-display font-light text-gradient-teal"
                        style={{ fontSize: "clamp(1.75rem, 4vw, 2.25rem)" }}
                        aria-label="87% completion rate"
                      >
                        87%
                      </div>
                      <div className="font-body text-xs text-text/40 mt-1">
                        Completion Rate
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </MotionReveal>
          )}

          {/* Healing Progress Dashboard — real API data for non-demo users */}
          {!isDemoUser && outcomeSummary.data && (
            <MotionReveal delay={0.1}>
              <section
                className="mb-12"
                aria-labelledby="healing-dashboard-heading"
              >
                <h2 id="healing-dashboard-heading" className="sr-only">
                  Healing Progress Dashboard
                </h2>
                <HealingProgressDashboard summary={outcomeSummary.data} />
              </section>
            </MotionReveal>
          )}

          {/* Personalized Matches */}
          {hasIntake && (
            <MotionReveal>
              <section className="mb-12" aria-labelledby="matches-heading">
                <h2
                  id="matches-heading"
                  className="section-heading-sm mb-2 flex items-center gap-3"
                >
                  <span
                    className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl flex-shrink-0"
                    aria-hidden="true"
                  >
                    {"\u{2728}"}
                  </span>
                  Your Matched Modalities
                </h2>
                <hr className="rule-gold mb-6" aria-hidden="true" />
                <ApiStateView
                  loading={matches.loading}
                  error={matches.error}
                  empty={!matches.data || matches.data.matches.length === 0}
                  loadingText="Matching modalities to your profile..."
                  emptyText="Complete the full assessment to get personalized modality recommendations."
                  onRetry={matches.refetch}
                >
                  {matches.data && (
                    <MotionStagger className="grid sm:grid-cols-2 gap-4">
                      {matches.data.matches.map((match) => (
                        <MotionStaggerItem key={match.modality}>
                          <div
                            className={`card-surface p-5 hover:-translate-y-1 transition-all duration-500 ${
                              match.contraindicated
                                ? "opacity-50 border-l-2 border-white/20"
                                : "hover:glow-teal"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xl" aria-hidden="true">
                                  {getModalityIcon(match.modality)}
                                </span>
                                <h3 className="font-body font-medium text-sm text-text/80">
                                  {match.modality}
                                </h3>
                              </div>
                              <span className="font-body text-xs text-accent/70">
                                {Math.round(match.preference_score * 100)}%
                              </span>
                            </div>
                            <div className="flex items-center gap-2 mt-2 flex-wrap">
                              <span className="font-body text-[0.7rem] tracking-wider uppercase px-2 py-0.5 bg-white/5 text-text/30 rounded-full">
                                {match.difficulty_level}
                              </span>
                              {match.contraindicated && (
                                <span className="font-body text-[0.7rem] tracking-wider uppercase px-2 py-0.5 bg-white/5 text-text/40 rounded-full">
                                  Contraindicated
                                </span>
                              )}
                            </div>
                          </div>
                        </MotionStaggerItem>
                      ))}
                    </MotionStagger>
                  )}
                </ApiStateView>
              </section>
            </MotionReveal>
          )}

          {/* Breathwork Timer */}
          <MotionReveal>
            <section className="mb-12" aria-labelledby="breathwork-heading">
              {selectedPattern ? (
                <BreathworkTimer
                  pattern={PATTERNS[selectedPattern]}
                  onComplete={(data: BreathworkCompletionData) => {
                    if (user?.id && selectedPattern) {
                      logActivity({
                        user_id: user.id,
                        system: "healing",
                        activity_type: "breathwork_session",
                        metadata: {
                          pattern: selectedPattern,
                          pattern_name: data.pattern_name,
                          duration_seconds: data.duration_seconds,
                          cycles: data.cycles,
                        },
                      }).catch(() => {});
                    }
                    setSelectedPattern(null);
                  }}
                  onStop={() => setSelectedPattern(null)}
                />
              ) : (
                <div id="breathwork">
                  <h2
                    id="breathwork-heading"
                    className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
                  >
                    Breathwork Sessions
                    <EvidenceBadge level="strong" />
                  </h2>
                  <hr className="rule-gold mb-6" aria-hidden="true" />
                  <MotionStagger className="grid md:grid-cols-3 gap-6">
                    {Object.entries(PATTERNS).map(([key, p]) => (
                      <MotionStaggerItem key={key}>
                        <div className="card-surface p-6 hover:glow-teal hover:-translate-y-1 transition-all duration-500 flex flex-col h-full">
                          <h3 className="font-display text-lg font-light text-gradient-teal mb-2">
                            {p.name}
                          </h3>
                          <p className="font-body text-text/40 text-sm mb-4 flex-1">
                            {p.description}
                          </p>
                          <p className="font-body text-text/25 text-xs mb-5">
                            {p.phases
                              .map((ph) => `${ph.label} ${ph.duration}s`)
                              .join(" \u2192 ")}{" "}
                            {"\u00B7"} {p.cycles} cycles
                          </p>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => setSelectedPattern(key)}
                            aria-label={`Start ${p.name} session`}
                          >
                            Start
                          </Button>
                        </div>
                      </MotionStaggerItem>
                    ))}
                  </MotionStagger>
                </div>
              )}
            </section>
          </MotionReveal>

          {/* Modality Progress Cards — demo data only */}
          {isDemoUser && (
            <MotionReveal>
              <section
                className="mb-12"
                aria-labelledby="modality-progress-heading"
              >
                <h2 id="modality-progress-heading" className="sr-only">
                  Modality Progress
                </h2>
                <ModalityProgressCards modalities={DEMO_MODALITY_PROGRESS} />
              </section>
            </MotionReveal>
          )}

          {/* Modalities Grid */}
          <MotionReveal>
            <section className="mb-12" aria-labelledby="modalities-heading">
              <h2
                id="modalities-heading"
                className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
              >
                Healing Modalities
                <EvidenceBadge level="moderate" />
              </h2>
              <hr className="rule-gold mb-6" aria-hidden="true" />
              <ApiStateView
                loading={modalities.loading}
                error={modalities.error}
                loadingText="Loading modalities..."
                onRetry={modalities.refetch}
              >
                <MotionStagger className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  {(modalityList.length > 0
                    ? modalityList.map((mod) => ({
                        key: mod.name,
                        icon: getModalityIcon(mod.name),
                        name: mod.name,
                        sub: mod.category,
                        badge: mod.evidence_level,
                        dim: false,
                      }))
                    : [
                        "Breathwork",
                        "Coherence Meditation",
                        "Language Awareness",
                        "Resilience Training",
                        "Sound Healing",
                        "Somatic Practice",
                        "Nature Healing",
                        "Sleep Healing",
                      ].map((name) => ({
                        key: name,
                        icon: getModalityIcon(name),
                        name,
                        sub: null,
                        badge: "Coming Soon",
                        dim: true,
                      }))
                  ).map((item) => (
                    <MotionStaggerItem key={item.key}>
                      <div
                        className={`card-surface p-4 hover:glow-teal hover:-translate-y-1 transition-all duration-500 ${
                          item.dim ? "opacity-50" : "cursor-pointer"
                        }`}
                      >
                        <div className="text-3xl mb-3" aria-hidden="true">
                          {item.icon}
                        </div>
                        <h3 className="font-body font-medium text-sm text-text/80">
                          {item.name}
                        </h3>
                        {item.sub && (
                          <p className="font-body text-xs text-text/40 mt-1">
                            {item.sub}
                          </p>
                        )}
                        <span className="font-body text-[0.7rem] tracking-wider uppercase inline-block mt-2 px-2 py-0.5 bg-white/5 text-text/30 rounded-full">
                          {item.badge}
                        </span>
                      </div>
                    </MotionStaggerItem>
                  ))}
                </MotionStagger>
              </ApiStateView>

              <MethodologyPanel
                title="Healing Modalities"
                methodology="Healing modalities are matched to user profiles based on attachment style, personality traits, and stated intentions. Breathwork protocols follow established patterns (Box Breathing, Coherence, 4-7-8) with fixed timing cycles. Modality recommendations are AI-assisted but grounded in evidence-based frameworks. All sessions include safety protocols and crisis resource access."
                evidenceLevel="moderate"
                calculationType="hybrid"
                sources={[
                  'Zaccaro et al. (2018) "How Breath-Control Can Change Your Life" - systematic review of breathwork effects on autonomic nervous system',
                  'McCraty & Zayas (2014) "Cardiac coherence, self-regulation" - HeartMath Institute research on coherence breathing',
                  'Weil, A. "4-7-8 Breathing Technique" - clinical observations on relaxation response',
                  "SAMHSA Treatment Improvement Protocols for crisis resource standards",
                ]}
              />
            </section>
          </MotionReveal>
          {/* Connections — healing-perspective bridge */}
          {hasIntake && (
            <MotionReveal>
              <section
                className="mb-12"
                aria-labelledby="healing-connections-heading"
                data-testid="connections-section"
              >
                <div className="card-surface border border-accent/10 p-5">
                  <h2
                    id="healing-connections-heading"
                    className="font-display text-sm font-medium text-accent mb-3"
                  >
                    Connected: Healing &amp; Perspective
                  </h2>
                  <p className="font-body text-sm text-text/50 leading-relaxed mb-3">
                    Your healing practices directly prime your capacity for perspective shifts.
                    Breathwork and somatic work soften rigid thinking patterns, making Kegan
                    stage transitions more accessible. Start with a breathwork session before
                    doing perspective work for deeper integration.
                  </p>
                  <Link
                    href="/perspective"
                    className="font-body text-xs text-accent underline underline-offset-2"
                  >
                    Explore Perspective Prism &rarr;
                  </Link>
                </div>
              </section>
            </MotionReveal>
          )}

          {/* Bottom spacing to prevent fixed footer overlap */}
          <div className="h-12" aria-hidden="true" />
        </div>
      </main>

      {/* Fixed "Need Support?" safety link — always accessible, non-intrusive */}
      <div
        className="fixed bottom-4 right-4 z-50"
        role="complementary"
        aria-label="Crisis support resources"
      >
        <a
          href="#crisis-heading"
          className="font-body text-xs text-text/30 hover:text-text/60 transition-colors duration-200 flex items-center gap-1.5 bg-bg/80 backdrop-blur-sm px-3 py-2 rounded-full border border-white/5 hover:border-white/10"
          aria-label="Need support? Jump to crisis resources"
        >
          <span aria-hidden="true">
            <svg
              className="w-3 h-3"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
            </svg>
          </span>
          Need Support?
        </a>
      </div>
    </ProtectedRoute>
  );
}
