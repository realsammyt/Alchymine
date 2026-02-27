'use client';

import { useState, useEffect, useRef } from 'react';
import Button from '@/components/shared/Button';
import MethodologyPanel from '@/components/shared/MethodologyPanel';

interface BreathworkPhase {
  label: string;
  duration: number; // seconds
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

const HEALING_MODALITIES = [
  { name: 'Breathwork', icon: '\u{1F32C}\u{FE0F}', status: 'active', path: '#breathwork' },
  { name: 'Coherence Meditation', icon: '\u{1F9D8}', status: 'active', path: '#' },
  { name: 'Language Awareness', icon: '\u{1F4DD}', status: 'coming', path: '#' },
  { name: 'Resilience Training', icon: '\u{1F4AA}', status: 'coming', path: '#' },
  { name: 'Sound Healing', icon: '\u{1F514}', status: 'coming', path: '#' },
  { name: 'Somatic Practice', icon: '\u{1FAC0}', status: 'coming', path: '#' },
  { name: 'Nature Healing', icon: '\u{1F332}', status: 'coming', path: '#' },
  { name: 'Sleep Healing', icon: '\u{1F319}', status: 'coming', path: '#' },
];

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

export default function HealingPage() {
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [currentCycle, setCurrentCycle] = useState(1);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const pattern = selectedPattern ? PATTERNS[selectedPattern] : null;

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  function startSession(patternKey: string) {
    const p = PATTERNS[patternKey];
    setSelectedPattern(patternKey);
    setIsRunning(true);
    setCurrentPhaseIndex(0);
    setCurrentCycle(1);
    setTimeRemaining(p.phases[0].duration);

    if (intervalRef.current) clearInterval(intervalRef.current);

    let phaseIdx = 0;
    let cycle = 1;
    let remaining = p.phases[0].duration;

    intervalRef.current = setInterval(() => {
      remaining -= 0.1;

      if (remaining <= 0) {
        phaseIdx++;
        if (phaseIdx >= p.phases.length) {
          phaseIdx = 0;
          cycle++;
          if (cycle > p.cycles) {
            // Session complete
            clearInterval(intervalRef.current!);
            setIsRunning(false);
            setSelectedPattern(null);
            return;
          }
          setCurrentCycle(cycle);
        }
        remaining = p.phases[phaseIdx].duration;
        setCurrentPhaseIndex(phaseIdx);
      }

      setTimeRemaining(Math.max(0, remaining));
    }, 100);
  }

  function stopSession() {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setIsRunning(false);
    setSelectedPattern(null);
  }

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
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

        {/* Breathwork Timer */}
        <section className="mb-12" aria-labelledby="breathwork-heading">
          {isRunning && pattern ? (
            <div className="card-surface p-8 text-center" role="timer" aria-live="polite">
              <h2 id="breathwork-heading" className="text-2xl font-bold mb-2">{pattern.name}</h2>
              <p className="text-text/50 mb-8">Cycle {currentCycle} of {pattern.cycles}</p>

              {/* Breathing circle */}
              <div className="relative w-48 h-48 mx-auto mb-8">
                <div
                  className={`absolute inset-0 rounded-full border-4 ${pattern.phases[currentPhaseIndex].color} border-current transition-all duration-500`}
                  style={{
                    transform: `scale(${pattern.phases[currentPhaseIndex].label === 'Inhale' ? 1 : pattern.phases[currentPhaseIndex].label === 'Exhale' ? 0.7 : 0.85})`,
                  }}
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-3xl font-bold ${pattern.phases[currentPhaseIndex].color}`}>
                    {pattern.phases[currentPhaseIndex].label}
                  </span>
                  <span className="text-text/60 text-xl mt-2">
                    {Math.ceil(timeRemaining)}s
                  </span>
                </div>
              </div>

              <Button variant="ghost" onClick={stopSession}>
                End Session
              </Button>
            </div>
          ) : (
            /* Pattern Selection */
            <div id="breathwork">
              <h2 id="breathwork-heading" className="text-2xl font-bold mb-6">Breathwork Sessions</h2>
              <div className="grid md:grid-cols-3 gap-6">
                {Object.entries(PATTERNS).map(([key, p]) => (
                  <div key={key} className="card-surface p-6 hover:glow-gold transition-all">
                    <h3 className="text-lg font-semibold text-primary mb-2">{p.name}</h3>
                    <p className="text-text/50 text-sm mb-4">{p.description}</p>
                    <p className="text-text/40 text-xs mb-4">
                      {p.phases.map((ph) => `${ph.label} ${ph.duration}s`).join(' \u2192 ')} \u00B7 {p.cycles} cycles
                    </p>
                    <Button variant="primary" size="sm" onClick={() => startSession(key)}>
                      Start
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Modalities Grid */}
        <section className="mb-12" aria-labelledby="modalities-heading">
          <h2 id="modalities-heading" className="text-2xl font-bold mb-6">Healing Modalities</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            {HEALING_MODALITIES.map((mod) => (
              <div
                key={mod.name}
                className={`card-surface p-4 ${mod.status === 'active' ? 'hover:glow-gold cursor-pointer' : 'opacity-50'} transition-all`}
              >
                <div className="text-3xl mb-2" aria-hidden="true">{mod.icon}</div>
                <h3 className="font-medium text-sm">{mod.name}</h3>
                {mod.status === 'coming' && (
                  <span className="text-xs text-text/30 mt-1 block">Coming Soon</span>
                )}
              </div>
            ))}
          </div>

          <MethodologyPanel
            title="Healing Modalities"
            methodology="Healing modalities are matched to user profiles based on attachment style, personality traits, and stated intentions. Breathwork protocols follow established patterns (Box Breathing, Coherence, 4-7-8) with fixed timing cycles. Modality recommendations are AI-assisted but grounded in evidence-based frameworks. All sessions include safety protocols and crisis resource access."
            evidenceLevel="moderate"
            calculationType="hybrid"
            sources={[
              'Zaccaro et al. (2018) \"How Breath-Control Can Change Your Life\" - systematic review of breathwork effects on autonomic nervous system',
              'McCraty & Zayas (2014) \"Cardiac coherence, self-regulation\" - HeartMath Institute research on coherence breathing',
              'Weil, A. \"4-7-8 Breathing Technique\" - clinical observations on relaxation response',
              'SAMHSA Treatment Improvement Protocols for crisis resource standards',
            ]}
          />
        </section>

        {/* Crisis Resources */}
        <section className="mb-12" aria-labelledby="crisis-heading">
          <h2 id="crisis-heading" className="text-2xl font-bold mb-6 flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center" aria-hidden="true">
              <svg className="w-5 h-5 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
                <path d="M12 8v4" />
                <path d="M12 16h.01" />
              </svg>
            </span>
            Crisis Resources
          </h2>
          <p className="text-text/50 text-sm mb-4">
            If you or someone you know is in crisis, these resources are available 24/7. You are not alone.
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {CRISIS_RESOURCES.map((resource) => (
              <div key={resource.name} className="card-surface p-5 border-l-2 border-red-400/30">
                <h3 className="text-sm font-semibold text-text mb-1">{resource.name}</h3>
                <p className="text-primary font-bold text-sm mb-2">{resource.contact}</p>
                <p className="text-xs text-text/40">{resource.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
