"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Button from "@/components/shared/Button";

// ── Types ─────────────────────────────────────────────────────────

interface BreathworkPhase {
  label: string;
  duration: number;
  color: string;
}

interface BreathworkPattern {
  name: string;
  phases: BreathworkPhase[];
  cycles: number;
  description: string;
}

interface BreathworkTimerProps {
  pattern: BreathworkPattern;
  onComplete: () => void;
  onStop: () => void;
}

// ── Phase color to CSS hex map ───────────────────────────────────

const COLOR_MAP: Record<string, string> = {
  "text-accent": "#20b2aa",
  "text-primary": "#DAA520",
  "text-secondary": "#7b2d8e",
};

function getHexColor(colorClass: string): string {
  return COLOR_MAP[colorClass] || "#DAA520";
}

// ── Component ─────────────────────────────────────────────────────

export default function BreathworkTimer({
  pattern,
  onComplete,
  onStop,
}: BreathworkTimerProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(
    pattern.phases[0].duration,
  );
  const [currentCycle, setCurrentCycle] = useState(1);
  const [sessionComplete, setSessionComplete] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  function startSession() {
    setIsRunning(true);
    setCurrentPhaseIndex(0);
    setCurrentCycle(1);
    setTimeRemaining(pattern.phases[0].duration);
    setSessionComplete(false);

    cleanup();

    let phaseIdx = 0;
    let cycle = 1;
    let remaining = pattern.phases[0].duration;

    intervalRef.current = setInterval(() => {
      remaining -= 0.1;

      if (remaining <= 0) {
        phaseIdx++;
        if (phaseIdx >= pattern.phases.length) {
          phaseIdx = 0;
          cycle++;
          if (cycle > pattern.cycles) {
            clearInterval(intervalRef.current!);
            intervalRef.current = null;
            setIsRunning(false);
            setSessionComplete(true);
            return;
          }
          setCurrentCycle(cycle);
        }
        remaining = pattern.phases[phaseIdx].duration;
        setCurrentPhaseIndex(phaseIdx);
      }

      setTimeRemaining(Math.max(0, remaining));
    }, 100);
  }

  function stopSession() {
    cleanup();
    setIsRunning(false);
    onStop();
  }

  const currentPhase = pattern.phases[currentPhaseIndex];
  const phaseColor = getHexColor(currentPhase.color);
  const totalPhaseDuration = currentPhase.duration;
  const progress =
    ((totalPhaseDuration - timeRemaining) / totalPhaseDuration) * 100;

  // Calculate the circle scale based on phase
  const circleScale =
    currentPhase.label === "Inhale"
      ? 0.7 + (progress / 100) * 0.3
      : currentPhase.label === "Exhale"
        ? 1.0 - (progress / 100) * 0.3
        : 0.85;

  // Inhale phase gets teal glow; other phases use a softer version
  const isInhale = currentPhase.label === "Inhale";

  if (sessionComplete) {
    return (
      <div
        className="card-surface p-8 text-center"
        data-testid="breathwork-complete"
      >
        <div className="text-4xl mb-4" aria-hidden="true">
          {"\u{2728}"}
        </div>
        <h2 className="font-display text-2xl font-light mb-2">
          <span className="text-gradient-teal">Session Complete</span>
        </h2>
        <p className="font-body text-sm text-text/50 mb-2">{pattern.name}</p>
        <p className="font-body text-sm text-text/40 mb-6">
          {pattern.cycles} cycles completed. Great work nurturing your nervous
          system.
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="primary" onClick={() => startSession()}>
            Repeat Session
          </Button>
          <Button variant="ghost" onClick={onComplete}>
            Done
          </Button>
        </div>
      </div>
    );
  }

  if (!isRunning) {
    return (
      <div
        className="card-surface p-8 text-center"
        data-testid="breathwork-ready"
      >
        <h2 className="font-display text-2xl font-light mb-2 text-text">
          {pattern.name}
        </h2>
        <p className="font-body text-sm text-text/50 mb-4">
          {pattern.description}
        </p>
        <p className="font-body text-xs text-text/40 mb-6">
          {pattern.phases
            .map((ph) => `${ph.label} ${ph.duration}s`)
            .join(" \u2192 ")}{" "}
          {"\u00B7"} {pattern.cycles} cycles
        </p>
        <div className="flex gap-3 justify-center">
          {/* Teal gradient start button */}
          <button
            onClick={startSession}
            className="inline-flex items-center justify-center gap-2 font-body font-medium tracking-wide transition-all duration-300 ease-out px-6 py-3 text-base rounded-xl touch-target bg-gradient-to-r from-accent-dark via-accent to-accent-light text-bg hover:shadow-[0_0_30px_rgba(32,178,170,0.25)] hover:scale-[1.02] active:scale-[0.98]"
          >
            Begin
          </button>
          <Button variant="ghost" onClick={onStop}>
            Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="card-surface p-8 text-center backdrop-blur-xl"
      role="timer"
      aria-live="polite"
      data-testid="breathwork-active"
    >
      <h2 className="font-display text-xl font-light text-text mb-1">
        {pattern.name}
      </h2>
      <p className="font-body text-sm text-text/50 mb-8">
        Cycle {currentCycle} of {pattern.cycles}
      </p>

      {/* Animated breathing circle */}
      <div className="relative w-52 h-52 mx-auto mb-8">
        {/* Outer pulse ring — teal-tinted, pulses with animate-glow-breathe */}
        <div
          className={`absolute inset-0 rounded-full animate-glow-breathe ${isInhale ? "glow-teal" : ""}`}
          style={{
            border: `2px solid ${phaseColor}33`,
          }}
          aria-hidden="true"
        />

        {/* Progress ring (SVG) */}
        <svg
          className="absolute inset-0 -rotate-90"
          viewBox="0 0 208 208"
          aria-hidden="true"
        >
          <circle
            cx="104"
            cy="104"
            r="96"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="4"
          />
          <circle
            cx="104"
            cy="104"
            r="96"
            fill="none"
            stroke={phaseColor}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 96}`}
            strokeDashoffset={`${2 * Math.PI * 96 * (1 - progress / 100)}`}
            className="transition-all duration-100"
            style={{ opacity: 0.6 }}
          />
        </svg>

        {/* Breathing circle that scales */}
        <div
          className="absolute rounded-full"
          style={{
            inset: 20,
            background: `radial-gradient(circle at center, ${phaseColor}20, ${phaseColor}08)`,
            border: `3px solid ${phaseColor}44`,
            transform: `scale(${circleScale})`,
            transition: "transform 0.1s linear",
          }}
          aria-hidden="true"
        />

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-body text-sm tracking-wider uppercase"
            style={{ color: phaseColor }}
            aria-label={`Current phase: ${currentPhase.label}`}
          >
            {currentPhase.label}
          </span>
          <span
            className="font-display text-3xl font-light mt-1 text-text"
            aria-label={`${Math.ceil(timeRemaining)} seconds remaining`}
          >
            {Math.ceil(timeRemaining)}
          </span>
          <span className="font-body text-xs text-text/40 mt-0.5">sec</span>
        </div>
      </div>

      {/* Phase indicators */}
      <div
        className="flex justify-center gap-2 mb-6 flex-wrap"
        role="group"
        aria-label="Breathing phases"
      >
        {pattern.phases.map((phase, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-1 px-3 py-1 rounded-full font-body text-xs transition-all duration-300 ${
              idx === currentPhaseIndex
                ? "border"
                : "border border-transparent text-text/30"
            }`}
            style={
              idx === currentPhaseIndex
                ? {
                    background: `${getHexColor(phase.color)}22`,
                    color: getHexColor(phase.color),
                    borderColor: `${getHexColor(phase.color)}44`,
                    fontWeight: 600,
                  }
                : undefined
            }
            aria-current={idx === currentPhaseIndex ? "true" : undefined}
          >
            {phase.label} {phase.duration}s
          </div>
        ))}
      </div>

      <Button variant="ghost" onClick={stopSession}>
        End Session
      </Button>
    </div>
  );
}
