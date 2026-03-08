"use client";

import { MotionReveal } from "@/components/shared/MotionReveal";

const SYSTEM_MESSAGES: Record<string, string> = {
  Intelligence:
    "Calculating your numerology, astrology, and personality profile...",
  Healing: "Matching therapeutic modalities to your unique profile...",
  Wealth: "Analyzing your wealth archetype and financial levers...",
  Creative: "Exploring your creative orientation and strengths...",
  Perspective: "Assessing your developmental stage and cognitive patterns...",
};

interface GeneratingStateProps {
  systemName: string;
}

export default function GeneratingState({ systemName }: GeneratingStateProps) {
  const message =
    SYSTEM_MESSAGES[systemName] ?? "Generating your personalized results...";

  return (
    <MotionReveal>
      <div
        className="card-surface p-10 text-center max-w-lg mx-auto"
        role="status"
        aria-live="polite"
      >
        {/* Animated spinner orb */}
        <div className="relative w-20 h-20 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full bg-primary/[0.08] animate-pulse" />
          <div
            className="absolute inset-1.5 rounded-full border-2 border-transparent border-t-primary border-r-primary/50 animate-spin"
            style={{ animationDuration: "3s" }}
          />
          <div className="absolute inset-3 rounded-full bg-gradient-to-br from-primary-dark/20 to-secondary-dark/20" />
        </div>

        <h3 className="font-display text-lg font-light text-text/80 mb-2">
          Report in Progress
        </h3>
        <p className="font-body text-sm text-text/50 mb-4">{message}</p>
        <p className="font-body text-xs text-text/30">
          This may take a moment. Your results will appear here when ready.
        </p>
      </div>
    </MotionReveal>
  );
}
