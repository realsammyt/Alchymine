"use client";

import MethodologyPanel from "@/components/shared/MethodologyPanel";
import ApiStateView from "@/components/shared/ApiStateView";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";
import {
  getNumerology,
  getAstrology,
  NumerologyResponse,
  AstrologyResponse,
} from "@/lib/api";
import { useApi, useIntake } from "@/lib/useApi";
import { useAuth } from "@/lib/AuthContext";
import EvidenceBadge from "@/components/shared/EvidenceBadge";

const NUMEROLOGY_NUMBERS = [
  {
    name: "Life Path Number",
    description:
      "Derived from your complete birth date. Reveals your life purpose, natural talents, and the path of experiences you will encounter.",
    formula:
      "Reduce birth date (MM + DD + YYYY) to single digit or Master Number (11, 22, 33).",
  },
  {
    name: "Expression Number",
    description:
      "Calculated from the full name at birth using Pythagorean numerology. Shows your natural abilities, potential, and personal goals.",
    formula:
      "Convert each letter to its numeric value (A=1 through Z=8, cycling), then reduce.",
  },
  {
    name: "Soul Urge Number",
    description:
      "Derived from the vowels in your birth name. Reveals your inner desires, motivations, and what truly drives you.",
    formula: "Sum the numeric values of all vowels in birth name, then reduce.",
  },
  {
    name: "Personality Number",
    description:
      "Calculated from the consonants in your birth name. Represents how others perceive you and your outward persona.",
    formula:
      "Sum the numeric values of all consonants in birth name, then reduce.",
  },
];

const ASTROLOGY_SECTIONS = [
  {
    name: "Sun Sign",
    description:
      "Your core identity and ego expression, determined by the sun's position at birth.",
  },
  {
    name: "Moon Sign",
    description:
      "Your emotional nature and inner world, based on the moon's zodiac position at birth.",
  },
  {
    name: "Rising Sign",
    description:
      "Your outward persona and first impression, determined by the ascendant at birth time.",
  },
  {
    name: "Planetary Aspects",
    description:
      "Geometric relationships between planets that shape personality dynamics and life themes.",
  },
];

const BIORHYTHM_CYCLES = [
  {
    name: "Physical",
    period: "23 days",
    description: "Strength, coordination, endurance, and physical well-being.",
    color: "text-accent",
  },
  {
    name: "Emotional",
    period: "28 days",
    description: "Mood, sensitivity, creativity, and emotional resilience.",
    color: "text-secondary",
  },
  {
    name: "Intellectual",
    period: "33 days",
    description:
      "Analytical thinking, memory, learning capacity, and communication.",
    color: "text-primary",
  },
];

function NumberResult({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: number | string;
  subtitle?: string;
}) {
  return (
    <div className="card-surface-elevated glow-gold p-5 text-center">
      <div className="font-display text-3xl font-light text-gradient-gold mb-1">
        {value}
      </div>
      <div className="font-body text-sm font-medium text-text/80">{label}</div>
      {subtitle && (
        <div className="font-body text-xs text-text/40 mt-1">{subtitle}</div>
      )}
    </div>
  );
}

export default function IntelligencePage() {
  const { user } = useAuth();
  const { data: intake } = useIntake(user?.id);
  const hasIntake = !!intake?.fullName && !!intake?.birthDate;

  const numerology = useApi<NumerologyResponse>(
    hasIntake
      ? () => getNumerology(intake!.fullName!, intake!.birthDate!)
      : null,
    [intake?.fullName, intake?.birthDate],
  );

  const astrology = useApi<AstrologyResponse>(
    hasIntake && intake?.birthDate
      ? () =>
          getAstrology(
            intake!.birthDate!,
            intake?.birthTime ?? undefined,
            intake?.birthCity ?? undefined,
          )
      : null,
    [intake?.birthDate, intake?.birthTime],
  );

  return (
    <main
      id="main-content"
      className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <MotionReveal delay={0}>
          <header className="mb-10">
            <h1 className="font-display text-display-md font-light text-gradient-gold mb-3">
              Personalized Intelligence
            </h1>
            <hr className="rule-gold mb-4" aria-hidden="true" />
            <p className="font-body text-text/50 text-base max-w-2xl">
              Numerology, astrology, and biorhythm engines map your unique
              identity profile using deterministic calculations. Every result is
              reproducible and transparent.
            </p>
          </header>
        </MotionReveal>

        {/* Personalized Numerology Results */}
        {hasIntake && (
          <MotionReveal delay={0.1}>
            <section
              className="mb-12"
              aria-labelledby="your-numerology-heading"
            >
              <h2
                id="your-numerology-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{2728}"}
                </span>
                Your Numerology
              </h2>
              <hr className="rule-gold mb-6" aria-hidden="true" />
              <ApiStateView
                loading={numerology.loading}
                error={numerology.error}
                empty={!numerology.data}
                loadingText="Calculating your numerology..."
                onRetry={numerology.refetch}
              >
                {numerology.data && (
                  <MotionStagger className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
                    <MotionStaggerItem>
                      <NumberResult
                        label="Life Path"
                        value={numerology.data.life_path}
                        subtitle={
                          numerology.data.is_master_number
                            ? "Master Number"
                            : undefined
                        }
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Expression"
                        value={numerology.data.expression}
                        subtitle="Destiny Number"
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Soul Urge"
                        value={numerology.data.soul_urge}
                        subtitle="Heart's Desire"
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Personality"
                        value={numerology.data.personality}
                        subtitle="Outer Number"
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Personal Year"
                        value={numerology.data.personal_year}
                        subtitle="Current Cycle"
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Maturity"
                        value={numerology.data.maturity}
                      />
                    </MotionStaggerItem>
                  </MotionStagger>
                )}
              </ApiStateView>
            </section>
          </MotionReveal>
        )}

        {/* Personalized Astrology Results */}
        {hasIntake && (
          <MotionReveal delay={0.15}>
            <section className="mb-12" aria-labelledby="your-astrology-heading">
              <h2
                id="your-astrology-heading"
                className="section-heading-sm mb-2 flex items-center gap-3"
              >
                <span
                  className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl"
                  aria-hidden="true"
                >
                  {"\u{1F320}"}
                </span>
                Your Astrology
              </h2>
              <hr className="rule-gold mb-6" aria-hidden="true" />
              <ApiStateView
                loading={astrology.loading}
                error={astrology.error}
                empty={!astrology.data}
                loadingText="Calculating your natal chart..."
                onRetry={astrology.refetch}
              >
                {astrology.data && (
                  <MotionStagger className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
                    <MotionStaggerItem>
                      <NumberResult
                        label="Sun Sign"
                        value={astrology.data.sun_sign}
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Moon Sign"
                        value={astrology.data.moon_sign}
                      />
                    </MotionStaggerItem>
                    <MotionStaggerItem>
                      <NumberResult
                        label="Rising Sign"
                        value={astrology.data.rising_sign ?? "N/A"}
                        subtitle={
                          !astrology.data.rising_sign
                            ? "Birth time required"
                            : undefined
                        }
                      />
                    </MotionStaggerItem>
                  </MotionStagger>
                )}
              </ApiStateView>
            </section>
          </MotionReveal>
        )}

        {/* Numerology Education Section */}
        <MotionReveal delay={0.2}>
          <section className="mb-12" aria-labelledby="numerology-heading">
            <h2
              id="numerology-heading"
              className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
            >
              <span
                className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{1F522}"}
              </span>
              Numerology
              <EvidenceBadge level="traditional" />
            </h2>
            <hr className="rule-gold mb-6" aria-hidden="true" />

            <MotionStagger className="grid sm:grid-cols-2 gap-4 mb-4">
              {NUMEROLOGY_NUMBERS.map((num) => (
                <MotionStaggerItem key={num.name}>
                  <div className="card-surface p-5 h-full transition-all duration-300 hover:glow-gold hover:-translate-y-1">
                    <h3 className="font-display text-sm font-medium text-primary mb-2">
                      {num.name}
                    </h3>
                    <p className="font-body text-sm text-text/50 leading-relaxed mb-3">
                      {num.description}
                    </p>
                    <div className="bg-bg/50 rounded-lg px-3 py-2">
                      <p className="font-body text-xs text-text/30">
                        <span className="font-medium text-text/40">
                          Formula:
                        </span>{" "}
                        {num.formula}
                      </p>
                    </div>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>

            <MethodologyPanel
              title="Numerology"
              methodology="Pythagorean numerology uses a letter-to-number mapping system (A=1, B=2, ... I=9, J=1, ...) to derive core personality numbers from birth date and birth name. All calculations are fully deterministic: given the same inputs, the same outputs are always produced. No AI interpretation is used for the numerical calculations themselves."
              evidenceLevel="traditional"
              calculationType="deterministic"
              sources={[
                "Pythagorean number theory and letter-number correspondences (historical)",
                "Cultural numerology traditions across Chaldean, Kabbalistic, and Pythagorean systems",
                "Alchymine uses Pythagorean (Western) as the primary system for consistency",
              ]}
            />
          </section>
        </MotionReveal>

        {/* Astrology Section */}
        <MotionReveal delay={0.1}>
          <section className="mb-12" aria-labelledby="astrology-heading">
            <h2
              id="astrology-heading"
              className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
            >
              <span
                className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{2B50}"}
              </span>
              Astrology
              <EvidenceBadge level="traditional" />
            </h2>
            <hr className="rule-gold mb-6" aria-hidden="true" />

            <MotionStagger className="grid sm:grid-cols-2 gap-4 mb-4">
              {ASTROLOGY_SECTIONS.map((section) => (
                <MotionStaggerItem key={section.name}>
                  <div className="card-surface p-5 h-full transition-all duration-300 hover:glow-gold hover:-translate-y-1">
                    <h3 className="font-display text-sm font-medium text-secondary mb-2">
                      {section.name}
                    </h3>
                    <p className="font-body text-sm text-text/50 leading-relaxed">
                      {section.description}
                    </p>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>

            <MethodologyPanel
              title="Astrology"
              methodology="Natal chart calculations use the Swiss Ephemeris for precise planetary positions at the time and location of birth. Sign placements, house cusps (Placidus system), and aspects are all computed deterministically. AI-assisted interpretation synthesizes these positions into a readable narrative while adhering to established astrological frameworks."
              evidenceLevel="traditional"
              calculationType="hybrid"
              sources={[
                "Swiss Ephemeris (Astrodienst) for astronomical calculations",
                "Western tropical zodiac, Placidus house system",
                "Interpretive frameworks from Liz Greene, Robert Hand, and Stephen Arroyo",
              ]}
            />
          </section>
        </MotionReveal>

        {/* Biorhythm Section */}
        <MotionReveal delay={0.1}>
          <section className="mb-12" aria-labelledby="biorhythm-heading">
            <h2
              id="biorhythm-heading"
              className="section-heading-sm mb-2 flex items-center gap-3 flex-wrap"
            >
              <span
                className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-xl"
                aria-hidden="true"
              >
                {"\u{1F4C8}"}
              </span>
              Biorhythm
              <EvidenceBadge level="entertainment" />
            </h2>
            <p className="font-body text-[11px] text-text/30 italic mb-2">
              For entertainment and self-reflection purposes only.
            </p>
            <hr className="rule-gold mb-6" aria-hidden="true" />

            <MotionStagger className="grid sm:grid-cols-3 gap-4 mb-4">
              {BIORHYTHM_CYCLES.map((cycle) => (
                <MotionStaggerItem key={cycle.name}>
                  <div className="card-surface p-5 h-full transition-all duration-300 hover:glow-gold hover:-translate-y-1">
                    <div className="flex items-center justify-between mb-3">
                      <h3
                        className={`font-display text-sm font-medium ${cycle.color}`}
                      >
                        {cycle.name}
                      </h3>
                      <span className="font-body text-xs text-text/30">
                        {cycle.period}
                      </span>
                    </div>
                    <p className="font-body text-sm text-text/50 leading-relaxed">
                      {cycle.description}
                    </p>
                    <div className="mt-4 h-8 bg-bg/50 rounded-lg flex items-center justify-center">
                      <span className="font-body text-xs text-text/20">
                        Chart available after assessment
                      </span>
                    </div>
                  </div>
                </MotionStaggerItem>
              ))}
            </MotionStagger>

            <MethodologyPanel
              title="Biorhythm"
              methodology="Biorhythm theory posits three sinusoidal cycles beginning at birth: Physical (23 days), Emotional (28 days), and Intellectual (33 days). The value for each cycle on any given day is calculated as sin(2 * pi * t / period), where t is the number of days since birth. All calculations are purely mathematical and deterministic."
              evidenceLevel="emerging"
              calculationType="deterministic"
              sources={[
                'Thommen, George S. "Is This Your Day?" (1973) - foundational biorhythm reference',
                'Hines, T.M. "Comprehensive review of biorhythm theory" (1998) - critical review noting mixed evidence',
                "Note: Biorhythm theory has limited empirical support. Presented as a self-reflection framework, not a predictive tool.",
              ]}
            />
          </section>
        </MotionReveal>

        {/* CTA */}
        <MotionReveal delay={0.1}>
          <div className="text-center">
            <a
              href="/discover/intake"
              className="inline-flex items-center gap-2 px-6 py-3 min-h-[44px] bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(218,165,32,0.3)] hover:scale-[1.02] active:scale-100"
            >
              {hasIntake
                ? "Recalculate Your Profile"
                : "Calculate Your Profile"}
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
