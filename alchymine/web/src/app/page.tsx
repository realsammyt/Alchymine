"use client";

import SystemCard from "@/components/shared/SystemCard";
import ProtectedRoute from "@/components/shared/ProtectedRoute";

const SYSTEMS = [
  {
    name: "Personalized Intelligence",
    href: "/intelligence",
    icon: "\u{1F9E0}",
    description:
      "Numerology, astrology, and biorhythm engines map your unique identity profile using deterministic calculations.",
    status: "active" as const,
    features: [
      "Numerology Life Path & Expression",
      "Natal Chart Analysis",
      "Biorhythm Tracking",
    ],
    gradient: "from-primary-dark/30 to-primary/20",
  },
  {
    name: "Ethical Healing",
    href: "/healing",
    icon: "\u{1F33F}",
    description:
      "Personalized modalities for emotional and somatic healing, matched to your profile with full safety protocols.",
    status: "active" as const,
    features: ["Breathwork Sessions", "Modality Matching", "Crisis Resources"],
    gradient: "from-accent-dark/30 to-accent/20",
  },
  {
    name: "Generational Wealth",
    href: "/wealth",
    icon: "\u{1F4CA}",
    description:
      "Deterministic financial strategies across five wealth levers. All calculations are math-based, never AI-generated.",
    status: "active" as const,
    features: [
      "Wealth Archetype",
      "Five Levers Strategy",
      "Debt Payoff Calculator",
    ],
    gradient: "from-primary-dark/30 to-primary/20",
  },
  {
    name: "Creative Development",
    href: "/creative",
    icon: "\u{1F3A8}",
    description:
      "Guilford-based creative assessment to discover your Creative DNA and tools for sustained creative output.",
    status: "beta" as const,
    features: ["Creative Assessment", "Style Profile", "Project Collaboration"],
    gradient: "from-secondary-dark/30 to-secondary/20",
  },
  {
    name: "Perspective Enhancement",
    href: "/perspective",
    icon: "\u{1F52D}",
    description:
      "Kegan stages, mental models, cognitive reframing, and strategic clarity for how you see the world.",
    status: "beta" as const,
    features: [
      "Developmental Frameworks",
      "Cognitive Bias Awareness",
      "Scenario Planning",
    ],
    gradient: "from-accent-dark/30 to-accent/20",
  },
];

export default function DashboardPage() {
  return (
    <ProtectedRoute>
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Page Header */}
        <header className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold mb-3">
            <span className="text-gradient-gold">Dashboard</span>
          </h1>
          <p className="text-text/50 text-base max-w-2xl">
            Your personal transformation at a glance. Five integrated systems
            work together through a unified profile to support your growth.
          </p>
        </header>

        {/* Profile Summary Banner */}
        <section className="card-surface p-6 mb-8" aria-label="Profile summary">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-text mb-1">
                Unified Profile
              </h2>
              <p className="text-sm text-text/40">
                Complete your discovery assessment to unlock personalized
                insights across all five systems.
              </p>
            </div>
            <a
              href="/discover/intake"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-dark to-primary text-bg font-semibold rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(218,165,32,0.3)] hover:scale-[1.02] active:scale-100 whitespace-nowrap"
            >
              Begin Discovery
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
        </section>

        {/* System Cards Grid */}
        <section aria-label="Five transformation systems">
          <h2 className="sr-only">Transformation Systems</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {SYSTEMS.map((system) => (
              <SystemCard
                key={system.name}
                name={system.name}
                href={system.href}
                icon={<span aria-hidden="true">{system.icon}</span>}
                description={system.description}
                status={system.status}
                features={system.features}
                gradient={system.gradient}
              />
            ))}
          </div>
        </section>

        {/* Ethics & Transparency Note */}
        <section
          className="mt-10 card-surface p-5 border-l-2 border-primary/30"
          aria-label="Ethics and transparency"
        >
          <div className="flex items-start gap-3">
            <svg
              className="w-5 h-5 text-primary/60 mt-0.5 flex-shrink-0"
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
            <div>
              <h3 className="text-sm font-semibold text-text/70 mb-1">
                Ethics-First Design
              </h3>
              <p className="text-xs text-text/40 leading-relaxed">
                All financial calculations are deterministic (never
                AI-generated). Every system includes methodology panels showing
                evidence levels, sources, and calculation types. Your data stays
                on your infrastructure. No dark patterns, no artificial urgency,
                no manipulative design.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
    </ProtectedRoute>
  );
}
