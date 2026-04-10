"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Button from "@/components/shared/Button";

// ── Types ────────────────────────────────────────────────────────────

export interface BreathPhase {
  label: string;
  seconds: number;
}

export interface BreathPattern {
  name: string;
  description: string;
  phases: BreathPhase[];
  cycles: number;
}

interface BreathworkGuideProps {
  /** Breath pattern to run. */
  pattern: BreathPattern;
  /** Called when all cycles are completed. */
  onComplete?: (durationSeconds: number) => void;
  /** Called when user exits early. */
  onExit?: () => void;
}

// ── Default patterns from common YAML skills ────────────────────────

export const DEFAULT_PATTERNS: BreathPattern[] = [
  {
    name: "Box Breathing (4-4-4-4)",
    description: "Equal inhale, hold, exhale, hold pattern used by Navy SEALs.",
    phases: [
      { label: "Inhale", seconds: 4 },
      { label: "Hold", seconds: 4 },
      { label: "Exhale", seconds: 4 },
      { label: "Hold", seconds: 4 },
    ],
    cycles: 8,
  },
  {
    name: "4-7-8 Relaxation",
    description: "A calming pattern that extends the exhale for deeper relaxation.",
    phases: [
      { label: "Inhale", seconds: 4 },
      { label: "Hold", seconds: 7 },
      { label: "Exhale", seconds: 8 },
    ],
    cycles: 4,
  },
  {
    name: "Coherence Breathing",
    description: "Simple 5-in, 5-out rhythm for heart-rate variability coherence.",
    phases: [
      { label: "Inhale", seconds: 5 },
      { label: "Exhale", seconds: 5 },
    ],
    cycles: 12,
  },
];

// ── Phase → circle scale mapping ────────────────────────────────────

function getScale(label: string, progress: number): number {
  const normalized = label.toLowerCase();
  if (normalized === "inhale") return 0.55 + progress * 0.45;
  if (normalized === "exhale") return 1.0 - progress * 0.45;
  return 0.75; // hold phases stay mid-size
}

function getPhaseColor(label: string): string {
  const normalized = label.toLowerCase();
  if (normalized === "inhale") return "#20b2aa";
  if (normalized === "exhale") return "#7b2d8e";
  return "#DAA520"; // hold
}

// ── Component ────────────────────────────────────────────────────────

export default function BreathworkGuide({
  pattern,
  onComplete,
  onExit,
}: BreathworkGuideProps) {
  const [state, setState] = useState<"idle" | "running" | "done">("idle");
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [cycle, setCycle] = useState(1);
  const [elapsed, setElapsed] = useState(0); // within current phase
  const [totalElapsed, setTotalElapsed] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);
  const stateRef = useRef({ phaseIndex: 0, cycle: 1, elapsed: 0 });

  const currentPhase = pattern.phases[phaseIndex];
  const phaseDuration = currentPhase.seconds;
  const progress = Math.min(elapsed / phaseDuration, 1);
  const scale = getScale(currentPhase.label, progress);
  const color = getPhaseColor(currentPhase.label);

  // Sync ref with state
  useEffect(() => {
    stateRef.current = { phaseIndex, cycle, elapsed };
  }, [phaseIndex, cycle, elapsed]);

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const tick = useCallback(
    (now: number) => {
      const dt = (now - lastTickRef.current) / 1000;
      lastTickRef.current = now;
      const { phaseIndex: pi, cycle: cy, elapsed: el } = stateRef.current;

      const newElapsed = el + dt;
      const phase = pattern.phases[pi];

      if (newElapsed >= phase.seconds) {
        // Advance to next phase
        let nextPhase = pi + 1;
        let nextCycle = cy;
        if (nextPhase >= pattern.phases.length) {
          nextPhase = 0;
          nextCycle = cy + 1;
          if (nextCycle > pattern.cycles) {
            // Session complete
            stop();
            setState("done");
            return;
          }
          setCycle(nextCycle);
        }
        setPhaseIndex(nextPhase);
        setElapsed(0);
        setTotalElapsed((t) => t + dt);
        stateRef.current = { phaseIndex: nextPhase, cycle: nextCycle, elapsed: 0 };
      } else {
        setElapsed(newElapsed);
        setTotalElapsed((t) => t + dt);
        stateRef.current = { ...stateRef.current, elapsed: newElapsed };
      }

      rafRef.current = requestAnimationFrame(tick);
    },
    [pattern, stop],
  );

  const start = useCallback(() => {
    setState("running");
    setPhaseIndex(0);
    setCycle(1);
    setElapsed(0);
    setTotalElapsed(0);
    stateRef.current = { phaseIndex: 0, cycle: 1, elapsed: 0 };
    lastTickRef.current = performance.now();
    rafRef.current = requestAnimationFrame(tick);
  }, [tick]);

  useEffect(() => {
    return stop;
  }, [stop]);

  // ── Idle / pre-start ────────────────────────────────────────────

  if (state === "idle") {
    return (
      <div className="card-surface p-6 text-center" data-testid="breathwork-guide-idle">
        <h2 className="font-display text-xl font-light text-text mb-1">
          {pattern.name}
        </h2>
        <p className="font-body text-sm text-text/50 mb-4">{pattern.description}</p>

        <div className="flex flex-wrap justify-center gap-2 mb-4">
          {pattern.phases.map((ph, i) => (
            <span
              key={i}
              className="px-2.5 py-1 rounded-full text-xs font-body border border-white/10 text-text/60"
            >
              {ph.label} {ph.seconds}s
            </span>
          ))}
          <span className="px-2.5 py-1 rounded-full text-xs font-body border border-white/10 text-text/40">
            {pattern.cycles} cycles
          </span>
        </div>

        <div className="flex gap-3 justify-center">
          <Button variant="primary" onClick={start}>
            Begin
          </Button>
          {onExit && (
            <Button variant="ghost" onClick={onExit}>
              Back
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ── Done ────────────────────────────────────────────────────────

  if (state === "done") {
    const totalSec = Math.round(totalElapsed);
    return (
      <div className="card-surface p-6 text-center" data-testid="breathwork-guide-done">
        <h2 className="font-display text-xl font-light mb-2">
          <span className="text-gradient-teal">Session Complete</span>
        </h2>
        <p className="font-body text-sm text-text/50 mb-2">{pattern.name}</p>
        <p className="font-body text-xs text-text/40 mb-4">
          {pattern.cycles} cycles in {Math.floor(totalSec / 60)}m {totalSec % 60}s
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="primary" onClick={start}>
            Repeat
          </Button>
          <Button
            variant="ghost"
            onClick={() => onComplete?.(totalSec)}
          >
            Done
          </Button>
        </div>
      </div>
    );
  }

  // ── Running ─────────────────────────────────────────────────────

  const remaining = Math.max(0, phaseDuration - elapsed);

  return (
    <div
      className="card-surface p-6 text-center"
      role="timer"
      aria-live="polite"
      data-testid="breathwork-guide-running"
    >
      <p className="font-body text-xs text-text/40 mb-6">
        Cycle {cycle} of {pattern.cycles}
      </p>

      {/* Animated circle */}
      <div className="relative w-48 h-48 mx-auto mb-6">
        {/* Background ring */}
        <svg className="absolute inset-0" viewBox="0 0 200 200" aria-hidden="true">
          <circle
            cx="100"
            cy="100"
            r="90"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="3"
          />
          <circle
            cx="100"
            cy="100"
            r="90"
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 90}`}
            strokeDashoffset={`${2 * Math.PI * 90 * (1 - progress)}`}
            className="transition-none"
            style={{ opacity: 0.5, transform: "rotate(-90deg)", transformOrigin: "center" }}
          />
        </svg>

        {/* Breathing circle */}
        <div
          className="absolute rounded-full"
          style={{
            inset: 18,
            background: `radial-gradient(circle at center, ${color}20, ${color}08)`,
            border: `2px solid ${color}44`,
            transform: `scale(${scale})`,
            transition: "transform 0.05s linear",
          }}
          aria-hidden="true"
        />

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-body text-sm uppercase tracking-wider"
            style={{ color }}
            aria-label={`Phase: ${currentPhase.label}`}
          >
            {currentPhase.label}
          </span>
          <span
            className="font-display text-3xl font-light mt-1 text-text"
            aria-label={`${Math.ceil(remaining)} seconds remaining`}
          >
            {Math.ceil(remaining)}
          </span>
        </div>
      </div>

      {/* Phase indicators */}
      <div className="flex justify-center gap-2 mb-4 flex-wrap">
        {pattern.phases.map((ph, idx) => (
          <span
            key={idx}
            className={`px-2.5 py-1 rounded-full text-xs font-body transition-all duration-200 ${
              idx === phaseIndex
                ? "font-semibold border"
                : "text-text/30 border border-transparent"
            }`}
            style={
              idx === phaseIndex
                ? {
                    color: getPhaseColor(ph.label),
                    background: `${getPhaseColor(ph.label)}18`,
                    borderColor: `${getPhaseColor(ph.label)}30`,
                  }
                : undefined
            }
          >
            {ph.label} {ph.seconds}s
          </span>
        ))}
      </div>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          stop();
          setState("idle");
          onExit?.();
        }}
      >
        End Session
      </Button>
    </div>
  );
}
