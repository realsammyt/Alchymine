"use client";

import { useState, useCallback } from "react";
import Link from "next/link";

// ── Types ─────────────────────────────────────────────────────────

interface SystemRecommendation {
  system: string;
  score: number;
  reason: string;
  entry_action: string;
  priority: number;
}

interface SpiralRouteResult {
  primary_system: string;
  recommendations: SystemRecommendation[];
  for_you_today: string;
  evidence_level: string;
  calculation_type: string;
  methodology: string;
}

// ── Constants ─────────────────────────────────────────────────────

const GUIDED_INTENTIONS = [
  {
    key: "self-understanding",
    label: "I want to understand myself better",
    icon: "\u{1F52E}",
    category: "intelligence",
  },
  {
    key: "financial-decision",
    label: "I need to make a financial decision",
    icon: "\u{1F4B0}",
    category: "wealth",
  },
  {
    key: "creative-block",
    label: "I'm feeling stuck creatively",
    icon: "\u{1F3A8}",
    category: "creative",
  },
  {
    key: "emotional-healing",
    label: "I want to heal emotionally",
    icon: "\u{1F331}",
    category: "healing",
  },
  {
    key: "career-direction",
    label: "I need career direction",
    icon: "\u{1F4BC}",
    category: "intelligence",
  },
  {
    key: "build-wealth",
    label: "I want to build generational wealth",
    icon: "\u{1F48E}",
    category: "wealth",
  },
  {
    key: "perspective-shift",
    label: "I want to see things differently",
    icon: "\u{1F52D}",
    category: "perspective",
  },
  {
    key: "relationship-growth",
    label: "I want to improve my relationships",
    icon: "\u{2764}\u{FE0F}",
    category: "healing",
  },
  {
    key: "find-purpose",
    label: "I want to find my purpose",
    icon: "\u{1F9ED}",
    category: "intelligence",
  },
  {
    key: "legacy-planning",
    label: "I want to build a lasting legacy",
    icon: "\u{1F3DB}\u{FE0F}",
    category: "wealth",
  },
];

/** System metadata aligned to the Alchymine design system color tokens. */
const SYSTEM_META: Record<
  string,
  {
    label: string;
    color: string;
    accentText: string;
    accentBg: string;
    accentBorder: string;
    icon: string;
    path: string;
    tagline: string;
  }
> = {
  intelligence: {
    label: "Personalized Intelligence",
    color: "#DAA520",
    accentText: "text-primary",
    accentBg: "bg-primary/10",
    accentBorder: "border-primary/20",
    icon: "\u{1F52E}",
    path: "/intelligence",
    tagline: "Know yourself deeply",
  },
  healing: {
    label: "Ethical Healing",
    color: "#20B2AA",
    accentText: "text-accent",
    accentBg: "bg-accent/10",
    accentBorder: "border-accent/20",
    icon: "\u{1F331}",
    path: "/healing",
    tagline: "Heal with integrity",
  },
  wealth: {
    label: "Generational Wealth",
    color: "#DAA520",
    accentText: "text-primary",
    accentBg: "bg-primary/10",
    accentBorder: "border-primary/20",
    icon: "\u{1F48E}",
    path: "/wealth",
    tagline: "Build lasting prosperity",
  },
  creative: {
    label: "Creative Development",
    color: "#9B4DCA",
    accentText: "text-secondary-light",
    accentBg: "bg-secondary/10",
    accentBorder: "border-secondary/20",
    icon: "\u{1F3A8}",
    path: "/creative",
    tagline: "Express your vision",
  },
  perspective: {
    label: "Perspective Enhancement",
    color: "#7B2D8E",
    accentText: "text-secondary",
    accentBg: "bg-secondary/10",
    accentBorder: "border-secondary/20",
    icon: "\u{1F52D}",
    path: "/perspective",
    tagline: "Expand your worldview",
  },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Spiral Visual ─────────────────────────────────────────────────
// The spiral animation requires dynamic colors, so inline styles are necessary here.

function SpiralVisual({
  active,
  primarySystem,
}: {
  active: boolean;
  primarySystem: string | null;
}) {
  const color = primarySystem
    ? SYSTEM_META[primarySystem]?.color || "#DAA520"
    : "#DAA520";

  return (
    <div
      className="spiral-visual-container relative w-[200px] h-[200px] mx-auto mb-8"
      aria-hidden="true"
    >
      {/* Outer glow ring */}
      <div
        className={`absolute inset-0 rounded-full ${active ? "animate-spiral-pulse" : ""}`}
        style={{
          background: `radial-gradient(circle at center, ${color}15 0%, transparent 70%)`,
        }}
      />
      {/* Middle ring */}
      <div
        className={`absolute rounded-full ${active ? "animate-spiral-rotate" : ""}`}
        style={{
          inset: 20,
          border: `2px solid ${color}33`,
          background: `conic-gradient(from 0deg, ${color}11, ${color}22, ${color}11, transparent)`,
        }}
      />
      {/* Inner ring */}
      <div
        className={`absolute rounded-full ${active ? "animate-spiral-rotate-reverse" : ""}`}
        style={{
          inset: 45,
          border: `2px solid ${color}55`,
          background: `conic-gradient(from 180deg, ${color}22, ${color}33, ${color}22, transparent)`,
        }}
      />
      {/* Core circle */}
      <div
        className={`absolute rounded-full flex items-center justify-center ${active ? "animate-spiral-pulse-fast" : ""}`}
        style={{
          inset: 70,
          background: `radial-gradient(circle at center, ${color}44, ${color}22)`,
        }}
      >
        <span className="text-2xl">
          {primarySystem
            ? SYSTEM_META[primarySystem]?.icon || "\u{2728}"
            : "\u{2728}"}
        </span>
      </div>
      {/* Five system dots around the spiral */}
      {Object.entries(SYSTEM_META).map(([key, meta], i) => {
        const angle = (i * 72 - 90) * (Math.PI / 180);
        const radius = 88;
        const x = 100 + radius * Math.cos(angle) - 8;
        const y = 100 + radius * Math.sin(angle) - 8;
        const isActive = primarySystem === key;
        return (
          <div
            key={key}
            className="absolute w-4 h-4 rounded-full transition-all duration-400"
            style={{
              left: x,
              top: y,
              background: isActive ? meta.color : `${meta.color}44`,
              border: isActive
                ? `2px solid ${meta.color}`
                : "1px solid transparent",
              transform: isActive ? "scale(1.4)" : "scale(1)",
              boxShadow: isActive ? `0 0 12px ${meta.color}66` : "none",
            }}
          />
        );
      })}
    </div>
  );
}

// ── Recommendation Card ──────────────────────────────────────────

function RecommendationCard({
  rec,
  isPrimary,
}: {
  rec: SystemRecommendation;
  isPrimary: boolean;
}) {
  const meta = SYSTEM_META[rec.system];
  if (!meta) return null;

  return (
    <Link href={meta.path} className="block no-underline text-inherit group">
      <div
        className={`card-surface border-l-4 px-5 py-5 sm:px-6 transition-all duration-300 hover:-translate-y-0.5 ${
          isPrimary ? "glow-gold" : ""
        }`}
        style={{ borderLeftColor: meta.color }}
        role="article"
        aria-label={`${meta.label} recommendation`}
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-[10px] flex items-center justify-center text-xl flex-shrink-0"
              style={{ background: `${meta.color}15` }}
            >
              {meta.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-display text-[0.95rem] font-medium text-text">
                  {meta.label}
                </h4>
                {isPrimary && (
                  <span
                    className="text-[0.65rem] font-body font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full"
                    style={{
                      background: `${meta.color}22`,
                      color: meta.color,
                    }}
                  >
                    Best Match
                  </span>
                )}
              </div>
              <p className="text-xs font-body text-text/30 mt-0.5">
                {meta.tagline}
              </p>
            </div>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="mb-3">
          <div className="flex justify-between mb-1">
            <span className="text-[0.7rem] font-body text-text/30 uppercase tracking-wide">
              Confidence
            </span>
            <span
              className="text-[0.8rem] font-body font-semibold"
              style={{ color: meta.color }}
            >
              {rec.score.toFixed(0)}%
            </span>
          </div>
          <div
            className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round(rec.score)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${meta.label} confidence`}
          >
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${rec.score}%`,
                background: `linear-gradient(90deg, ${meta.color}88, ${meta.color})`,
              }}
            />
          </div>
        </div>

        {/* Reason */}
        <p className="font-body text-sm text-text/40 leading-relaxed mb-2">
          {rec.reason}
        </p>

        {/* Action link */}
        <span
          className="font-body text-sm font-medium opacity-70 group-hover:opacity-100 transition-opacity"
          style={{ color: meta.color }}
        >
          {rec.entry_action} &rarr;
        </span>
      </div>
    </Link>
  );
}

// ── Component ─────────────────────────────────────────────────────

export default function SpiralHub() {
  const [selectedIntention, setSelectedIntention] = useState<string | null>(
    null,
  );
  const [routeResult, setRouteResult] = useState<SpiralRouteResult | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getRoute = useCallback(async (intentionKey: string) => {
    setSelectedIntention(intentionKey);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/spiral/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intention: intentionKey }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SpiralRouteResult = await res.json();
      setRouteResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get routing");
    } finally {
      setLoading(false);
    }
  }, []);

  const primarySystem = routeResult?.primary_system || null;

  return (
    <div className="max-w-[820px] mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-6">
        <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.15em] mb-3">
          Your Transformation Hub
        </p>
        <h1 className="font-display text-display-md font-light text-text mb-2">
          The Alchemical Spiral
        </h1>
        <hr className="rule-gold my-4 max-w-[60px] mx-auto" />
        <p className="font-body text-text/40 max-w-[560px] mx-auto text-sm leading-relaxed">
          Choose what matters most to you right now, and we will guide you to
          the highest-leverage system for your growth.
        </p>
      </div>

      {/* Spiral Visual */}
      <SpiralVisual
        active={loading || !!routeResult}
        primarySystem={primarySystem}
      />

      {/* Intention Selection */}
      <div className="mb-8">
        <h2 className="text-xs font-body font-medium text-text/30 text-center mb-4 uppercase tracking-[0.08em]">
          What brings you here today?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {GUIDED_INTENTIONS.map(({ key, label, icon }) => {
            const isSelected = selectedIntention === key;
            return (
              <button
                key={key}
                onClick={() => getRoute(key)}
                aria-pressed={isSelected}
                data-testid={`intention-${key}`}
                className={`touch-target flex items-center gap-3 px-4 py-3.5 rounded-xl text-left font-body text-sm font-medium text-text transition-all duration-300 ${
                  isSelected
                    ? "bg-primary/10 border-2 border-primary"
                    : "bg-surface border border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.03]"
                }`}
              >
                <span className="text-xl flex-shrink-0">{icon}</span>
                <span className="leading-snug">{label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className="text-center py-10"
          role="status"
          aria-label="Calculating optimal path"
        >
          <div className="w-10 h-10 border-2 border-white/[0.08] border-t-primary rounded-full mx-auto mb-4 animate-spin" />
          <p className="font-body text-sm text-text/35">
            Calculating your optimal path...
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 bg-primary-dark/[0.08] border border-primary-dark/[0.18] text-primary-dark text-sm font-body rounded-xl px-4 py-3 mb-4"
        >
          <svg
            className="w-4 h-4 flex-shrink-0 mt-0.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {/* Route Results */}
      {routeResult && !loading && (
        <div data-testid="spiral-results" className="space-y-6">
          {/* For You Today */}
          <div
            className="card-surface-elevated p-6"
            style={{
              background: `linear-gradient(135deg, ${SYSTEM_META[routeResult.primary_system]?.color || "#DAA520"}18, var(--tw-surface-elevated, #22223A))`,
            }}
          >
            <h3 className="text-xs font-body font-medium text-text/30 uppercase tracking-[0.05em] mb-2">
              For You Today
            </h3>
            <p className="font-body text-base text-text leading-relaxed">
              {routeResult.for_you_today}
            </p>
          </div>

          {/* System Rankings */}
          <div>
            <h3 className="text-xs font-body font-medium text-text/30 uppercase tracking-[0.08em] mb-4">
              Your Systems, Ranked
            </h3>
            <div className="flex flex-col gap-3">
              {routeResult.recommendations.map((rec) => (
                <RecommendationCard
                  key={rec.system}
                  rec={rec}
                  isPrimary={rec.priority === 1}
                />
              ))}
            </div>
          </div>

          {/* Methodology */}
          <div className="bg-surface rounded-xl px-5 py-4 border border-white/[0.06]">
            <p className="font-body text-xs text-text/30 leading-relaxed">
              <strong className="text-text/50">Methodology:</strong>{" "}
              {routeResult.methodology}
            </p>
            <p className="font-body text-xs text-text/25 mt-1">
              Evidence: {routeResult.evidence_level} | Calculation:{" "}
              {routeResult.calculation_type}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
