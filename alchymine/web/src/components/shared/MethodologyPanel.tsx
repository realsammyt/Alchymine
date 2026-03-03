"use client";

import { useState } from "react";
import EvidenceRatingBadge, { type EvidenceLevel } from "./EvidenceRatingBadge";

interface MethodologyPanelProps {
  title: string;
  methodology: string;
  evidenceLevel: EvidenceLevel;
  calculationType: "deterministic" | "ai-assisted" | "hybrid";
  sources?: string[];
  defaultExpanded?: boolean;
}

const calculationTypeConfig: Record<
  string,
  { label: string; description: string; className: string }
> = {
  deterministic: {
    label: "Deterministic",
    description:
      "Results are calculated using fixed mathematical formulas. No AI interpretation involved.",
    className: "bg-accent/10 text-accent border-accent/20",
  },
  "ai-assisted": {
    label: "AI-Assisted",
    description:
      "Results use AI interpretation guided by validated frameworks and safety protocols.",
    className: "bg-secondary/10 text-secondary border-secondary/20",
  },
  hybrid: {
    label: "Hybrid",
    description:
      "Deterministic calculations enhanced with AI-generated narrative and context.",
    className: "bg-primary/10 text-primary border-primary/20",
  },
};

export default function MethodologyPanel({
  title,
  methodology,
  evidenceLevel,
  calculationType,
  sources = [],
  defaultExpanded = false,
}: MethodologyPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const calcConfig = calculationTypeConfig[calculationType];

  return (
    <div className="card-surface border border-white/5 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
        aria-expanded={expanded}
        aria-controls={`methodology-content-${title.replace(/\s+/g, "-").toLowerCase()}`}
      >
        <div className="flex items-center gap-3">
          <svg
            className="w-4 h-4 text-text/40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          <span className="text-sm font-medium text-text/70">
            {title} — Methodology & Evidence
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-text/40 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {expanded && (
        <div
          id={`methodology-content-${title.replace(/\s+/g, "-").toLowerCase()}`}
          className="px-4 pb-4 animate-fade-in"
          role="region"
          aria-label={`${title} methodology details`}
        >
          <div className="border-t border-white/5 pt-4 space-y-4">
            {/* Evidence and Calculation Type badges */}
            <div className="flex flex-wrap items-center gap-2">
              <EvidenceRatingBadge level={evidenceLevel} />
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${calcConfig.className}`}
              >
                <svg
                  className="w-3 h-3"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  {calculationType === "deterministic" ? (
                    <>
                      <rect x="4" y="4" width="16" height="16" rx="2" />
                      <path d="M8 10h8" />
                      <path d="M8 14h4" />
                    </>
                  ) : calculationType === "ai-assisted" ? (
                    <>
                      <path d="M12 2a4 4 0 0 0-4 4v1a4 4 0 0 0-4 4c0 1.5.8 2.8 2 3.4V18a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-3.6c1.2-.6 2-1.9 2-3.4a4 4 0 0 0-4-4V6a4 4 0 0 0-4-4z" />
                    </>
                  ) : (
                    <>
                      <circle cx="12" cy="12" r="10" />
                      <path d="m8 12 3 3 5-5" />
                    </>
                  )}
                </svg>
                {calcConfig.label}
              </span>
            </div>

            {/* Calculation type explanation */}
            <p className="text-xs text-text/40">{calcConfig.description}</p>

            {/* Methodology text */}
            <div>
              <h4 className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-2">
                How it works
              </h4>
              <p className="text-sm text-text/60 leading-relaxed">
                {methodology}
              </p>
            </div>

            {/* Sources */}
            {sources.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-2">
                  Sources & References
                </h4>
                <ul className="space-y-1">
                  {sources.map((source, i) => (
                    <li
                      key={i}
                      className="text-xs text-text/40 flex items-start gap-2"
                    >
                      <span
                        className="text-primary/50 mt-0.5"
                        aria-hidden="true"
                      >
                        [{i + 1}]
                      </span>
                      {source}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
