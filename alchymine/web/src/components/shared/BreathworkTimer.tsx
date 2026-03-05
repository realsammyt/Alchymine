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

export interface BreathworkCompletionData {
  duration_seconds: number;
  cycles: number;
  pattern_name: string;
}

interface BreathworkTimerProps {
  pattern: BreathworkPattern;
  onComplete: (data: BreathworkCompletionData) => void;
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

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

// ── Reduced-motion text instructions ────────────────────────────

function TextInstructions({
  pattern,
  currentPhaseIndex,
  currentCycle,
  timeRemaining,
  isRunning,
  onStart,
  onStop,
}: {
  pattern: BreathworkPattern;
  currentPhaseIndex: number;
  currentCycle: number;
  timeRemaining: number;
  isRunning: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  const currentPhase = pattern.phases[currentPhaseIndex];
  const phaseColor = getHexColor(currentPhase.color);

  if (!isRunning) {
    return (
      <div className="card-surface p-8 text-center" data-testid="breathwork-ready">
        <h2 className="font-display text-2xl font-light mb-2 text-text">
          {pattern.name}
        </h2>
        <p className="font-body text-sm text-text/50 mb-4">{pattern.description}</p>
        <div className="card-surface-elevated p-4 rounded-xl mb-6 text-left">
          <p className="font-body text-xs text-text/40 mb-3 uppercase tracking-wider">
            Instructions
          </p>
          {pattern.phases.map((phase, idx) => (
            <div key={idx} className="flex items-center gap-3 mb-2">
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-body flex-shrink-0"
                style={{
                  background: `${getHexColor(phase.color)}20`,
                  color: getHexColor(phase.color),
                  border: `1px solid ${getHexColor(phase.color)}40`,
                }}
              >
                {idx + 1}
              </span>
              <span className="font-body text-sm text-text/70">
                {phase.label} for {phase.duration} seconds
              </span>
            </div>
          ))}
          <p className="font-body text-xs text-text/40 mt-3">
            Repeat {pattern.cycles} times
          </p>
        </div>
        <div className="flex gap-3 justify-center">
          <button
            onClick={onStart}
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
      className="card-surface p-8 text-center"
      role="timer"
      aria-live="polite"
      data-testid="breathwork-active"
    >
      <h2 className="font-display text-xl font-light text-text mb-1">
        {pattern.name}
      </h2>
      <p className="font-body text-sm text-text/50 mb-6">
        Cycle {currentCycle} of {pattern.cycles}
      </p>

      {/* Large text instruction */}
      <div className="mb-8">
        <p
          className="font-display text-4xl font-light mb-2"
          style={{ color: phaseColor }}
          aria-label={`Current phase: ${currentPhase.label}`}
        >
          {currentPhase.label}
        </p>
        <p
          className="font-display text-6xl font-light text-text"
          aria-label={`${Math.ceil(timeRemaining)} seconds remaining`}
        >
          {Math.ceil(timeRemaining)}
        </p>
        <p className="font-body text-xs text-text/40 mt-1">seconds</p>
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

      <Button variant="ghost" onClick={onStop}>
        End Session
      </Button>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────

export default function BreathworkTimer({
  pattern,
  onComplete,
  onStop,
}: BreathworkTimerProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(pattern.phases[0].duration);
  const [currentCycle, setCurrentCycle] = useState(1);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [completedCycles, setCompletedCycles] = useState(0);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    if (mq.addEventListener) {
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, []);

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
    setElapsedSeconds(0);

    cleanup();

    startTimeRef.current = Date.now();
    let phaseIdx = 0;
    let cycle = 1;
    let remaining = pattern.phases[0].duration;

    intervalRef.current = setInterval(() => {
      remaining -= 0.1;
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));

      if (remaining <= 0) {
        phaseIdx++;
        if (phaseIdx >= pattern.phases.length) {
          phaseIdx = 0;
          cycle++;
          if (cycle > pattern.cycles) {
            clearInterval(intervalRef.current!);
            intervalRef.current = null;
            const duration = Math.floor(
              (Date.now() - startTimeRef.current) / 1000,
            );
            setElapsedSeconds(duration);
            setCompletedCycles(pattern.cycles);
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
        <p className="font-body text-sm text-text/50 mb-4">{pattern.name}</p>

        {/* Session summary */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-white/[0.03] rounded-xl p-3">
            <div
              className="font-display text-xl font-light text-gradient-teal"
              aria-label={`${completedCycles} cycles completed`}
            >
              {completedCycles}
            </div>
            <div className="font-body text-xs text-text/40 mt-0.5">Cycles</div>
          </div>
          <div className="bg-white/[0.03] rounded-xl p-3">
            <div
              className="font-display text-xl font-light text-gradient-teal"
              aria-label={`${formatDuration(elapsedSeconds)} total duration`}
            >
              {formatDuration(elapsedSeconds)}
            </div>
            <div className="font-body text-xs text-text/40 mt-0.5">Duration</div>
          </div>
          <div className="bg-white/[0.03] rounded-xl p-3">
            <div className="font-display text-xl font-light text-gradient-teal">
              {pattern.phases.length}
            </div>
            <div className="font-body text-xs text-text/40 mt-0.5">Phases</div>
          </div>
        </div>

        <p className="font-body text-sm text-text/40 mb-6">
          Great work nurturing your nervous system.
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="primary" onClick={() => startSession()}>
            Repeat Session
          </Button>
          <Button
            variant="ghost"
            onClick={() =>
              onComplete({
                duration_seconds: elapsedSeconds,
                cycles: completedCycles,
                pattern_name: pattern.name,
              })
            }
          >
            Done
          </Button>
        </div>
      </div>
    );
  }

  // Render text-only instructions for prefers-reduced-motion
  if (prefersReducedMotion) {
    return (
      <TextInstructions
        pattern={pattern}
        currentPhaseIndex={currentPhaseIndex}
        currentCycle={currentCycle}
        timeRemaining={timeRemaining}
        isRunning={isRunning}
        onStart={startSession}
        onStop={stopSession}
      />
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
        {/* Outer pulse ring */}
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

      {/* Session elapsed time */}
      <p className="font-body text-xs text-text/30 mb-4" aria-live="off">
        {formatDuration(elapsedSeconds)} elapsed
      </p>

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
