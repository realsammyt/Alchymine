"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";

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
    <div className="min-h-screen">
      {/* ── Landing Header ──────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-bg/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 sm:px-6 py-3">
          <span className="text-gradient-gold font-bold text-xl">
            Alchymine
          </span>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-text/60 hover:text-text transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="text-sm px-4 py-2 bg-gradient-to-r from-primary-dark to-primary text-bg font-semibold rounded-lg transition-all duration-300 hover:shadow-[0_0_20px_rgba(218,165,32,0.3)] hover:scale-[1.02] active:scale-100"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-20 px-4 sm:px-6 relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-40 left-1/4 w-[300px] h-[300px] bg-secondary/5 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-xs text-primary mb-6">
            <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
            Open-Source Personal Transformation
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            <span className="text-gradient-gold">
              Discover Who You Truly Are
            </span>
            <br />
            <span className="text-text/90">
              Through Five Integrated Systems
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-text/50 max-w-2xl mx-auto mb-10 leading-relaxed">
            AI-powered identity mapping, ethical healing, wealth strategy,
            creative development, and perspective enhancement — built on
            transparent methodology and open-source principles.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-primary-dark to-primary text-bg font-semibold rounded-xl text-base transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.3)] hover:scale-[1.02] active:scale-100"
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
              className="inline-flex items-center gap-2 px-6 py-3.5 border border-white/10 text-text/70 rounded-xl text-base hover:bg-white/5 hover:text-text transition-all duration-200"
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

          {/* Trust strip */}
          <div className="mt-14 flex flex-wrap items-center justify-center gap-6 text-xs text-text/30">
            <span className="flex items-center gap-1.5">
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
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
              </svg>
              Ethics-First
            </span>
            <span className="w-px h-3 bg-white/10" />
            <span className="flex items-center gap-1.5">
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
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
              </svg>
              Open Source
            </span>
            <span className="w-px h-3 bg-white/10" />
            <span className="flex items-center gap-1.5">
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
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              Your Data Stays Yours
            </span>
            <span className="w-px h-3 bg-white/10" />
            <span>CC-BY-NC-SA 4.0</span>
          </div>
        </div>
      </section>

      {/* ── Five Systems ────────────────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6" id="five-systems">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              <span className="text-gradient-gold">
                Five Integrated Systems
              </span>
            </h2>
            <p className="text-text/50 max-w-2xl mx-auto">
              Each system provides a unique lens on your transformation.
              Together, they create a unified profile that grows with you.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {FIVE_SYSTEMS.map((system) => {
              const colors = colorClass(system.color);
              return (
                <div
                  key={system.name}
                  className={`group card-surface p-6 transition-all duration-300 ${colors.glow}`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className={`w-10 h-10 rounded-xl ${colors.bg} ${colors.border} border flex items-center justify-center`}
                    >
                      <SystemIcon icon={system.icon} className={colors.text} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-text">{system.name}</h3>
                      <p className={`text-xs ${colors.text}`}>
                        {system.tagline}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-text/50 mb-4 leading-relaxed">
                    {system.description}
                  </p>
                  <ul className="space-y-1.5">
                    {system.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-center gap-2 text-xs text-text/40"
                      >
                        <svg
                          className={`w-3.5 h-3.5 ${colors.text} flex-shrink-0`}
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
              );
            })}
          </div>
        </div>
      </section>

      {/* ── How It Works ────────────────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6 bg-surface/30" id="how-it-works">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              <span className="text-gradient-gold">How It Works</span>
            </h2>
            <p className="text-text/50 max-w-xl mx-auto">
              Three steps from curiosity to a personalized transformation path.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <span className="text-primary font-bold text-lg">
                    {item.step}
                  </span>
                </div>
                <h3 className="font-semibold text-lg text-text mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-text/50 leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>

          {/* Connecting lines (desktop only) */}
          <div className="hidden md:flex justify-center mt-[-180px] mb-[120px] pointer-events-none">
            <div className="flex items-center gap-0 w-[60%]">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent via-primary/20 to-primary/20" />
              <div className="flex-1 h-px bg-gradient-to-r from-primary/20 via-primary/20 to-transparent" />
            </div>
          </div>
        </div>
      </section>

      {/* ── Ethics & Transparency ───────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6" id="ethics">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              <span className="text-gradient-gold">Built on Trust</span>
            </h2>
            <p className="text-text/50 max-w-xl mx-auto">
              Radical transparency isn&apos;t a feature — it&apos;s the
              foundation.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {TRUST_CARDS.map((card) => (
              <div
                key={card.title}
                className="card-surface p-6 flex items-start gap-4"
              >
                <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <TrustIcon icon={card.icon} className="text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-text mb-1">{card.title}</h3>
                  <p className="text-sm text-text/50 leading-relaxed">
                    {card.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ─────────────────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6 bg-surface/30">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Invitation card */}
            <div className="card-surface p-8 text-center flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center">
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
                <h3 className="text-xl font-semibold text-text mb-2">
                  Have an Invitation?
                </h3>
                <p className="text-sm text-text/50 mb-6">
                  If you have an invitation code, create your account and start
                  your transformation journey today.
                </p>
              </div>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-dark to-primary text-bg font-semibold rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(218,165,32,0.3)] hover:scale-[1.02] active:scale-100"
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

            {/* Waitlist card */}
            <div className="card-surface p-8 text-center flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-accent/20 flex items-center justify-center">
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
                <h3 className="text-xl font-semibold text-text mb-2">
                  Join the Waitlist
                </h3>
                <p className="text-sm text-text/50 mb-6">
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
                  <input
                    type="email"
                    required
                    value={waitlistEmail}
                    onChange={(e) => setWaitlistEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="flex-1 bg-bg border border-white/10 rounded-lg px-4 py-2.5 text-sm text-text placeholder-text/30 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30 transition-colors"
                  />
                  <button
                    type="submit"
                    className="px-5 py-2.5 bg-accent/20 text-accent border border-accent/20 rounded-lg text-sm font-medium hover:bg-accent/30 transition-colors flex-shrink-0"
                  >
                    Join
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Founding Quote ──────────────────────────────────────────────── */}
      <section className="py-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center">
          <blockquote className="text-lg sm:text-xl text-text/60 italic leading-relaxed mb-4">
            &ldquo;We built Alchymine because personal transformation tools
            shouldn&apos;t require blind trust. Every algorithm is visible,
            every methodology is cited, every financial calculation is
            deterministic. This is open-source self-discovery.&rdquo;
          </blockquote>
          <p className="text-sm text-text/30">The Alchymine Project</p>
          <a
            href="https://github.com/realsammyt/Alchymine"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-4 text-xs text-text/20 hover:text-text/40 transition-colors"
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
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-12 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-8">
            {/* Brand */}
            <div>
              <span className="text-gradient-gold font-bold text-lg block mb-2">
                Alchymine
              </span>
              <p className="text-xs text-text/30 leading-relaxed">
                Open-source, AI-powered Personal Transformation Operating
                System. Licensed under CC-BY-NC-SA 4.0.
              </p>
            </div>

            {/* Links */}
            <div>
              <h4 className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-3">
                Navigation
              </h4>
              <ul className="space-y-2 text-sm text-text/30">
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
              <h4 className="text-xs font-semibold text-text/50 uppercase tracking-wider mb-3">
                Principles
              </h4>
              <ul className="space-y-2 text-sm text-text/30">
                <li>First, Do No Harm</li>
                <li>Transparency Over Trust</li>
                <li>Your Data Stays Yours</li>
                <li>Math, Not Magic</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-white/5 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text/20">
            <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
            <span>CC-BY-NC-SA 4.0 — The Alchymine Project</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
