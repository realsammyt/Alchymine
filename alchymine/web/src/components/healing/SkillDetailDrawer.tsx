"use client";

import { useEffect, useRef, useCallback } from "react";
import { useApi } from "@/lib/useApi";
import { getHealingSkill, HealingSkill } from "@/lib/api";
import Button from "@/components/shared/Button";

// ── Evidence rating display ─────────────────────────────────────────

const EVIDENCE_LABELS: Record<string, { label: string; color: string }> = {
  A: { label: "Strong (RCT / Meta-Analytic)", color: "#22c55e" },
  B: { label: "Moderate (Controlled Studies)", color: "#eab308" },
  C: { label: "Limited (Observational)", color: "#f97316" },
  D: { label: "Traditional / Anecdotal", color: "#a78bfa" },
};

function EvidenceTag({ rating }: { rating: string }) {
  const info = EVIDENCE_LABELS[rating] ?? {
    label: rating,
    color: "#94a3b8",
  };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-body font-medium"
      style={{
        background: `${info.color}18`,
        color: info.color,
        border: `1px solid ${info.color}30`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: info.color }}
        aria-hidden="true"
      />
      {info.label}
    </span>
  );
}

// ── Props ────────────────────────────────────────────────────────────

interface SkillDetailDrawerProps {
  /** Skill name slug to fetch detail for. `null` closes the drawer. */
  skillName: string | null;
  /** Called when the drawer should close. */
  onClose: () => void;
  /** Optional callback when user wants to start a practice. */
  onStartPractice?: (skill: HealingSkill) => void;
}

// ── Component ────────────────────────────────────────────────────────

export default function SkillDetailDrawer({
  skillName,
  onClose,
  onStartPractice,
}: SkillDetailDrawerProps) {
  const open = skillName !== null;
  const drawerRef = useRef<HTMLDivElement>(null);

  const { data: skill, loading, error } = useApi<HealingSkill>(
    skillName ? (signal) => getHealingSkill(skillName) : null,
    [skillName],
  );

  // Close on Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) onClose();
    },
    [open, onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Trap focus inside drawer when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
          data-testid="drawer-backdrop"
          aria-hidden="true"
        />
      )}

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal={open}
        aria-label={skill?.title ?? "Skill details"}
        className={`fixed top-0 right-0 h-full w-full max-w-md bg-bg border-l border-white/10 z-50 transform transition-transform duration-300 ease-out overflow-y-auto ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        data-testid="skill-detail-drawer"
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg/90 backdrop-blur-md border-b border-white/5 px-6 py-4 flex items-center justify-between z-10">
          <h2 className="font-display text-lg font-light text-text truncate">
            {loading ? "Loading..." : skill?.title ?? "Skill Detail"}
          </h2>
          <button
            onClick={onClose}
            className="text-text/40 hover:text-text/70 transition-colors p-1"
            aria-label="Close drawer"
            data-testid="drawer-close"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {loading && (
            <div className="animate-pulse space-y-4" data-testid="drawer-loading">
              <div className="h-4 bg-white/10 rounded w-3/4" />
              <div className="h-4 bg-white/10 rounded w-1/2" />
              <div className="h-20 bg-white/10 rounded" />
            </div>
          )}

          {error && (
            <div className="text-red-400 font-body text-sm" data-testid="drawer-error">
              Failed to load skill: {error}
            </div>
          )}

          {skill && !loading && (
            <>
              {/* Meta badges */}
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-body bg-white/5 text-text/60 border border-white/10">
                  {skill.modality.replace(/_/g, " ")}
                </span>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-body bg-white/5 text-text/60 border border-white/10">
                  {skill.duration_minutes} min
                </span>
                <EvidenceTag rating={skill.evidence_rating} />
              </div>

              {/* Description */}
              <div>
                <h3 className="font-body text-xs text-text/40 uppercase tracking-wider mb-2">
                  Description
                </h3>
                <p className="font-body text-sm text-text/70 leading-relaxed">
                  {skill.description}
                </p>
              </div>

              {/* Steps */}
              <div>
                <h3 className="font-body text-xs text-text/40 uppercase tracking-wider mb-3">
                  Steps
                </h3>
                <ol className="space-y-3">
                  {skill.steps.map((step, idx) => (
                    <li key={idx} className="flex gap-3">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/15 text-accent text-xs font-body flex items-center justify-center border border-accent/25 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="font-body text-sm text-text/70 leading-relaxed">
                        {step}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Contraindications */}
              {skill.contraindications.length > 0 && (
                <div>
                  <h3 className="font-body text-xs text-text/40 uppercase tracking-wider mb-2">
                    Contraindications
                  </h3>
                  <ul className="space-y-1.5">
                    {skill.contraindications.map((ci, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 font-body text-sm text-red-400/80"
                      >
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-red-400/60 flex-shrink-0" />
                        {ci}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action button */}
              {onStartPractice && (
                <div className="pt-2">
                  <Button
                    variant="primary"
                    className="w-full"
                    onClick={() => onStartPractice(skill)}
                  >
                    Start Practice
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
