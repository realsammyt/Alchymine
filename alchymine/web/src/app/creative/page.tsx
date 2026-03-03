"use client";

import { useMemo } from "react";
import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import { getCreativeStyle, StyleFingerprintResponse } from "@/lib/api";
import { useApi, getStoredIntake } from "@/lib/useApi";

const CREATIVE_DIMENSIONS = [
  {
    name: "Divergent Thinking",
    description:
      "Ability to generate multiple ideas, explore possibilities, and make unexpected connections.",
    traits: ["Fluency", "Flexibility", "Originality", "Elaboration"],
  },
  {
    name: "Convergent Thinking",
    description:
      "Ability to evaluate ideas, find optimal solutions, and refine concepts into actionable plans.",
    traits: ["Analysis", "Synthesis", "Evaluation", "Decision-making"],
  },
  {
    name: "Creative Temperament",
    description:
      "Personality traits that support creative expression, including openness, tolerance for ambiguity, and intrinsic motivation.",
    traits: ["Openness", "Persistence", "Risk tolerance", "Curiosity"],
  },
];

const STYLE_PROFILES = [
  {
    name: "The Architect",
    description:
      "Structured creativity through careful planning, systems design, and methodical execution.",
    icon: "\u{1F3DB}\u{FE0F}",
  },
  {
    name: "The Explorer",
    description:
      "Creativity through experimentation, boundary-pushing, and embracing the unknown.",
    icon: "\u{1F9ED}",
  },
  {
    name: "The Connector",
    description:
      "Creativity through synthesizing ideas from different domains and building bridges between concepts.",
    icon: "\u{1F517}",
  },
  {
    name: "The Alchemist",
    description:
      "Creativity through transformation, taking raw materials and transmuting them into something entirely new.",
    icon: "\u{2697}\u{FE0F}",
  },
];

const PROJECT_TYPES = [
  {
    name: "Solo Projects",
    description:
      "Individual creative works matched to your style profile and strengths.",
    status: "available",
  },
  {
    name: "Collaborative Works",
    description:
      "Team projects that pair complementary creative styles for maximum output.",
    status: "coming-soon",
  },
  {
    name: "Creative Challenges",
    description:
      "Time-boxed prompts and constraints designed to stretch your creative abilities.",
    status: "coming-soon",
  },
];

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="font-body text-sm text-text/60 w-28 text-right">
        {label}
      </span>
      <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-secondary-dark via-secondary to-secondary-light transition-all duration-700"
          style={{ width: `${Math.min(value * 100, 100)}%` }}
        />
      </div>
      <span className="font-body text-sm font-mono text-secondary w-10">
        {Math.round(value * 100)}
      </span>
    </div>
  );
}

export default function CreativePage() {
  const intake = useMemo(() => getStoredIntake(), []);
  const hasIntake = !!intake?.intention;

  const style = useApi<StyleFingerprintResponse>(
    hasIntake ? () => getCreativeStyle({ intention: intake!.intention }) : null,
    [intake?.intention],
  );

  return (
    <main className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <MotionReveal delay={0}>
          <header className="mb-10">
            <h1 className="font-display text-display-md font-light text-gradient-purple mb-3">
              Creative Development
            </h1>
            <hr className="rule-gold mb-4" aria-hidden="true" />
            <p className="font-body text-text/50 text-base max-w-2xl">
              Guilford-based creative assessment to discover your Creative DNA,
              style profile, and tools for sustained creative output.
            </p>
          </header>
        </MotionReveal>

        {/* Personalized Style Fingerprint */}
        {hasIntake && (
          <MotionReveal delay={0.1}>
            <section className="mb-12" aria-labelledby="your-creative-heading">
              <h2
                id="your-creative-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{2728}"}
                </span>
                Your Creative Fingerprint
              </h2>
              <hr className="rule-gold mb-6" aria-hidden="true" />
              <ApiStateView
                loading={style.loading}
                error={style.error}
                empty={!style.data}
                loadingText="Analyzing your creative profile..."
                emptyText="Complete the full assessment to discover your Creative DNA and style fingerprint."
                onRetry={style.refetch}
              >
                {style.data && (
                  <div className="card-surface-elevated glow-purple p-6 space-y-6">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-secondary/10 flex items-center justify-center text-3xl">
                        {STYLE_PROFILES.find((p) =>
                          p.name
                            .toLowerCase()
                            .includes(style.data!.creative_style.toLowerCase()),
                        )?.icon ?? "\u{1F3A8}"}
                      </div>
                      <div>
                        <h3 className="font-display text-xl font-light text-gradient-purple">
                          {style.data.creative_style}
                        </h3>
                        <p className="font-body text-sm text-text/50">
                          Overall Score:{" "}
                          {Math.round(style.data.overall_score * 100)}%
                        </p>
                      </div>
                    </div>

                    {/* Guilford Scores */}
                    {style.data.guilford_summary &&
                      Object.keys(style.data.guilford_summary).length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                            Guilford Scores
                          </h4>
                          {Object.entries(style.data.guilford_summary).map(
                            ([key, val]) => (
                              <ScoreBar
                                key={key}
                                label={key}
                                value={Number(val) || 0}
                              />
                            ),
                          )}
                        </div>
                      )}

                    <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                      <div>
                        <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                          Strengths
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {style.data.strengths.map((s) => (
                            <span
                              key={s}
                              className="px-3 py-1 bg-secondary/10 text-secondary text-xs rounded-full"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                          Growth Areas
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {style.data.growth_areas.map((g) => (
                            <span
                              key={g}
                              className="px-3 py-1 bg-white/5 text-text/50 text-xs rounded-full"
                            >
                              {g}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {style.data.recommended_mediums.length > 0 && (
                      <div className="pt-4 border-t border-white/5">
                        <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                          Recommended Mediums
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {style.data.recommended_mediums.map((m) => (
                            <span
                              key={m}
                              className="px-3 py-1 bg-accent/10 text-accent text-xs rounded-full"
                            >
                              {m}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </ApiStateView>
            </section>
          </MotionReveal>
        )}

        {/* Creative Assessment Section */}
        <MotionReveal delay={0.2}>
          <section className="mb-12" aria-labelledby="assessment-heading">
            <h2
              id="assessment-heading"
              className="section-heading-sm mb-2 flex items-center gap-3"
            >
              <span
                className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{1F9EA}"}
              </span>
              Creative Assessment
            </h2>
            <hr className="rule-gold mb-4" aria-hidden="true" />
            <p className="font-body text-text/50 text-sm mb-6">
              The assessment measures three dimensions of creativity based on
              J.P. Guilford&apos;s Structure of Intellect model. Each dimension
              reveals different aspects of your creative potential.
            </p>

            <MotionStagger className="grid sm:grid-cols-3 gap-4 mb-4">
              {CREATIVE_DIMENSIONS.map((dimension) => (
                <MotionStaggerItem key={dimension.name}>
                  <div className="card-surface p-5 h-full transition-all duration-300 hover:glow-purple hover:-translate-y-1">
                    <h3 className="font-display text-sm font-semibold text-secondary mb-2">
                      {dimension.name}
                    </h3>
                    <p className="font-body text-sm text-text/50 leading-relaxed mb-3">
                      {dimension.description}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {dimension.traits.map((trait) => (
                        <span
                          key={trait}
                          className="px-2 py-0.5 bg-secondary/10 text-secondary/70 text-[10px] font-medium rounded-full"
                        >
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>

            <MethodologyPanel
              title="Creative Assessment"
              methodology="The creative assessment is based on J.P. Guilford's Structure of Intellect (SOI) model, specifically the divergent production operations. Assessment items measure fluency (quantity of ideas), flexibility (category shifts), originality (statistical rarity of responses), and elaboration (detail and development). Scoring uses normative data from published creativity research. The Creative DNA profile synthesizes assessment results with personality data (Big Five Openness) from the Intelligence system."
              evidenceLevel="strong"
              calculationType="hybrid"
              sources={[
                'Guilford, J.P. (1967) "The Nature of Human Intelligence" - foundational creativity model',
                'Torrance, E.P. (1974) "Torrance Tests of Creative Thinking" - validated assessment methodology',
                'Runco, M.A. & Acar, S. (2012) "Divergent Thinking as an Indicator of Creative Potential" - meta-analysis',
                "Big Five Openness to Experience as creativity predictor - Kaufman et al. (2016)",
              ]}
            />
          </section>
        </MotionReveal>

        {/* Style Profile Section */}
        <MotionReveal delay={0.1}>
          <section className="mb-12" aria-labelledby="style-heading">
            <h2
              id="style-heading"
              className="section-heading-sm mb-2 flex items-center gap-3"
            >
              <span
                className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{1F3A8}"}
              </span>
              Creative Style Profiles
            </h2>
            <hr className="rule-gold mb-4" aria-hidden="true" />
            <p className="font-body text-text/50 text-sm mb-6">
              Your creative style profile is derived from your assessment
              results, personality data, and preferred modes of expression.
            </p>

            <MotionStagger className="grid sm:grid-cols-2 gap-4">
              {STYLE_PROFILES.map((profile) => (
                <MotionStaggerItem key={profile.name}>
                  <div className="card-surface p-5 h-full">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl" aria-hidden="true">
                        {profile.icon}
                      </span>
                      <h3 className="font-display text-sm font-semibold text-secondary">
                        {profile.name}
                      </h3>
                    </div>
                    <p className="font-body text-sm text-text/50 leading-relaxed">
                      {profile.description}
                    </p>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>
          </section>
        </MotionReveal>

        {/* Projects & Collaboration Section */}
        <MotionReveal delay={0.1}>
          <section className="mb-12" aria-labelledby="projects-heading">
            <h2
              id="projects-heading"
              className="section-heading-sm mb-2 flex items-center gap-3"
            >
              <span
                className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{1F4DD}"}
              </span>
              Projects &amp; Collaboration
            </h2>
            <hr className="rule-gold mb-6" aria-hidden="true" />

            <MotionStagger className="grid sm:grid-cols-3 gap-4">
              {PROJECT_TYPES.map((project) => (
                <MotionStaggerItem key={project.name}>
                  <div
                    className={`card-surface-elevated p-5 h-full ${project.status === "coming-soon" ? "opacity-60" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-display text-sm font-semibold text-text">
                        {project.name}
                      </h3>
                      {project.status === "coming-soon" && (
                        <span className="px-2 py-0.5 bg-secondary/10 text-secondary/60 text-[10px] font-medium rounded-full">
                          Coming Soon
                        </span>
                      )}
                    </div>
                    <p className="font-body text-sm text-text/50 leading-relaxed">
                      {project.description}
                    </p>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>
          </section>
        </MotionReveal>

        {/* CTA */}
        <MotionReveal delay={0.1}>
          <div className="text-center">
            <a
              href="/discover/intake"
              className="inline-flex items-center gap-2 px-6 py-3 min-h-[44px] bg-gradient-to-r from-secondary-dark via-secondary to-secondary-light text-white font-body font-semibold rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-100"
            >
              {hasIntake
                ? "Update Your Creative Profile"
                : "Discover Your Creative DNA"}
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </a>
          </div>
        </MotionReveal>
      </div>
    </main>
  );
}
