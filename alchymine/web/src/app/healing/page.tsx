'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Button from '@/components/shared/Button';

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
  { name: 'Breathwork', icon: '🌬️', status: 'active', path: '#breathwork' },
  { name: 'Coherence Meditation', icon: '🧘', status: 'active', path: '#' },
  { name: 'Language Awareness', icon: '📝', status: 'coming', path: '#' },
  { name: 'Resilience Training', icon: '💪', status: 'coming', path: '#' },
  { name: 'Sound Healing', icon: '🔔', status: 'coming', path: '#' },
  { name: 'Somatic Practice', icon: '🫀', status: 'coming', path: '#' },
  { name: 'Nature Healing', icon: '🌲', status: 'coming', path: '#' },
  { name: 'Sleep Healing', icon: '🌙', status: 'coming', path: '#' },
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
    <main className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-white/5 bg-surface/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-gradient-gold font-bold text-xl">
            Alchymine
          </Link>
          <span className="text-text/50 text-sm">Healing System</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-gradient-gold mb-4">
            Ethical Healing
          </h1>
          <p className="text-text/60 text-lg max-w-2xl mx-auto">
            Personalized modalities matched to your unique profile. Evidence-informed,
            culturally sensitive, with full safety protocols.
          </p>
        </div>

        {/* Breathwork Timer */}
        {isRunning && pattern ? (
          <div className="card-surface p-8 mb-12 text-center">
            <h2 className="text-2xl font-bold mb-2">{pattern.name}</h2>
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
          <div className="mb-12" id="breathwork">
            <h2 className="text-2xl font-bold mb-6">Breathwork Sessions</h2>
            <div className="grid md:grid-cols-3 gap-6">
              {Object.entries(PATTERNS).map(([key, p]) => (
                <div key={key} className="card-surface p-6 hover:glow-gold transition-all">
                  <h3 className="text-lg font-semibold text-primary mb-2">{p.name}</h3>
                  <p className="text-text/50 text-sm mb-4">{p.description}</p>
                  <p className="text-text/40 text-xs mb-4">
                    {p.phases.map((ph) => `${ph.label} ${ph.duration}s`).join(' → ')} · {p.cycles} cycles
                  </p>
                  <Button variant="primary" size="sm" onClick={() => startSession(key)}>
                    Start
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Modalities Grid */}
        <h2 className="text-2xl font-bold mb-6">Healing Modalities</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {HEALING_MODALITIES.map((mod) => (
            <div
              key={mod.name}
              className={`card-surface p-4 ${mod.status === 'active' ? 'hover:glow-gold cursor-pointer' : 'opacity-50'} transition-all`}
            >
              <div className="text-3xl mb-2">{mod.icon}</div>
              <h3 className="font-medium text-sm">{mod.name}</h3>
              {mod.status === 'coming' && (
                <span className="text-xs text-text/30 mt-1 block">Coming Soon</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
