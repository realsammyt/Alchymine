"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  getKeganAssessment,
  getProfile,
  KeganAssessResponse,
  ProfileResponse,
} from "@/lib/api";
import { useApi, useIntake, useReportStatus } from "@/lib/useApi";
import { useAuth } from "@/lib/AuthContext";
import EvidenceBadge from "@/components/shared/EvidenceBadge";
import GeneratingState from "@/components/shared/GeneratingState";

const KEGAN_STAGES = [
  {
    stage: 2,
    name: "Imperial Mind",
    description:
      "Self-focused perspective. Needs and interests drive decision-making. Relationships are transactional.",
    focus: "Personal advantage and concrete reciprocity",
  },
  {
    stage: 3,
    name: "Socialized Mind",
    description:
      "Defined by relationships and social roles. Values loyalty and belonging. Seeks external validation.",
    focus: "Social acceptance and shared norms",
  },
  {
    stage: 4,
    name: "Self-Authoring Mind",
    description:
      "Self-directed perspective. Creates own value system. Can evaluate and manage relationships from a personal framework.",
    focus: "Internal standards and self-authored identity",
  },
  {
    stage: 5,
    name: "Self-Transforming Mind",
    description:
      "Holds multiple frameworks simultaneously. Sees limitations of any single system. Embraces paradox and complexity.",
    focus: "Interconnection and dialectical thinking",
  },
];

const COGNITIVE_BIASES = [
  {
    name: "Confirmation Bias",
    description:
      "Tendency to seek and interpret information that confirms existing beliefs.",
    mitigation:
      "Actively seek disconfirming evidence. Practice steel-manning opposing views.",
    category: "Information Processing",
  },
  {
    name: "Anchoring Effect",
    description:
      "Over-reliance on the first piece of information encountered when making decisions.",
    mitigation:
      "Generate multiple reference points. Consider the decision from different starting conditions.",
    category: "Decision Making",
  },
  {
    name: "Availability Heuristic",
    description:
      "Judging probability based on how easily examples come to mind rather than actual frequency.",
    mitigation:
      "Check base rates. Consult data rather than relying on memorable anecdotes.",
    category: "Probability Assessment",
  },
  {
    name: "Sunk Cost Fallacy",
    description:
      "Continuing to invest in something because of previously invested resources, not future value.",
    mitigation:
      'Evaluate decisions based only on future costs and benefits. Practice the "fresh start" reframe.',
    category: "Decision Making",
  },
  {
    name: "Dunning-Kruger Effect",
    description:
      "Overestimating competence in areas of low expertise while underestimating it in areas of high expertise.",
    mitigation:
      "Seek calibrated feedback. Compare self-assessment with objective measures.",
    category: "Self-Assessment",
  },
  {
    name: "Framing Effect",
    description:
      "Different conclusions from the same information depending on how it is presented.",
    mitigation:
      'Restate the problem in multiple frames. Ask: "How would I see this if presented differently?"',
    category: "Information Processing",
  },
];

const SCENARIO_TYPES = [
  {
    name: "Pre-Mortem Analysis",
    description:
      "Imagine a decision has failed. Work backward to identify what went wrong and how to prevent it.",
    icon: "\u{1F50D}",
  },
  {
    name: "Best/Worst/Most Likely",
    description:
      "Map three scenarios for any decision to calibrate expectations and prepare contingencies.",
    icon: "\u{1F4CA}",
  },
  {
    name: "Second-Order Effects",
    description:
      "Trace the consequences of consequences. What happens after the immediate outcome?",
    icon: "\u{1F300}",
  },
  {
    name: "Inversion Thinking",
    description:
      "Instead of asking how to succeed, ask what would guarantee failure — then avoid those things.",
    icon: "\u{1F504}",
  },
];

export default function PerspectivePage() {
  const [mounted, setMounted] = useState(false);
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const { data: intake } = useIntake(userId);
  const hasIntake = !!(intake?.intentions?.length || intake?.intention);
  const { status: reportStatus } = useReportStatus();

  useEffect(() => {
    setMounted(true);
  }, []);

  const intakeKey = intake?.intentions?.join(",") ?? intake?.intention ?? "";

  // Fetch the stored profile — populated by the report pipeline after
  // generation completes.  The Kegan endpoint requires computed assessment
  // responses (dimension scores 1-5) from the perspective layer.
  const profileState = useApi<ProfileResponse>(
    () =>
      userId
        ? getProfile(userId)
        : Promise.reject(new Error("Not authenticated")),
    [userId],
  );

  const perspectiveLayerData = profileState.data?.perspective as
    | Record<string, unknown>
    | null
    | undefined;

  const keganPayload = useMemo((): Record<string, unknown> | null => {
    if (!perspectiveLayerData) return null;
    // KeganAssessRequest expects dimension scores (1-5).
    // These are stored in the kegan_dimension_scores column.
    const scores = perspectiveLayerData.kegan_dimension_scores as
      | Record<string, number>
      | null
      | undefined;
    if (!scores) return null;
    return scores;
  }, [perspectiveLayerData]);

  const kegan = useApi<KeganAssessResponse>(
    keganPayload ? () => getKeganAssessment(keganPayload) : null,
    [JSON.stringify(keganPayload)],
  );

  return (
    <ProtectedRoute>
      <main
        id="main-content"
        className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8"
      >
        <div className="max-w-5xl mx-auto">
          {/* Page Header */}
          <MotionReveal delay={0}>
            <header className="mb-10">
              <h1 className="font-display text-display-md font-light text-gradient-teal mb-3">
                Perspective Enhancement
              </h1>
              <hr className="rule-gold mb-4" aria-hidden="true" />
              <p className="font-body text-text/50 text-base max-w-2xl">
                Kegan developmental stages, cognitive bias awareness, mental
                models, and scenario planning tools for how you see the world.
              </p>
            </header>
          </MotionReveal>

          {/* Generation in progress */}
          {(reportStatus === "pending" || reportStatus === "generating") && (
            <div className="mb-12">
              <GeneratingState systemName="Perspective" />
            </div>
          )}

          {/* Personalized Kegan Assessment */}
          <MotionReveal delay={0.1}>
            <section
              className="mb-12"
              aria-labelledby="your-perspective-heading"
            >
              <h2
                id="your-perspective-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{2728}"}
                </span>
                Your Developmental Stage
              </h2>
              <hr className="rule-gold mb-6" aria-hidden="true" />
              {!profileState.loading && !keganPayload ? (
                <div className="card-surface p-6 text-center space-y-3">
                  <p className="font-body text-text/60 text-sm">
                    Complete your Alchymine report first to see personalized
                    perspective insights.
                  </p>
                  <Link
                    href="/discover"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-accent/10 text-accent font-body text-sm rounded-lg hover:bg-accent/20 transition-colors"
                  >
                    Generate your report &rarr;
                  </Link>
                </div>
              ) : (
                <ApiStateView
                  loading={kegan.loading || profileState.loading}
                  error={kegan.error}
                  empty={!kegan.data}
                  loadingText="Assessing your developmental stage..."
                  emptyText="Complete the full assessment to discover your Kegan developmental stage."
                  onRetry={kegan.refetch}
                >
                  {kegan.data && (
                    <div className="card-surface-elevated glow-teal p-6 space-y-4">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center">
                          <span className="font-display text-2xl font-light text-accent">
                            {kegan.data.stage_number}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-display text-xl font-light text-gradient-teal">
                            {kegan.data.name}
                          </h3>
                          <p className="font-body text-sm text-text/50">
                            {kegan.data.description}
                          </p>
                        </div>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
                        <div>
                          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                            Strengths
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {kegan.data.strengths.map((s) => (
                              <span
                                key={s}
                                className="px-3 py-1 bg-accent/10 text-accent text-xs rounded-full"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                            Growth Edges
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {kegan.data.growth_edges.map((g) => (
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

                      {kegan.data.growth_practices.length > 0 && (
                        <div className="pt-4 border-t border-white/5">
                          <h4 className="font-body text-xs uppercase tracking-wider text-text/40 mb-2">
                            Growth Practices
                          </h4>
                          <ul className="space-y-1">
                            {kegan.data.growth_practices.map((p) => (
                              <li
                                key={p}
                                className="font-body text-sm text-text/60 flex items-start gap-2"
                              >
                                <span
                                  className="w-1.5 h-1.5 rounded-full bg-accent mt-2 flex-shrink-0"
                                  aria-hidden="true"
                                />
                                {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="bg-accent/5 rounded-xl p-4 mt-4">
                        <p className="font-body text-sm text-text/60 italic">
                          {kegan.data.encouragement}
                        </p>
                      </div>
                    </div>
                  )}
                </ApiStateView>
              )}
            </section>
          </MotionReveal>

          {/* Developmental Frameworks Section */}
          <MotionReveal delay={0.2}>
            <section className="mb-12" aria-labelledby="frameworks-heading">
              <h2
                id="frameworks-heading"
                className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{1F4D0}"}
                </span>
                Developmental Frameworks
                <EvidenceBadge level="strong" />
              </h2>
              <hr className="rule-gold mb-4" aria-hidden="true" />
              <p className="font-body text-text/50 text-sm mb-6">
                Robert Kegan&apos;s constructive-developmental theory maps how
                adults make meaning of their experiences. Each stage represents
                a qualitatively different way of understanding self and world.
              </p>

              <MotionStagger className="space-y-4 mb-4">
                {KEGAN_STAGES.map((stage) => {
                  const isCurrentStage =
                    kegan.data?.stage_number === stage.stage;
                  return (
                    <MotionStaggerItem key={stage.stage}>
                      <div
                        className={
                          isCurrentStage
                            ? "card-surface-elevated glow-teal p-5 ring-1 ring-accent/30 transition-all duration-500"
                            : "card-surface p-5 transition-all duration-500 hover:glow-teal hover:-translate-y-0.5"
                        }
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <span className="w-8 h-8 rounded-full bg-accent/10 text-accent text-sm font-bold flex items-center justify-center flex-shrink-0">
                            {stage.stage}
                          </span>
                          <h3 className="font-display text-sm font-medium text-text">
                            {stage.name}
                            {isCurrentStage && (
                              <span className="ml-2 font-body text-accent text-xs font-normal">
                                (Your stage)
                              </span>
                            )}
                          </h3>
                        </div>
                        <p className="font-body text-sm text-text/50 leading-relaxed mb-2 ml-11">
                          {stage.description}
                        </p>
                        <p className="font-body text-xs text-text/30 ml-11">
                          <span className="font-medium text-text/40">
                            Focus:
                          </span>{" "}
                          {stage.focus}
                        </p>
                      </div>
                    </MotionStaggerItem>
                  );
                })}
              </MotionStagger>

              <MethodologyPanel
                title="Developmental Frameworks"
                methodology="Kegan's constructive-developmental theory describes five stages of adult meaning-making, from the Impulsive Mind (Stage 1) through the Self-Transforming Mind (Stage 5). Stage assessment uses the Subject-Object Interview (SOI) methodology adapted into a structured questionnaire format. The assessment identifies your current center of gravity and growing edge. AI-assisted interpretation synthesizes responses into a developmental profile while respecting the complexity of stage transitions."
                evidenceLevel="strong"
                calculationType="ai-assisted"
                sources={[
                  'Kegan, R. (1982) "The Evolving Self" - foundational developmental theory',
                  'Kegan, R. (1994) "In Over Our Heads" - application to modern life complexity',
                  "Lahey et al. (2011) Subject-Object Interview scoring manual and reliability studies",
                  'Cook-Greuter, S. (2013) "Nine Levels of Increasing Embrace" - complementary ego development model',
                ]}
              />
            </section>
          </MotionReveal>

          {/* Cognitive Biases Section */}
          <MotionReveal delay={0.1}>
            <section className="mb-12" aria-labelledby="biases-heading">
              <h2
                id="biases-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{1F9E0}"}
                </span>
                Cognitive Bias Awareness
              </h2>
              <hr className="rule-gold mb-4" aria-hidden="true" />
              <p className="font-body text-text/50 text-sm mb-6">
                Understanding your cognitive biases is the first step toward
                clearer thinking. Each bias includes a practical mitigation
                strategy.
              </p>

              <MotionStagger className="grid sm:grid-cols-2 gap-4">
                {COGNITIVE_BIASES.map((bias) => (
                  <MotionStaggerItem key={bias.name}>
                    <div className="card-surface p-5 h-full transition-all duration-500 hover:glow-teal hover:-translate-y-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-display text-sm font-medium text-accent">
                          {bias.name}
                        </h3>
                        <span className="font-body px-2 py-0.5 bg-white/5 text-text/30 text-[10px] font-medium rounded-full">
                          {bias.category}
                        </span>
                      </div>
                      <p className="font-body text-sm text-text/50 leading-relaxed mb-3">
                        {bias.description}
                      </p>
                      <div className="bg-bg/50 rounded-lg px-3 py-2">
                        <p className="font-body text-xs text-accent/70">
                          <span className="font-medium">Mitigation:</span>{" "}
                          {bias.mitigation}
                        </p>
                      </div>
                    </div>
                  </MotionStaggerItem>
                ))}
              </MotionStagger>
            </section>
          </MotionReveal>

          {/* Scenario Planning Section */}
          <MotionReveal delay={0.1}>
            <section className="mb-12" aria-labelledby="scenarios-heading">
              <h2
                id="scenarios-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{1F52D}"}
                </span>
                Scenario Planning
              </h2>
              <hr className="rule-gold mb-4" aria-hidden="true" />
              <p className="font-body text-text/50 text-sm mb-6">
                Mental models and scenario planning tools to help you think
                through decisions with greater clarity and fewer blind spots.
              </p>

              <MotionStagger className="grid sm:grid-cols-2 gap-4">
                {SCENARIO_TYPES.map((scenario) => (
                  <MotionStaggerItem key={scenario.name}>
                    <div className="card-surface p-5 h-full transition-all duration-500 hover:glow-teal hover:-translate-y-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl" aria-hidden="true">
                          {scenario.icon}
                        </span>
                        <h3 className="font-display text-sm font-medium text-text">
                          {scenario.name}
                        </h3>
                      </div>
                      <p className="font-body text-sm text-text/50 leading-relaxed">
                        {scenario.description}
                      </p>
                    </div>
                  </MotionStaggerItem>
                ))}
              </MotionStagger>
            </section>
          </MotionReveal>

          {/* Connections — healing-perspective bridge */}
          {hasIntake && (
            <MotionReveal delay={0.1}>
              <section
                className="mb-12"
                aria-labelledby="perspective-connections-heading"
                data-testid="connections-section"
              >
                <div className="card-surface border border-accent/10 p-5">
                  <h2
                    id="perspective-connections-heading"
                    className="font-display text-sm font-medium text-accent mb-3"
                  >
                    Connected: Perspective &amp; Healing Readiness
                  </h2>
                  <p className="font-body text-sm text-text/50 leading-relaxed mb-3">
                    Nervous system regulation through healing practices creates
                    the physiological safety needed for higher-order perspective
                    work. Kegan stage transitions require a regulated nervous
                    system — breathwork and somatic healing practices prepare
                    your system to hold greater complexity without collapsing
                    into reactivity.
                  </p>
                  <Link
                    href="/healing"
                    className="font-body text-xs text-accent underline underline-offset-2"
                  >
                    Explore Ethical Healing &rarr;
                  </Link>
                </div>
              </section>
            </MotionReveal>
          )}

          {/* CTA */}
          <MotionReveal delay={0.1}>
            <div className="text-center">
              <a
                href="/discover/assessment"
                className="inline-flex items-center gap-2 px-6 py-3 min-h-[44px] bg-gradient-to-r from-accent-dark via-accent to-accent-light text-bg font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(32,178,170,0.3)] hover:scale-[1.02] active:scale-100"
              >
                {hasIntake
                  ? "Update Your Perspective Profile"
                  : "Map Your Perspective"}
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
    </ProtectedRoute>
  );
}
