'use client';

import { useState, useMemo } from 'react';
import Button from '@/components/shared/Button';
import MethodologyPanel from '@/components/shared/MethodologyPanel';
import ApiStateView from '@/components/shared/ApiStateView';
import BreathworkTimer from '@/components/shared/BreathworkTimer';
import {
  getHealingModalities,
  getHealingMatch,
  ModalityListResponse,
  HealingMatchListResponse,
} from '@/lib/api';
import { useApi, getStoredIntake } from '@/lib/useApi';

// ── Constants ─────────────────────────────────────────────────────

interface BreathworkPhase {
  label: string;
  duration: number;
  color: string;
}

const BOX_BREATHING: BreathworkPhase[] = [
  { label: 'Inhale', duration: 4, color: 'text-accent' },
  { label: 'Hold', duration: 4, color: 'text-primary' },
  { label: 'Exhale', duration: 4, color: 'text-secondary' },
  { label: 'Hold', duration: 4, color: 'text-primary' },
];

const COHERENCE: BreathworkPhase[] = [
  { label: 'Inhale', duration: 5.5, color: 'text-accent' },
  { label: 'Exhale', duration: 5.5, color: 'text-secondary' },
];

const RELAXING_478: BreathworkPhase[] = [
  { label: 'Inhale', duration: 4, color: 'text-accent' },
  { label: 'Hold', duration: 7, color: 'text-primary' },
  { label: 'Exhale', duration: 8, color: 'text-secondary' },
];

const PATTERNS: Record<string, { name: string; phases: BreathworkPhase[]; cycles: number; description: string }> = {
  box: {
    name: 'Box Breathing',
    phases: BOX_BREATHING,
    cycles: 6,
    description: 'Equal inhale-hold-exhale-hold. Used by Navy SEALs for focus and calm.',
  },
  coherence: {
    name: 'Coherence Breathing',
    phases: COHERENCE,
    cycles: 10,
    description: '5.5-second rhythm synchronizes heart and breath for nervous system coherence.',
  },
  relaxing: {
    name: '4-7-8 Relaxing Breath',
    phases: RELAXING_478,
    cycles: 4,
    description: 'Dr. Andrew Weil\'s technique for deep relaxation and sleep preparation.',
  },
};

const MODALITY_ICONS: Record<string, string> = {
  'breathwork': '\u{1F32C}\u{FE0F}',
  'meditation': '\u{1F9D8}',
  'language': '\u{1F4DD}',
  'resilience': '\u{1F4AA}',
  'sound': '\u{1F514}',
  'somatic': '\u{1FAC0}',
  'nature': '\u{1F332}',
  'sleep': '\u{1F319}',
};

const CRISIS_RESOURCES = [
  {
    name: '988 Suicide & Crisis Lifeline',
    contact: 'Call or text 988',
    description: 'Free, confidential 24/7 support for anyone in crisis.',
  },
  {
    name: 'Crisis Text Line',
    contact: 'Text HOME to 741741',
    description: 'Free crisis counseling via text message, 24/7.',
  },
  {
    name: 'SAMHSA National Helpline',
    contact: '1-800-662-4357',
    description: 'Free referral service for substance abuse and mental health, 24/7.',
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
  { name: 'Breathwork', sessionsCompleted: 18, totalSessions: 30, lastPracticed: '2026-02-28', streak: 5 },
  { name: 'Meditation', sessionsCompleted: 12, totalSessions: 30, lastPracticed: '2026-02-27', streak: 3 },
  { name: 'Sound Healing', sessionsCompleted: 6, totalSessions: 15, lastPracticed: '2026-02-25', streak: 0 },
  { name: 'Somatic Practice', sessionsCompleted: 8, totalSessions: 20, lastPracticed: '2026-02-28', streak: 2 },
  { name: 'Nature Healing', sessionsCompleted: 4, totalSessions: 12, lastPracticed: '2026-02-23', streak: 0 },
  { name: 'Sleep Healing', sessionsCompleted: 14, totalSessions: 30, lastPracticed: '2026-02-28', streak: 7 },
];

// ── Helper ────────────────────────────────────────────────────────

function getModalityIcon(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, icon] of Object.entries(MODALITY_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return '\u{2728}';
}

// ── Sub-components ────────────────────────────────────────────────

function PracticeStreakCounter({ streakDays }: { streakDays: number }) {
  const streakLevel =
    streakDays >= 30 ? 'Legendary' :
    streakDays >= 14 ? 'Committed' :
    streakDays >= 7 ? 'Building' :
    streakDays >= 3 ? 'Starting' :
    'Begin';

  const streakColor =
    streakDays >= 30 ? '#f59e0b' :
    streakDays >= 14 ? '#6366f1' :
    streakDays >= 7 ? '#10b981' :
    streakDays >= 3 ? '#8b5cf6' :
    '#6b7280';

  // Show last 7 days (demo: assume current streak is consecutive ending today)
  const days = Array.from({ length: 7 }, (_, i) => {
    const dayOffset = 6 - i;
    return {
      label: ['S', 'M', 'T', 'W', 'T', 'F', 'S'][(new Date().getDay() - dayOffset + 7) % 7],
      active: dayOffset < streakDays,
    };
  });

  return (
    <div data-testid="practice-streak" className="card-surface p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Practice Streak</h3>
        <span
          className="px-3 py-1 rounded-full text-xs font-medium"
          style={{ background: `${streakColor}22`, color: streakColor }}
        >
          {streakLevel}
        </span>
      </div>

      {/* Big streak number */}
      <div className="text-center mb-4">
        <div className="text-5xl font-bold" style={{ color: streakColor }}>
          {streakDays}
        </div>
        <div className="text-sm text-text/40 mt-1">days in a row</div>
      </div>

      {/* Week view */}
      <div className="flex justify-center gap-2">
        {days.map((day, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all"
              style={{
                background: day.active ? `${streakColor}33` : 'rgba(255,255,255,0.05)',
                border: day.active ? `2px solid ${streakColor}` : '1px solid rgba(255,255,255,0.1)',
                color: day.active ? streakColor : 'rgba(255,255,255,0.3)',
              }}
            >
              {day.active ? '\u{2713}' : ''}
            </div>
            <span className="text-[10px] text-text/30">{day.label}</span>
          </div>
        ))}
      </div>

      {/* Motivation line */}
      <p className="text-center text-xs text-text/40 mt-4">
        {streakDays === 0
          ? 'Start your first session to begin your streak!'
          : streakDays < 7
            ? 'Keep going! Consistency builds transformation.'
            : streakDays < 30
              ? 'You are building a powerful habit. Stay with it.'
              : 'Incredible dedication. Your practice is becoming part of you.'}
      </p>
    </div>
  );
}

function ModalityProgressCards({ modalities }: { modalities: ModalityProgress[] }) {
  return (
    <div data-testid="modality-progress">
      <h3 className="text-lg font-semibold mb-4">Modality Progress</h3>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modalities.map((mod) => {
          const pct = (mod.sessionsCompleted / mod.totalSessions) * 100;
          const icon = getModalityIcon(mod.name);
          return (
            <div
              key={mod.name}
              className="card-surface p-4 hover:glow-gold transition-all"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xl" aria-hidden="true">{icon}</span>
                  <h4 className="text-sm font-medium">{mod.name}</h4>
                </div>
                {mod.streak > 0 && (
                  <span className="text-xs text-primary flex items-center gap-1">
                    {'\u{1F525}'} {mod.streak}d
                  </span>
                )}
              </div>

              {/* Session progress bar */}
              <div className="mb-2">
                <div className="flex justify-between text-xs text-text/40 mb-1">
                  <span>Sessions</span>
                  <span>{mod.sessionsCompleted}/{mod.totalSessions}</span>
                </div>
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-700"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>

              <div className="text-[10px] text-text/30">
                Last: {mod.lastPracticed}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────

export default function HealingPage() {
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);
  const intake = useMemo(() => getStoredIntake(), []);
  const hasIntake = !!intake?.intention;

  // Fetch modalities from API
  const modalities = useApi<ModalityListResponse>(
    () => getHealingModalities(),
    [],
  );

  // Fetch personalized matches if user has intake data
  const matches = useApi<HealingMatchListResponse>(
    hasIntake ? () => getHealingMatch({ intention: intake!.intention }) : null,
    [intake?.intention],
  );

  // Use API modalities if available, otherwise show hardcoded list
  const modalityList = modalities.data?.modalities ?? [];

  // Demo streak (would come from API in production)
  const demoStreak = 5;

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Crisis Resources — ALWAYS visible, prominent, at top */}
        <section className="mb-8" aria-labelledby="crisis-heading">
          <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-5">
            <h2 id="crisis-heading" className="text-lg font-bold mb-3 flex items-center gap-3">
              <span className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center" aria-hidden="true">
                <svg className="w-4 h-4 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
                  <path d="M12 8v4" />
                  <path d="M12 16h.01" />
                </svg>
              </span>
              Crisis Resources
            </h2>
            <p className="text-text/50 text-sm mb-3">
              If you or someone you know is in crisis, these resources are available 24/7. You are not alone.
            </p>
            <div className="grid sm:grid-cols-3 gap-3">
              {CRISIS_RESOURCES.map((resource) => (
                <div key={resource.name} className="bg-surface/50 border border-red-400/10 rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-text mb-1">{resource.name}</h3>
                  <p className="text-primary font-bold text-sm mb-1">{resource.contact}</p>
                  <p className="text-xs text-text/40">{resource.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Ethical Healing</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Personalized modalities matched to your unique profile. Evidence-informed,
            culturally sensitive, with full safety protocols.
          </p>
        </header>

        {/* Practice Streak + Stats Row */}
        <section className="mb-12 grid md:grid-cols-2 gap-6" aria-labelledby="streak-heading">
          <div>
            <h2 id="streak-heading" className="sr-only">Practice Streak</h2>
            <PracticeStreakCounter streakDays={demoStreak} />
          </div>

          {/* Quick stats */}
          <div className="card-surface p-6">
            <h3 className="text-lg font-semibold mb-4">Healing Summary</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">62</div>
                <div className="text-xs text-text/40 mt-1">Total Sessions</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-accent">6</div>
                <div className="text-xs text-text/40 mt-1">Modalities Used</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-secondary">4.2h</div>
                <div className="text-xs text-text/40 mt-1">This Week</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-400">87%</div>
                <div className="text-xs text-text/40 mt-1">Completion Rate</div>
              </div>
            </div>
          </div>
        </section>

        {/* Personalized Matches */}
        {hasIntake && (
          <section className="mb-12" aria-labelledby="matches-heading">
            <h2 id="matches-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl" aria-hidden="true">
                {'\u{2728}'}
              </span>
              Your Matched Modalities
            </h2>
            <ApiStateView
              loading={matches.loading}
              error={matches.error}
              empty={!matches.data || matches.data.matches.length === 0}
              loadingText="Matching modalities to your profile..."
              emptyText="Complete the full assessment to get personalized modality recommendations."
              onRetry={matches.refetch}
            >
              {matches.data && (
                <div className="grid sm:grid-cols-2 gap-4">
                  {matches.data.matches.map((match) => (
                    <div
                      key={match.modality}
                      className={`card-surface p-5 ${match.contraindicated ? 'opacity-50 border-l-2 border-red-400/30' : 'hover:glow-gold'} transition-all`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xl" aria-hidden="true">{getModalityIcon(match.modality)}</span>
                          <h3 className="font-semibold text-sm text-text">{match.modality}</h3>
                        </div>
                        <span className="text-xs font-mono text-primary">
                          {Math.round(match.preference_score * 100)}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-0.5 bg-white/5 text-text/30 text-[10px] font-medium rounded-full">
                          {match.difficulty_level}
                        </span>
                        {match.contraindicated && (
                          <span className="px-2 py-0.5 bg-red-400/10 text-red-400 text-[10px] font-medium rounded-full">
                            Contraindicated
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ApiStateView>
          </section>
        )}

        {/* Breathwork Timer */}
        <section className="mb-12" aria-labelledby="breathwork-heading">
          {selectedPattern ? (
            <BreathworkTimer
              pattern={PATTERNS[selectedPattern]}
              onComplete={() => setSelectedPattern(null)}
              onStop={() => setSelectedPattern(null)}
            />
          ) : (
            <div id="breathwork">
              <h2 id="breathwork-heading" className="text-2xl font-bold mb-6">Breathwork Sessions</h2>
              <div className="grid md:grid-cols-3 gap-6">
                {Object.entries(PATTERNS).map(([key, p]) => (
                  <div key={key} className="card-surface p-6 hover:glow-gold transition-all">
                    <h3 className="text-lg font-semibold text-primary mb-2">{p.name}</h3>
                    <p className="text-text/50 text-sm mb-4">{p.description}</p>
                    <p className="text-text/40 text-xs mb-4">
                      {p.phases.map((ph) => `${ph.label} ${ph.duration}s`).join(' \u2192 ')} {'\u00B7'} {p.cycles} cycles
                    </p>
                    <Button variant="primary" size="sm" onClick={() => setSelectedPattern(key)}>
                      Start
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Modality Progress Cards */}
        <section className="mb-12" aria-labelledby="modality-progress-heading">
          <h2 id="modality-progress-heading" className="sr-only">Modality Progress</h2>
          <ModalityProgressCards modalities={DEMO_MODALITY_PROGRESS} />
        </section>

        {/* Modalities Grid */}
        <section className="mb-12" aria-labelledby="modalities-heading">
          <h2 id="modalities-heading" className="text-2xl font-bold mb-6">Healing Modalities</h2>
          <ApiStateView
            loading={modalities.loading}
            error={modalities.error}
            loadingText="Loading modalities..."
            onRetry={modalities.refetch}
          >
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {modalityList.length > 0
                ? modalityList.map((mod) => (
                    <div
                      key={mod.name}
                      className="card-surface p-4 hover:glow-gold cursor-pointer transition-all"
                    >
                      <div className="text-3xl mb-2" aria-hidden="true">{getModalityIcon(mod.name)}</div>
                      <h3 className="font-medium text-sm">{mod.name}</h3>
                      <p className="text-xs text-text/40 mt-1">{mod.category}</p>
                      <span className="inline-block mt-2 px-2 py-0.5 bg-white/5 text-text/30 text-[10px] font-medium rounded-full">
                        {mod.evidence_level}
                      </span>
                    </div>
                  ))
                : /* Fallback static list */
                  ['Breathwork', 'Coherence Meditation', 'Language Awareness', 'Resilience Training', 'Sound Healing', 'Somatic Practice', 'Nature Healing', 'Sleep Healing'].map(
                    (name) => (
                      <div key={name} className="card-surface p-4 opacity-60 transition-all">
                        <div className="text-3xl mb-2" aria-hidden="true">{getModalityIcon(name)}</div>
                        <h3 className="font-medium text-sm">{name}</h3>
                        <span className="text-xs text-text/30 mt-1 block">Coming Soon</span>
                      </div>
                    ),
                  )}
            </div>
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
              'SAMHSA Treatment Improvement Protocols for crisis resource standards',
            ]}
          />
        </section>
      </div>
    </main>
  );
}
