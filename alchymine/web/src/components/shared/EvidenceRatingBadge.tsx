export type EvidenceLevel =
  | "strong"
  | "moderate"
  | "emerging"
  | "traditional"
  | "entertainment";

interface EvidenceRatingBadgeProps {
  level: EvidenceLevel;
  showTooltip?: boolean;
}

const levelConfig: Record<
  EvidenceLevel,
  {
    label: string;
    description: string;
    className: string;
    dotCount: number;
    disclaimer?: string;
  }
> = {
  strong: {
    label: "Peer-Reviewed",
    description:
      "Supported by peer-reviewed research, meta-analyses, or widely replicated studies.",
    className: "bg-accent/10 text-accent border-accent/20",
    dotCount: 4,
  },
  moderate: {
    label: "Emerging Research",
    description:
      "Supported by multiple studies with consistent findings, though more research may be needed.",
    className: "bg-primary/10 text-primary border-primary/20",
    dotCount: 3,
  },
  emerging: {
    label: "Theoretical",
    description:
      "Preliminary studies show promise, but the evidence base is still developing.",
    className: "bg-secondary/10 text-secondary border-secondary/20",
    dotCount: 2,
  },
  traditional: {
    label: "Cultural/Historical",
    description:
      "Based on historical and cultural traditions. Valued for personal meaning, not empirical claims.",
    className: "bg-white/5 text-text/60 border-white/10",
    dotCount: 1,
  },
  entertainment: {
    label: "Entertainment",
    description:
      "Provided for entertainment and self-reflection purposes only. Not based on empirical evidence.",
    className: "bg-white/5 text-text/40 border-white/10",
    dotCount: 0,
    disclaimer: "For entertainment purposes only",
  },
};

export default function EvidenceRatingBadge({
  level,
  showTooltip = true,
}: EvidenceRatingBadgeProps) {
  const config = levelConfig[level];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${config.className}`}
      role="img"
      aria-label={`Evidence level: ${config.label}. ${showTooltip ? config.description : ""}`}
      title={showTooltip ? config.description : undefined}
    >
      {/* Evidence dots — entertainment level shows no filled dots */}
      <span className="flex items-center gap-0.5" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <span
            key={i}
            className={`w-1.5 h-1.5 rounded-full ${
              i < config.dotCount ? "bg-current" : "bg-current/20"
            }`}
          />
        ))}
      </span>
      {config.disclaimer ? (
        <em className="not-italic">{config.label}</em>
      ) : (
        config.label
      )}
    </span>
  );
}
