"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

const FIVE_SYSTEMS = [
  {
    name: "Personalized Intelligence",
    tagline: "Know thyself — mathematically",
    description:
      "Numerology, natal chart analysis, biorhythm tracking, archetype mapping, and Big Five personality assessment — all deterministic, all transparent.",
    icon: "brain",
    color: "primary",
    features: [
      "Life Path & Expression Numbers",
      "Natal Chart Analysis",
      "Archetype Mapping",
    ],
  },
  {
    name: "Ethical Healing",
    tagline: "First, do no harm",
    description:
      "Personalized modalities matched to your profile with full safety protocols, crisis resources, and evidence-based methodology panels.",
    icon: "leaf",
    color: "accent",
    features: [
      "Breathwork & Somatic Practices",
      "Modality Matching",
      "Crisis Safety Protocols",
    ],
  },
  {
    name: "Generational Wealth",
    tagline: "Math, not magic",
    description:
      "Five-lever financial strategy with deterministic calculations. All financial math is computed, never AI-generated. Your data stays encrypted.",
    icon: "chart",
    color: "primary",
    features: [
      "Wealth Archetype Assessment",
      "Debt Payoff Calculator",
      "Five Levers Strategy",
    ],
  },
  {
    name: "Creative Development",
    tagline: "Unlock your creative DNA",
    description:
      "Guilford-based creative assessment, Creative DNA profiling, medium affinity mapping, and tools for sustained creative output.",
    icon: "palette",
    color: "secondary",
    features: [
      "Divergent Thinking Assessment",
      "Creative DNA Profile",
      "Production Mode Matching",
    ],
  },
  {
    name: "Perspective Enhancement",
    tagline: "See beyond the frame",
    description:
      "Kegan developmental stages, mental models, cognitive bias awareness, and strategic clarity tools for how you see the world.",
    icon: "telescope",
    color: "accent",
    features: [
      "Developmental Stage Mapping",
      "Cognitive Reframing",
      "Strategic Clarity Score",
    ],
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Discovery",
    description:
      "Answer a short intake form — your name, birth date, intentions, and a 20-question assessment. Takes about 10 minutes.",
  },
  {
    step: "02",
    title: "Blueprint",
    description:
      "Our engines generate your personalized profile across all five systems. Deterministic math, transparent methodology, evidence ratings on every output.",
  },
  {
    step: "03",
    title: "Path",
    description:
      "Follow your personalized transformation path with daily practices, insights, and tools — all grounded in your unique profile data.",
  },
];

const TRUST_CARDS = [
  {
    title: "Open Source",
    description:
      "Every prompt, algorithm, and model is public. Inspect the code, verify the methodology, contribute improvements.",
    icon: "code",
  },
  {
    title: "Math-Only Finance",
    description:
      "All financial calculations are deterministic. No AI generates your numbers. Encrypted at rest, never sent to any LLM.",
    icon: "lock",
  },
  {
    title: "Local-First Data",
    description:
      "Your data stays on your infrastructure. No third-party analytics, no data selling, no dark patterns.",
    icon: "shield",
  },
  {
    title: "No Dark Patterns",
    description:
      "No artificial urgency, no manipulative design, no calming aesthetics to mask problems. Just honest tools.",
    icon: "eye",
  },
];

function SystemIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const baseClass = `w-6 h-6 ${className}`;
  switch (icon) {
    case "brain":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 2a4 4 0 0 0-4 4v1a4 4 0 0 0-4 4c0 1.5.8 2.8 2 3.4V18a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-3.6c1.2-.6 2-1.9 2-3.4a4 4 0 0 0-4-4V6a4 4 0 0 0-4-4z" />
          <path d="M12 2v20" />
        </svg>
      );
    case "leaf":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
      );
    case "chart":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="12" y1="20" x2="12" y2="10" />
          <line x1="18" y1="20" x2="18" y2="4" />
          <line x1="6" y1="20" x2="6" y2="16" />
        </svg>
      );
    case "palette":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
          <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
          <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
          <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
          <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
        </svg>
      );
    case "telescope":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m10.065 12.493-6.18 1.318a.934.934 0 0 1-1.108-.702l-.537-2.15a1.07 1.07 0 0 1 .691-1.265l13.504-4.44" />
          <path d="m13.56 11.747 4.332-.924" />
          <path d="m16.243 5.636 2.16.45a.93.93 0 0 1 .704 1.108l-.534 2.15a1.07 1.07 0 0 1-1.267.69l-2.455-.519" />
          <path d="m13.56 11.747-3.495 5.245" />
          <path d="m10.065 12.493-3.495 5.245" />
        </svg>
      );
    default:
      return null;
  }
}

function TrustIcon({
  icon,
  className = "",
}: {
  icon: string;
  className?: string;
}) {
  const baseClass = `w-5 h-5 ${className}`;
  switch (icon) {
    case "code":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      );
    case "lock":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case "shield":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
        </svg>
      );
    case "eye":
      return (
        <svg
          className={baseClass}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
    default:
      return null;
  }
}

function colorClass(color: string) {
  switch (color) {
    case "primary":
      return {
        bg: "bg-primary/10",
        border: "border-primary/20",
        text: "text-primary",
        glow: "group-hover:shadow-[0_0_30px_rgba(218,165,32,0.15)]",
      };
    case "secondary":
      return {
        bg: "bg-secondary/10",
        border: "border-secondary/20",
        text: "text-secondary",
        glow: "group-hover:shadow-[0_0_30px_rgba(123,45,142,0.15)]",
      };
    case "accent":
      return {
        bg: "bg-accent/10",
        border: "border-accent/20",
        text: "text-accent",
        glow: "group-hover:shadow-[0_0_30px_rgba(32,178,170,0.15)]",
      };
    default:
      return {
        bg: "bg-primary/10",
        border: "border-primary/20",
        text: "text-primary",
        glow: "group-hover:shadow-[0_0_30px_rgba(218,165,32,0.15)]",
      };
  }
}

export default function LandingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistSubmitted, setWaitlistSubmitted] = useState(false);

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, isLoading, router]);

  function handleWaitlist(e: React.FormEvent) {
    e.preventDefault();
    if (!waitlistEmail.trim()) return;

    const existing = JSON.parse(
      localStorage.getItem("alchymine_waitlist") || "[]",
    );
    if (!existing.includes(waitlistEmail)) {
      existing.push(waitlistEmail);
      localStorage.setItem("alchymine_waitlist", JSON.stringify(existing));
    }
    setWaitlistSubmitted(true);
  }

  // Show nothing while checking auth (prevents flash)
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  // Authed users get redirected (handled by useEffect)
  if (user) return null;

  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* ── Landing Header ──────────────────────────────────────────────── */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[60] focus:px-4 focus:py-2 focus:bg-primary focus:text-bg focus:rounded-lg focus:text-sm focus:font-body"
      >
        Skip to main content
      </a>
      <header className="fixed top-0 left-0 right-0 z-50 bg-bg/70 backdrop-blur-2xl border-b border-white/[0.04]">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 sm:px-6 py-4">
          <span className="font-display text-2xl font-light tracking-wide text-gradient-gold">
            Alchymine
          </span>
          <nav
            aria-label="Landing page navigation"
            className="flex items-center gap-4"
          >
            <Link
              href="/login"
              className="text-sm font-body text-text/50 hover:text-text transition-colors duration-300 px-3 py-2"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="text-sm font-body font-medium px-5 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <main id="main-content">
        <section className="pt-36 pb-28 px-4 sm:px-6 relative overflow-hidden bg-atmosphere">
          {/* Atmospheric background orbs */}
          <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary/[0.04] rounded-full blur-[160px] pointer-events-none animate-glow-breathe" />
          <div className="absolute top-32 left-[15%] w-[400px] h-[400px] bg-secondary/[0.05] rounded-full blur-[120px] pointer-events-none animate-glow-breathe animation-delay-200" />
          <div className="absolute top-48 right-[15%] w-[300px] h-[300px] bg-accent/[0.03] rounded-full blur-[100px] pointer-events-none animate-glow-breathe animation-delay-400" />

          <div className="max-w-4xl mx-auto text-center relative">
            <MotionReveal delay={0.1} y={16}>
              <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full border border-primary/15 bg-primary/[0.04] text-xs font-body font-medium text-primary/80 tracking-wider uppercase mb-8">
                <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-pulse" />
                Open-Source Personal Transformation
              </div>
            </MotionReveal>

            <MotionReveal delay={0.2} y={20}>
              <h1 className="font-display text-display-xl font-light mb-4">
                <span className="text-gradient-gold">Discover Who You</span>
                <br />
                <span className="text-gradient-gold">Truly Are</span>
              </h1>
            </MotionReveal>

            <MotionReveal delay={0.35}>
              <hr className="rule-gold my-8 max-w-[100px] mx-auto" />
            </MotionReveal>

            <MotionReveal delay={0.4} y={16}>
              <p className="font-display text-xl sm:text-2xl font-light text-text/40 italic max-w-2xl mx-auto mb-4 leading-relaxed">
                Through Five Integrated Systems
              </p>
            </MotionReveal>

            <MotionReveal delay={0.5} y={12}>
              <p className="text-base text-text/35 font-body max-w-xl mx-auto mb-12 leading-relaxed">
                Identity mapping, ethical healing, wealth strategy, creative
                development, and perspective enhancement — built on transparent
                methodology and open-source principles.
              </p>
            </MotionReveal>

            <MotionReveal delay={0.6} y={10}>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium rounded-xl text-base transition-all duration-300 hover:shadow-[0_0_40px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]"
                >
                  Start Your Discovery
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
                  href="#how-it-works"
                  className="inline-flex items-center gap-2 px-6 py-3.5 border border-white/[0.08] text-text/50 font-body rounded-xl text-base hover:bg-white/[0.03] hover:text-text/70 hover:border-white/[0.12] transition-all duration-300"
                >
                  How It Works
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
                    <path d="M12 5v14" />
                    <path d="m19 12-7 7-7-7" />
                  </svg>
                </a>
              </div>
            </MotionReveal>

            {/* Trust strip */}
            <MotionReveal delay={0.8} y={8}>
              <div className="mt-16 flex flex-wrap items-center justify-center gap-6 text-xs font-body text-text/40 tracking-wide">
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-3.5 h-3.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
                  </svg>
                  Ethics-First
                </span>
                <span className="w-px h-3 bg-white/[0.06]" />
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-3.5 h-3.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="16 18 22 12 16 6" />
                    <polyline points="8 6 2 12 8 18" />
                  </svg>
                  Open Source
                </span>
                <span className="w-px h-3 bg-white/[0.06]" />
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-3.5 h-3.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  Your Data Stays Yours
                </span>
                <span className="w-px h-3 bg-white/[0.06]" />
                <span>CC-BY-NC-SA 4.0</span>
              </div>
            </MotionReveal>
          </div>
        </section>

        {/* ── Five Systems ────────────────────────────────────────────────── */}
        <section className="py-28 px-4 sm:px-6" id="five-systems">
          <div className="max-w-6xl mx-auto">
            <MotionReveal>
              <div className="text-center mb-16">
                <h2 className="section-heading text-gradient-gold mb-4">
                  Five Integrated Systems
                </h2>
                <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
                <p className="text-text/40 font-body max-w-2xl mx-auto leading-relaxed">
                  Each system provides a unique lens on your transformation.
                  Together, they create a unified profile that grows with you.
                </p>
              </div>
            </MotionReveal>

            <MotionStagger
              staggerDelay={0.1}
              className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
            >
              {FIVE_SYSTEMS.map((system) => {
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
                            className={colors.text}
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
                      <p className="text-sm text-text/40 font-body mb-4 leading-relaxed">
                        {system.description}
                      </p>
                      <ul className="space-y-2">
                        {system.features.map((feature) => (
                          <li
                            key={feature}
                            className="flex items-center gap-2 text-xs font-body text-text/35"
                          >
                            <svg
                              className={`w-3.5 h-3.5 ${colors.text} flex-shrink-0 opacity-60`}
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden="true"
                            >
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
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

        {/* ── How It Works ────────────────────────────────────────────────── */}
        <section className="py-28 px-4 sm:px-6 relative" id="how-it-works">
          {/* Subtle background shift */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-surface/20 to-transparent pointer-events-none" />

          <div className="max-w-4xl mx-auto relative">
            <MotionReveal>
              <div className="text-center mb-16">
                <h2 className="section-heading text-gradient-gold mb-4">
                  How It Works
                </h2>
                <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
                <p className="text-text/40 font-body max-w-xl mx-auto">
                  Three steps from curiosity to a personalized transformation
                  path.
                </p>
              </div>
            </MotionReveal>

            <MotionStagger
              staggerDelay={0.15}
              className="grid grid-cols-1 md:grid-cols-3 gap-10"
            >
              {HOW_IT_WORKS.map((item) => (
                <MotionStaggerItem key={item.step}>
                  <div className="text-center">
                    <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center">
                      <span className="font-display text-2xl font-light text-primary/70">
                        {item.step}
                      </span>
                    </div>
                    <h3 className="font-display text-xl font-medium text-text mb-3">
                      {item.title}
                    </h3>
                    <p className="text-sm text-text/40 font-body leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>
          </div>
        </section>

        {/* ── Ethics & Transparency ───────────────────────────────────────── */}
        <section className="py-28 px-4 sm:px-6" id="ethics">
          <div className="max-w-5xl mx-auto">
            <MotionReveal>
              <div className="text-center mb-16">
                <h2 className="section-heading text-gradient-gold mb-4">
                  Built on Trust
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
              className="grid grid-cols-1 sm:grid-cols-2 gap-6"
            >
              {TRUST_CARDS.map((card) => (
                <MotionStaggerItem key={card.title}>
                  <div className="card-surface p-6 flex items-start gap-4 h-full">
                    <div className="w-10 h-10 rounded-xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center flex-shrink-0">
                      <TrustIcon icon={card.icon} className="text-primary/70" />
                    </div>
                    <div>
                      <h3 className="font-display text-lg font-medium text-text mb-1.5">
                        {card.title}
                      </h3>
                      <p className="text-sm text-text/40 font-body leading-relaxed">
                        {card.description}
                      </p>
                    </div>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>
          </div>
        </section>

        {/* ── CTA Section ─────────────────────────────────────────────────── */}
        <section className="py-28 px-4 sm:px-6 relative">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-surface/20 to-transparent pointer-events-none" />
          <div className="max-w-4xl mx-auto relative">
            <MotionStagger
              staggerDelay={0.15}
              className="grid grid-cols-1 md:grid-cols-2 gap-8"
            >
              {/* Invitation card */}
              <MotionStaggerItem>
                <div className="card-surface-elevated p-8 text-center flex flex-col justify-between h-full">
                  <div>
                    <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/[0.08] flex items-center justify-center">
                      <svg
                        className="w-6 h-6 text-primary"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                        <polyline points="10 17 15 12 10 7" />
                        <line x1="15" y1="12" x2="3" y2="12" />
                      </svg>
                    </div>
                    <h3 className="font-display text-xl font-medium text-text mb-2">
                      Have an Invitation?
                    </h3>
                    <p className="text-sm text-text/40 font-body mb-6">
                      If you have an invitation code, create your account and
                      start your transformation journey today.
                    </p>
                  </div>
                  <Link
                    href="/signup"
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Create Account
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
                  </Link>
                </div>
              </MotionStaggerItem>

              {/* Waitlist card */}
              <MotionStaggerItem>
                <div className="card-surface-elevated p-8 text-center flex flex-col justify-between h-full">
                  <div>
                    <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-accent/[0.08] flex items-center justify-center">
                      <svg
                        className="w-6 h-6 text-accent"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <rect width="20" height="16" x="2" y="4" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                      </svg>
                    </div>
                    <h3 className="font-display text-xl font-medium text-text mb-2">
                      Join the Waitlist
                    </h3>
                    <p className="text-sm text-text/40 font-body mb-6">
                      No invitation code yet? Join the waitlist and we&apos;ll
                      notify you when spots open up.
                    </p>
                  </div>

                  {waitlistSubmitted ? (
                    <div className="flex items-center justify-center gap-2 py-3 text-accent text-sm">
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
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      You&apos;re on the list — we&apos;ll be in touch.
                    </div>
                  ) : (
                    <form onSubmit={handleWaitlist} className="flex gap-2">
                      <label htmlFor="waitlist-email" className="sr-only">
                        Email address for waitlist
                      </label>
                      <input
                        id="waitlist-email"
                        type="email"
                        required
                        value={waitlistEmail}
                        onChange={(e) => setWaitlistEmail(e.target.value)}
                        placeholder="you@example.com"
                        className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/20 transition-all duration-300"
                      />
                      <button
                        type="submit"
                        className="px-5 py-3 bg-accent/[0.08] text-accent border border-accent/[0.15] rounded-xl text-sm font-body font-medium hover:bg-accent/[0.12] transition-all duration-300 flex-shrink-0"
                      >
                        Join
                      </button>
                    </form>
                  )}
                </div>
              </MotionStaggerItem>
            </MotionStagger>
          </div>
        </section>

        {/* ── Founding Quote ──────────────────────────────────────────────── */}
        <section className="py-24 px-4 sm:px-6">
          <MotionReveal>
            <div className="max-w-3xl mx-auto text-center">
              <blockquote className="font-display text-xl sm:text-2xl lg:text-3xl text-text/50 italic font-light leading-relaxed mb-6">
                &ldquo;We built Alchymine because personal transformation tools
                shouldn&apos;t require blind trust. Every algorithm is visible,
                every methodology is cited, every financial calculation is
                deterministic.&rdquo;
              </blockquote>
              <hr className="rule-gold my-6 max-w-[60px] mx-auto" />
              <p className="text-sm font-body text-text/25 tracking-wider uppercase">
                The Alchymine Project
              </p>
              <a
                href="https://github.com/realsammyt/Alchymine"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-4 text-xs font-body text-text/30 hover:text-text/50 transition-colors duration-300"
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                View on GitHub
              </a>
            </div>
          </MotionReveal>
        </section>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.04] py-16 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-10">
            {/* Brand */}
            <div>
              <span className="font-display text-xl font-light tracking-wide text-gradient-gold block mb-3">
                Alchymine
              </span>
              <p className="text-xs font-body text-text/30 leading-relaxed">
                Open-source, AI-powered Personal Transformation Operating
                System. Licensed under CC-BY-NC-SA 4.0.
              </p>
            </div>

            {/* Links */}
            <div>
              <h4 className="text-[0.65rem] font-body font-medium text-text/30 uppercase tracking-[0.15em] mb-4">
                Navigation
              </h4>
              <ul className="space-y-2.5 text-sm font-body text-text/35">
                <li>
                  <a
                    href="#five-systems"
                    className="hover:text-text/60 transition-colors"
                  >
                    Five Systems
                  </a>
                </li>
                <li>
                  <a
                    href="#how-it-works"
                    className="hover:text-text/60 transition-colors"
                  >
                    How It Works
                  </a>
                </li>
                <li>
                  <a
                    href="#ethics"
                    className="hover:text-text/60 transition-colors"
                  >
                    Ethics & Transparency
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/realsammyt/Alchymine"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-text/60 transition-colors"
                  >
                    GitHub
                  </a>
                </li>
              </ul>
            </div>

            {/* Principles */}
            <div>
              <h4 className="text-[0.65rem] font-body font-medium text-text/30 uppercase tracking-[0.15em] mb-4">
                Principles
              </h4>
              <ul className="space-y-2.5 text-sm font-body text-text/35">
                <li>First, Do No Harm</li>
                <li>Transparency Over Trust</li>
                <li>Your Data Stays Yours</li>
                <li>Math, Not Magic</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-white/[0.04] pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-body text-text/25 tracking-wide">
            <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
            <span>CC-BY-NC-SA 4.0 — The Alchymine Project</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
