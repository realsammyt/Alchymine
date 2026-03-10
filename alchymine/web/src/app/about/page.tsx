"use client";

import { useState } from "react";
import Link from "next/link";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  SystemIcon,
  ShieldIcon,
  CodeIcon,
  LockIcon,
  CheckIcon,
  EyeIcon,
} from "@/components/shared/Icons";
import FeedbackForm from "@/components/shared/FeedbackForm";

const FIVE_SYSTEMS_DETAIL = [
  {
    name: "Personalized Intelligence",
    tagline: "Know thyself — mathematically",
    description:
      "Decode your life path through the mathematics of numerology, the astronomy of natal charts, and the psychology of personality science. Six deterministic engines work in concert to build your unique identity profile.",
    icon: "brain",
    color: "primary",
    features: [
      "Life Path & Expression Numbers",
      "Natal Chart & Planetary Analysis",
      "Archetype Mapping",
      "Big Five Personality Assessment",
      "Biorhythm Cycles",
      "Human Design Integration",
    ],
  },
  {
    name: "Ethical Healing",
    tagline: "First, do no harm",
    description:
      "15 evidence-grounded healing modalities, from breathwork to somatic practices. Every recommendation comes with an evidence rating, cultural attribution, and safety protocols. Crisis detection runs first — always.",
    icon: "leaf",
    color: "accent",
    features: [
      "15 Evidence-Based Modalities",
      "Crisis Detection & Safety Protocols",
      "Cultural Attribution & Respect",
      "Evidence Ratings on Every Output",
      "Modality Matching to Your Profile",
      "Methodology Transparency Panels",
    ],
  },
  {
    name: "Generational Wealth",
    tagline: "Math, not magic",
    description:
      "Your wealth archetype mapped to five levers: Earn, Keep, Grow, Protect, Transfer. All math is deterministic. All data is encrypted. Nothing financial ever touches an LLM.",
    icon: "chart",
    color: "primary",
    features: [
      "Wealth Archetype Assessment",
      "Five Levers Strategy Framework",
      "Debt Payoff Calculator",
      "Deterministic Financial Math",
      "AES-256 Data Encryption",
      "Zero LLM Financial Exposure",
    ],
  },
  {
    name: "Creative Development",
    tagline: "Unlock your creative DNA",
    description:
      "Discover your Creative DNA through Guilford's framework. Map your style (Architect, Explorer, Connector, or Alchemist), find your medium affinity, and unlock sustained creative output.",
    icon: "palette",
    color: "secondary",
    features: [
      "Divergent Thinking Assessment",
      "Guilford's Creative Framework",
      "Style Archetype Mapping",
      "Medium Affinity Analysis",
      "Production Mode Matching",
      "Creative Flow Optimization",
    ],
  },
  {
    name: "Perspective Enhancement",
    tagline: "See beyond the frame",
    description:
      "Map your developmental stage with Kegan's model. Decondition cognitive biases. Expand your worldview. AI-guided perspective-opening exercises help you see beyond the frame.",
    icon: "telescope",
    color: "secondary",
    features: [
      "Kegan Developmental Stage Mapping",
      "Cognitive Bias Awareness",
      "Strategic Clarity Score",
      "Perspective-Opening Exercises",
      "Mental Model Expansion",
      "Worldview Deconditioning",
    ],
  },
];

const ARCHITECTURE_DIAGRAMS = [
  {
    src: "/diagrams/01-system-architecture.png",
    title: "System Architecture",
    description: "Hub-and-spoke agent design with 5 coordinators and 28 agents",
    featured: true,
  },
  {
    src: "/diagrams/02-information-flow.png",
    title: "Information Flow",
    description: "How data moves from intake through engines to your report",
    featured: false,
  },
  {
    src: "/diagrams/03-user-journey.png",
    title: "User Journey",
    description: "Your path from first contact to ongoing transformation",
    featured: false,
  },
  {
    src: "/diagrams/04-current-functions.png",
    title: "Current Functions",
    description:
      "The 103 deterministic engine functions across all five systems",
    featured: false,
  },
];

const ROADMAP_TRACKS = [
  {
    color: "primary",
    label: "Track 1",
    title: "Healing-Swarm-Skills + Cross-System UX",
    description:
      "Completing the healing agent swarm and unifying the cross-system user experience into a seamless transformation journey.",
  },
  {
    color: "secondary",
    label: "Track 2",
    title: "AI Growth Assistant Agent",
    description:
      "A persistent AI companion that synthesizes insights across all five systems and proactively surfaces personalized growth opportunities.",
  },
  {
    color: "accent",
    label: "Track 3",
    title: "Gemini Generative Art",
    description:
      "Visual representations of your unique profile — natal chart art, archetype imagery, and transformation visualizations.",
  },
];

const ETHICS_PRINCIPLES = [
  {
    title: "Do No Harm",
    description:
      "Crisis detection runs before any recommendation. Safety protocols are not optional add-ons — they are the foundation every output is built on.",
    icon: "shield",
  },
  {
    title: "Honor Traditions",
    description:
      "Every modality includes cultural attribution and proper citation. We draw from traditions without extracting from them.",
    icon: "eye",
  },
  {
    title: "Evidence + Humility",
    description:
      "Every recommendation carries an evidence rating. We distinguish between strong research, emerging evidence, and cultural wisdom.",
    icon: "check",
  },
  {
    title: "Empower, Not Control",
    description:
      "No artificial urgency. No manipulative design patterns. No calming aesthetics used to mask problems. Just honest tools.",
    icon: "code",
  },
  {
    title: "Privacy as Sanctuary",
    description:
      "Your data lives on your infrastructure. Local-first by default. No third-party analytics. No data selling. Ever.",
    icon: "lock",
  },
  {
    title: "Open Source Everything",
    description:
      "Every prompt, algorithm, and model is public. Inspect the methodology, verify the math, contribute improvements.",
    icon: "code",
  },
];

function colorClass(color: string) {
  switch (color) {
    case "primary":
      return {
        bg: "bg-primary/10",
        border: "border-primary/20",
        text: "text-primary",
        glow: "hover:shadow-[0_0_30px_rgba(218,165,32,0.15)]",
        pill: "bg-primary/[0.06] border-primary/[0.12] text-primary",
      };
    case "secondary":
      return {
        bg: "bg-secondary/10",
        border: "border-secondary/20",
        text: "text-secondary",
        glow: "hover:shadow-[0_0_30px_rgba(123,45,142,0.15)]",
        pill: "bg-secondary/[0.06] border-secondary/[0.12] text-secondary",
      };
    case "accent":
      return {
        bg: "bg-accent/10",
        border: "border-accent/20",
        text: "text-accent",
        glow: "hover:shadow-[0_0_30px_rgba(32,178,170,0.15)]",
        pill: "bg-accent/[0.06] border-accent/[0.12] text-accent",
      };
    default:
      return {
        bg: "bg-primary/10",
        border: "border-primary/20",
        text: "text-primary",
        glow: "hover:shadow-[0_0_30px_rgba(218,165,32,0.15)]",
        pill: "bg-primary/[0.06] border-primary/[0.12] text-primary",
      };
  }
}

function EthicsIcon({ name, className }: { name: string; className?: string }) {
  if (name === "check") return <CheckIcon className={className} />;
  if (name === "shield") return <ShieldIcon className={className} />;
  if (name === "code") return <CodeIcon className={className} />;
  if (name === "lock") return <LockIcon className={className} />;
  if (name === "eye") return <EyeIcon className={className} />;
  return null;
}

function FeedbackFormCTA() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-accent/80 via-accent to-accent/80 text-bg font-body font-medium rounded-xl text-base transition-all duration-300 hover:shadow-[0_0_40px_rgba(32,178,170,0.25)] hover:scale-[1.02] active:scale-[0.98]"
      >
        Share Your Feedback
      </button>
      <FeedbackForm isOpen={open} onClose={() => setOpen(false)} pageUrl="/about" />
    </>
  );
}

export default function AboutPage() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="pt-36 pb-28 px-4 sm:px-6 relative overflow-hidden bg-atmosphere">
        {/* Atmospheric background orbs */}
        <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary/[0.04] rounded-full blur-[160px] pointer-events-none animate-glow-breathe" />
        <div className="absolute top-32 left-[15%] w-[400px] h-[400px] bg-secondary/[0.05] rounded-full blur-[120px] pointer-events-none animate-glow-breathe animation-delay-200" />
        <div className="absolute top-48 right-[15%] w-[300px] h-[300px] bg-accent/[0.03] rounded-full blur-[100px] pointer-events-none animate-glow-breathe animation-delay-400" />

        <div className="max-w-4xl mx-auto text-center relative">
          <MotionReveal delay={0.1} y={16}>
            <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full border border-primary/15 bg-primary/[0.04] text-xs font-body font-medium text-primary/80 tracking-wider uppercase mb-8">
              <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-pulse" />
              Beta &middot; Open-Source Personal Transformation OS
            </div>
          </MotionReveal>

          <MotionReveal delay={0.2} y={20}>
            <h1 className="font-display text-display-xl font-light mb-4">
              <span className="text-gradient-gold">Transforming</span>
              <br />
              <span className="text-gradient-gold">
                Self-Knowledge Into Gold
              </span>
            </h1>
          </MotionReveal>

          <MotionReveal delay={0.35}>
            <hr className="rule-gold my-8 max-w-[100px] mx-auto" />
          </MotionReveal>

          <MotionReveal delay={0.45} y={12}>
            <p className="text-base text-text/40 font-body max-w-2xl mx-auto leading-relaxed">
              Alchymine is an open-source, AI-powered Personal Transformation
              Operating System with five integrated pillars — built on
              transparent methodology, deterministic math, and ethics-first
              design.
            </p>
          </MotionReveal>

          <MotionReveal delay={0.5} y={10}>
            <div className="mt-8 max-w-xl mx-auto card-surface-elevated px-6 py-5 text-center">
              <p className="font-display text-sm font-medium text-primary/80 mb-1.5">
                Alchymine is in beta — and evolving fast
              </p>
              <p className="text-xs text-text/40 font-body leading-relaxed">
                New features ship every week across all five systems. Your
                feedback is incredibly valuable and directly shapes what we
                build next. Found a bug? Have an idea? We want to hear it.
              </p>
            </div>
          </MotionReveal>

          <MotionReveal delay={0.6} y={10}>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-xs font-body text-text/40 tracking-wide">
              <span className="flex items-center gap-1.5">
                <ShieldIcon className="w-3.5 h-3.5" />
                Ethics-First
              </span>
              <span className="w-px h-3 bg-white/[0.06]" />
              <span className="flex items-center gap-1.5">
                <CodeIcon className="w-3.5 h-3.5" />
                Open Source
              </span>
              <span className="w-px h-3 bg-white/[0.06]" />
              <span className="flex items-center gap-1.5">
                <LockIcon className="w-3.5 h-3.5" />
                Your Data Stays Yours
              </span>
              <span className="w-px h-3 bg-white/[0.06]" />
              <span>CC-BY-NC-SA 4.0</span>
            </div>
          </MotionReveal>
        </div>
      </section>

      {/* ── The Vision ──────────────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-surface/20 to-transparent pointer-events-none" />
        <div className="max-w-3xl mx-auto relative">
          <MotionReveal>
            <div className="text-center mb-14">
              <h2 className="section-heading text-gradient-gold mb-4">
                The Vision
              </h2>
              <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
            </div>
          </MotionReveal>

          <MotionReveal delay={0.15} y={16}>
            <div className="card-surface-elevated p-8 sm:p-10 space-y-6">
              <p className="font-display text-lg sm:text-xl font-light text-text/60 italic leading-relaxed">
                Every person carries within them the raw materials for
                transformation — the patterns in their birth chart, the wisdom
                of their personality, the untapped potential of their creative
                DNA, the perspectives waiting to be opened. Alchymine is the
                crucible that brings these elements together.
              </p>
              <hr className="rule-gold" />
              <p className="font-body text-sm text-text/45 leading-relaxed">
                We believe personal transformation should be transparent,
                evidence-based, and accessible. Not hidden behind paywalls or
                wrapped in mysticism. Every algorithm is open source. Every
                recommendation comes with an evidence rating. Every financial
                calculation is deterministic math, not AI hallucination.
              </p>
              <hr className="rule-gold" />
              <p className="font-display text-base font-light text-text/50 italic leading-relaxed">
                Five systems. One integrated journey. Your data, your
                infrastructure, your transformation.
              </p>
            </div>
          </MotionReveal>
        </div>
      </section>

      {/* ── Architecture Diagrams ────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6" id="architecture">
        <div className="max-w-6xl mx-auto">
          <MotionReveal>
            <div className="text-center mb-16">
              <h2 className="section-heading text-gradient-gold mb-4">
                How It Works — Under the Hood
              </h2>
              <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
              <p className="text-text/40 font-body max-w-2xl mx-auto leading-relaxed">
                Open architecture. Transparent methodology. Built for trust.
              </p>
            </div>
          </MotionReveal>

          {/* Featured system architecture diagram */}
          <MotionReveal delay={0.1} y={20}>
            <div className="card-surface p-4 sm:p-6 mb-6 transition-all duration-500 hover:shadow-[0_0_40px_rgba(218,165,32,0.08)]">
              <div className="mb-4">
                <h3 className="font-display text-lg font-medium text-text mb-1">
                  System Architecture
                </h3>
                <p className="text-xs font-body text-text/35">
                  Hub-and-spoke agent design with 5 coordinators and 28 agents
                </p>
              </div>
              <div className="rounded-xl overflow-hidden bg-black/20">
                <img
                  src="/diagrams/01-system-architecture.png"
                  alt="Alchymine system architecture diagram showing the hub-and-spoke agent design"
                  className="w-full h-auto"
                  loading="lazy"
                />
              </div>
            </div>
          </MotionReveal>

          {/* Remaining diagrams in grid */}
          <MotionStagger
            staggerDelay={0.1}
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {ARCHITECTURE_DIAGRAMS.filter((d) => !d.featured).map((diagram) => (
              <MotionStaggerItem key={diagram.src}>
                <div className="card-surface p-4 h-full transition-all duration-500 hover:shadow-[0_0_30px_rgba(218,165,32,0.08)]">
                  <div className="mb-3">
                    <h3 className="font-display text-base font-medium text-text mb-1">
                      {diagram.title}
                    </h3>
                    <p className="text-[0.7rem] font-body text-text/35 leading-relaxed">
                      {diagram.description}
                    </p>
                  </div>
                  <div className="rounded-lg overflow-hidden bg-black/20">
                    <img
                      src={diagram.src}
                      alt={`${diagram.title} diagram`}
                      className="w-full h-auto"
                      loading="lazy"
                    />
                  </div>
                </div>
              </MotionStaggerItem>
            ))}
          </MotionStagger>
        </div>
      </section>

      {/* ── Five Systems ────────────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6 relative" id="five-systems">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-surface/20 to-transparent pointer-events-none" />
        <div className="max-w-6xl mx-auto relative">
          <MotionReveal>
            <div className="text-center mb-16">
              <h2 className="section-heading text-gradient-gold mb-4">
                The Five Systems
              </h2>
              <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
              <p className="text-text/40 font-body max-w-2xl mx-auto leading-relaxed">
                Each system provides a unique, deterministic lens on your
                transformation. Together, they create a unified profile that
                grows with you.
              </p>
            </div>
          </MotionReveal>

          <MotionStagger
            staggerDelay={0.1}
            className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6"
          >
            {FIVE_SYSTEMS_DETAIL.map((system) => {
              const colors = colorClass(system.color);
              return (
                <MotionStaggerItem key={system.name}>
                  <div
                    className={`group card-surface p-6 h-full transition-all duration-500 hover:-translate-y-1 ${colors.glow}`}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className={`w-10 h-10 rounded-xl ${colors.bg} ${colors.border} border flex items-center justify-center transition-transform duration-500 group-hover:scale-110`}
                      >
                        <SystemIcon
                          icon={system.icon}
                          className={`w-6 h-6 ${colors.text}`}
                        />
                      </div>
                      <div>
                        <h3 className="font-display text-lg font-medium text-text">
                          {system.name}
                        </h3>
                        <p
                          className={`text-xs font-body ${colors.text} tracking-wide`}
                        >
                          {system.tagline}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm text-text/40 font-body mb-5 leading-relaxed">
                      {system.description}
                    </p>
                    <ul className="space-y-2">
                      {system.features.map((feature) => (
                        <li
                          key={feature}
                          className="flex items-center gap-2 text-xs font-body text-text/35"
                        >
                          <CheckIcon
                            className={`w-3.5 h-3.5 ${colors.text} flex-shrink-0 opacity-60`}
                          />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </MotionStaggerItem>
              );
            })}
          </MotionStagger>
        </div>
      </section>

      {/* ── Roadmap ─────────────────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6" id="roadmap">
        <div className="max-w-6xl mx-auto">
          <MotionReveal>
            <div className="text-center mb-16">
              <h2 className="section-heading text-gradient-gold mb-4">
                The Road Ahead — 90 Days to Launch
              </h2>
              <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
              <p className="text-text/40 font-body max-w-2xl mx-auto leading-relaxed">
                Three parallel tracks. Three milestones. One launch.
              </p>
            </div>
          </MotionReveal>

          {/* Roadmap diagram */}
          <MotionReveal delay={0.1} y={20}>
            <div className="card-surface p-4 sm:p-6 mb-12 transition-all duration-500 hover:shadow-[0_0_40px_rgba(218,165,32,0.08)]">
              <div className="rounded-xl overflow-hidden bg-black/20">
                <img
                  src="/diagrams/05-roadmap-90-day.png"
                  alt="90-day launch roadmap showing three parallel development tracks"
                  className="w-full h-auto"
                  loading="lazy"
                />
              </div>
            </div>
          </MotionReveal>

          {/* Three tracks */}
          <MotionStagger
            staggerDelay={0.12}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12"
          >
            {ROADMAP_TRACKS.map((track) => {
              const colors = colorClass(track.color);
              return (
                <MotionStaggerItem key={track.label}>
                  <div className="card-surface p-6 h-full">
                    <div
                      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-body font-medium tracking-wider uppercase mb-4 ${colors.pill}`}
                    >
                      {track.label}
                    </div>
                    <h3 className="font-display text-base font-medium text-text mb-3">
                      {track.title}
                    </h3>
                    <p className="text-sm text-text/40 font-body leading-relaxed">
                      {track.description}
                    </p>
                  </div>
                </MotionStaggerItem>
              );
            })}
          </MotionStagger>

          {/* Milestones */}
          <MotionReveal delay={0.2} y={12}>
            <div className="card-surface-elevated p-6 sm:p-8">
              <h3 className="font-display text-lg font-medium text-text mb-6 text-center">
                Milestones
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                {[
                  {
                    week: "Week 4",
                    label: "MVP",
                    desc: "Core systems integrated, assessment flow complete",
                    color: "primary",
                  },
                  {
                    week: "Week 8",
                    label: "Beta",
                    desc: "AI growth assistant live, closed beta invitations sent",
                    color: "secondary",
                  },
                  {
                    week: "Week 12",
                    label: "Launch",
                    desc: "Generative art, full report suite, public availability",
                    color: "accent",
                  },
                ].map((m) => {
                  const colors = colorClass(m.color);
                  return (
                    <div key={m.week} className="text-center">
                      <div
                        className={`w-14 h-14 mx-auto mb-3 rounded-2xl ${colors.bg} ${colors.border} border flex items-center justify-center`}
                      >
                        <span
                          className={`font-display text-sm font-medium ${colors.text}`}
                        >
                          {m.label}
                        </span>
                      </div>
                      <p className={`text-xs font-body ${colors.text} mb-1`}>
                        {m.week}
                      </p>
                      <p className="text-xs font-body text-text/35 leading-relaxed">
                        {m.desc}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </MotionReveal>
        </div>
      </section>

      {/* ── Ethics & Trust ──────────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6 relative" id="ethics">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-surface/20 to-transparent pointer-events-none" />
        <div className="max-w-5xl mx-auto relative">
          <MotionReveal>
            <div className="text-center mb-16">
              <h2 className="section-heading text-gradient-gold mb-4">
                Ethics First — Always
              </h2>
              <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
              <p className="text-text/40 font-body max-w-xl mx-auto">
                Radical transparency isn&apos;t a feature — it&apos;s the
                foundation.
              </p>
            </div>
          </MotionReveal>

          <MotionStagger
            staggerDelay={0.1}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {ETHICS_PRINCIPLES.map((principle) => (
              <MotionStaggerItem key={principle.title}>
                <div className="card-surface p-6 flex items-start gap-4 h-full">
                  <div className="w-10 h-10 rounded-xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center flex-shrink-0">
                    <EthicsIcon
                      name={principle.icon}
                      className="w-5 h-5 text-primary/70"
                    />
                  </div>
                  <div>
                    <h3 className="font-display text-base font-medium text-text mb-1.5">
                      {principle.title}
                    </h3>
                    <p className="text-sm text-text/40 font-body leading-relaxed">
                      {principle.description}
                    </p>
                  </div>
                </div>
              </MotionStaggerItem>
            ))}
          </MotionStagger>
        </div>
      </section>

      {/* ── Beta Feedback CTA ──────────────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/[0.02] to-transparent pointer-events-none" />
        <div className="max-w-xl mx-auto text-center relative">
          <MotionReveal>
            <h2 className="font-display text-2xl sm:text-3xl font-light text-gradient-gold mb-3">
              Help Shape Alchymine
            </h2>
            <p className="text-text/40 font-body mb-8 leading-relaxed">
              Found a bug? Have a feature idea? Just want to share how the
              journey is going? Your feedback directly shapes what we build next.
            </p>
            <FeedbackFormCTA />
          </MotionReveal>
        </div>
      </section>

      {/* ── Footer CTA ──────────────────────────────────────────────────── */}
      <section className="py-28 px-4 sm:px-6 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.03] to-transparent pointer-events-none" />
        <div className="max-w-2xl mx-auto text-center relative">
          <MotionReveal>
            <h2 className="font-display text-3xl sm:text-4xl font-light text-gradient-gold mb-4">
              Ready to begin your transformation?
            </h2>
            <p className="text-text/40 font-body mb-10 leading-relaxed">
              Your free assessment takes about 10 minutes. Every algorithm is
              open source. Every recommendation is evidence-rated.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium rounded-xl text-base transition-all duration-300 hover:shadow-[0_0_40px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]"
              >
                Begin Your Journey
                <svg
                  className="w-5 h-5"
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
              </Link>
              <a
                href="https://github.com/realsammyt/Alchymine"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3.5 border border-white/[0.08] text-text/50 font-body rounded-xl text-base hover:bg-white/[0.03] hover:text-text/70 hover:border-white/[0.12] transition-all duration-300"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                View the Source
              </a>
            </div>
          </MotionReveal>
        </div>
      </section>
    </div>
  );
}
