"use client";

import { useApi } from "@/lib/useApi";
import {
  getHealingSpiralRoute,
  HealingSpiralRouteResponse,
} from "@/lib/api";

// ── System display mapping ──────────────────────────────────────────

const SYSTEM_LABELS: Record<string, { label: string; icon: string }> = {
  intelligence: { label: "Personalized Intelligence", icon: "\u{1F9E0}" },
  healing: { label: "Ethical Healing", icon: "\u{1F33F}" },
  wealth: { label: "Generational Wealth", icon: "\u{1F4B0}" },
  creative: { label: "Creative Development", icon: "\u{1F3A8}" },
  perspective: { label: "Perspective Enhancement", icon: "\u{1F52D}" },
};

const EVIDENCE_COLORS: Record<string, string> = {
  strong: "#22c55e",
  moderate: "#eab308",
  emerging: "#f97316",
  traditional: "#a78bfa",
};

// ── Props ───────────────────────────────────────────────────────────

interface SpiralBannerProps {
  /** User's primary intention for routing. */
  intention?: string;
  /** Numerology life path number. */
  lifePath?: number;
  /** Big Five openness score. */
  personalityOpenness?: number;
  /** Big Five neuroticism score. */
  personalityNeuroticism?: number;
}

// ── Component ───────────────────────────────────────────────────────

export default function SpiralBanner({
  intention = "health",
  lifePath,
  personalityOpenness,
  personalityNeuroticism,
}: SpiralBannerProps) {
  const { data, loading, error } = useApi<HealingSpiralRouteResponse>(
    (signal) =>
      getHealingSpiralRoute({
        intention,
        lifePath,
        personalityOpenness,
        personalityNeuroticism,
      }),
    [intention, lifePath, personalityOpenness, personalityNeuroticism],
  );

  // Loading state
  if (loading) {
    return (
      <div
        className="card-surface border border-accent/10 p-6 animate-pulse"
        data-testid="spiral-banner-loading"
        role="status"
        aria-label="Loading spiral recommendations"
      >
        <div className="h-5 bg-white/10 rounded w-1/3 mb-3" />
        <div className="h-4 bg-white/10 rounded w-2/3 mb-2" />
        <div className="h-4 bg-white/10 rounded w-1/2" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="card-surface border border-red-400/20 p-6"
        data-testid="spiral-banner-error"
        role="alert"
      >
        <p className="font-body text-sm text-red-400">
          Could not load spiral recommendations.
        </p>
      </div>
    );
  }

  if (!data) return null;

  const primaryInfo = SYSTEM_LABELS[data.primary_system] ?? {
    label: data.primary_system,
    icon: "\u{2728}",
  };

  return (
    <section
      className="card-surface border border-accent/10 p-6 glow-teal"
      data-testid="spiral-banner"
      aria-labelledby="spiral-banner-heading"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2
            id="spiral-banner-heading"
            className="font-display text-lg font-light text-text/80 flex items-center gap-2"
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
                aria-hidden="true"
              >
                <path d="M12 2a10 10 0 0 1 0 20 10 10 0 0 1 0-20" />
                <path d="M12 2a7 7 0 0 1 0 14 7 7 0 0 1 0-14" />
                <path d="M12 2a4 4 0 0 1 0 8 4 4 0 0 1 0-8" />
              </svg>
            </span>
            Your Alchemical Spiral
          </h2>
          <p className="font-body text-sm text-text/40 mt-1 ml-10">
            Personalized recommendations based on your profile
          </p>
        </div>

        {/* Primary system badge */}
        <div
          className="flex-shrink-0 text-center"
          aria-label={`Primary system: ${primaryInfo.label}`}
        >
          <span className="text-2xl" aria-hidden="true">
            {primaryInfo.icon}
          </span>
          <p className="font-body text-[0.65rem] text-text/40 mt-0.5">
            Primary
          </p>
        </div>
      </div>

      {/* Healing stage info */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-body text-sm font-medium text-text/70">
            Healing System
          </h3>
          <div className="flex items-center gap-2">
            <span
              className="font-body text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20"
              aria-label={`Rank ${data.healing_rank} of 5`}
            >
              #{data.healing_rank} of 5
            </span>
            <span
              className="font-body text-xs text-accent/70"
              aria-label={`Score ${Math.round(data.healing_score)}`}
            >
              {Math.round(data.healing_score)}%
            </span>
          </div>
        </div>
        <p className="font-body text-sm text-text/50 leading-relaxed">
          {data.healing_reason}
        </p>
        <p className="font-body text-xs text-accent mt-2">
          {data.healing_entry_action}
        </p>
      </div>

      {/* For You Today */}
      <div className="bg-accent/5 border border-accent/10 rounded-xl p-4 mb-5">
        <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
          For You Today
        </p>
        <p className="font-body text-sm text-text/70 leading-relaxed">
          {data.for_you_today}
        </p>
      </div>

      {/* Recommended modalities */}
      {data.recommended_modalities.length > 0 && (
        <div>
          <h3 className="font-body text-xs text-text/40 uppercase tracking-wider mb-3">
            Recommended Modalities
          </h3>
          <ul
            className="grid sm:grid-cols-2 gap-3"
            role="list"
            aria-label="Recommended healing modalities"
          >
            {data.recommended_modalities.map((mod) => {
              const evColor =
                EVIDENCE_COLORS[mod.evidence_level] ?? "#94a3b8";
              return (
                <li
                  key={mod.modality}
                  className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 hover:border-accent/20 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-body text-sm font-medium text-text/70">
                      {mod.modality.replace(/_/g, " ")}
                    </h4>
                    <span
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.65rem] font-body"
                      style={{
                        background: `${evColor}15`,
                        color: evColor,
                        border: `1px solid ${evColor}25`,
                      }}
                      aria-label={`Evidence: ${mod.evidence_level}`}
                    >
                      <span
                        className="w-1 h-1 rounded-full"
                        style={{ background: evColor }}
                        aria-hidden="true"
                      />
                      {mod.evidence_level}
                    </span>
                  </div>
                  <p className="font-body text-xs text-text/40 leading-relaxed line-clamp-2">
                    {mod.description}
                  </p>
                  <span className="font-body text-[0.65rem] text-text/25 mt-1 inline-block">
                    {mod.category}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
