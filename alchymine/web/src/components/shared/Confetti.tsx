"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";

const PARTICLE_COUNT = 30;

const COLORS = [
  "#f0c050", // gold
  "#daa520", // amber gold
  "#b8860b", // dark gold
  "#ffffff", // white
  "#fffacd", // lemon chiffon
];

type Particle = {
  id: number;
  x: number;
  color: string;
  delay: number;
  duration: number;
  size: number;
  drift: number;
};

let idCounter = 0;

function createParticles(): Particle[] {
  return Array.from({ length: PARTICLE_COUNT }, () => ({
    id: idCounter++,
    x: Math.random() * 100,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    delay: Math.random() * 0.4,
    duration: 1.6 + Math.random() * 0.8,
    size: 4 + Math.floor(Math.random() * 5),
    drift: (Math.random() - 0.5) * 60,
  }));
}

/**
 * Lightweight confetti burst component.
 *
 * Usage:
 *   const ref = useRef<ConfettiHandle>(null);
 *   <Confetti ref={ref} />
 *   ref.current?.trigger();
 *
 * Or use the named export `triggerConfetti` with a container ref.
 */

type ConfettiProps = {
  /** Called by parent to trigger a confetti burst */
  active?: boolean;
};

/**
 * Renders confetti when `active` transitions to true.
 * Falls back to a gold glow when prefers-reduced-motion is set.
 */
export function Confetti({ active = false }: ConfettiProps) {
  const [particles, setParticles] = useState<Particle[]>([]);
  const [reducedMotion, setReducedMotion] = useState(false);
  const prevActive = useRef(false);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (active && !prevActive.current) {
      setParticles(createParticles());
      // Clear after animation completes
      const timeout = window.setTimeout(() => setParticles([]), 3000);
      prevActive.current = true;
      return () => window.clearTimeout(timeout);
    }
    if (!active) {
      prevActive.current = false;
    }
  }, [active, forceUpdate]);

  if (particles.length === 0) return null;

  // Reduced motion fallback: gold glow pulse
  if (reducedMotion) {
    return (
      <div
        className="pointer-events-none fixed inset-0 z-[9999] flex items-center justify-center"
        aria-hidden="true"
      >
        <div
          style={{
            width: 200,
            height: 200,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(218,165,32,0.4) 0%, transparent 70%)",
            animation: "confetti-glow 1s ease-out forwards",
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[9999] overflow-hidden"
      aria-hidden="true"
    >
      {particles.map((p) => (
        <div
          key={p.id}
          style={
            {
              position: "absolute",
              left: `${p.x}%`,
              top: "-10px",
              width: p.size,
              height: p.size * 1.6,
              backgroundColor: p.color,
              borderRadius: 2,
              animationName: "confetti-fall",
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`,
              animationTimingFunction: "ease-in",
              animationFillMode: "forwards",
              "--drift": `${p.drift}px`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}

/**
 * Hook-based trigger for programmatic confetti bursts.
 * Returns `[active, trigger]` — pass `active` to <Confetti active={active} />.
 */
export function useConfetti(): [boolean, () => void] {
  const [active, setActive] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const trigger = useCallback(() => {
    setActive(false);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    // rAF to ensure React processes the false → true transition
    requestAnimationFrame(() => {
      setActive(true);
      timeoutRef.current = setTimeout(() => setActive(false), 3000);
    });
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return [active, trigger];
}
