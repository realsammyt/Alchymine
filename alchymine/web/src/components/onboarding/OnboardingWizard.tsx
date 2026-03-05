"use client";

import { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { calculateLifePathNumber } from "@/lib/numerology";

// ─── Types ────────────────────────────────────────────────────────────

interface OnboardingWizardProps {
  onComplete: () => void;
}

// ─── Pillar data ──────────────────────────────────────────────────────

const PILLARS = [
  {
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </svg>
    ),
    label: "Personal Intelligence",
    description: "Numerology, astrology & personality insights",
    href: "/intelligence",
    accentText: "text-primary",
    accentBg: "bg-primary/[0.08]",
    accentBorder: "border-primary/[0.15]",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
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
    ),
    label: "Ethical Healing",
    description: "Evidence-based modalities & breathwork",
    href: "/healing",
    accentText: "text-accent",
    accentBg: "bg-accent/[0.08]",
    accentBorder: "border-accent/[0.15]",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
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
    ),
    label: "Generational Wealth",
    description: "Wealth archetype & financial planning",
    href: "/wealth",
    accentText: "text-primary",
    accentBg: "bg-primary/[0.08]",
    accentBorder: "border-primary/[0.15]",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
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
    ),
    label: "Creative Forge",
    description: "Guilford assessment & creative DNA",
    href: "/creative",
    accentText: "text-secondary-light",
    accentBg: "bg-secondary/[0.08]",
    accentBorder: "border-secondary/[0.15]",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
    ),
    label: "Perspective Prism",
    description: "Kegan stages & cognitive bias awareness",
    href: "/perspective",
    accentText: "text-accent",
    accentBg: "bg-accent/[0.08]",
    accentBorder: "border-accent/[0.15]",
  },
];

// ─── Life path number meanings ────────────────────────────────────────

const LIFE_PATH_MEANINGS: Record<number, string> = {
  1: "The Leader — pioneering, independent, and driven to forge new paths.",
  2: "The Peacemaker — diplomatic, sensitive, and gifted at building harmony.",
  3: "The Creator — expressive, joyful, and overflowing with creative energy.",
  4: "The Builder — disciplined, reliable, and devoted to crafting lasting foundations.",
  5: "The Adventurer — freedom-seeking, versatile, and drawn to life's full spectrum.",
  6: "The Nurturer — compassionate, responsible, and committed to caring for others.",
  7: "The Seeker — introspective, analytical, and driven by a quest for deeper truth.",
  8: "The Achiever — ambitious, authoritative, and aligned with material and spiritual power.",
  9: "The Humanitarian — generous, wise, and devoted to uplifting the world.",
  11: "The Illuminator — a master number of heightened intuition and spiritual insight.",
  22: "The Master Builder — a master number combining vision with the power to manifest great works.",
  33: "The Master Teacher — a master number radiating unconditional love and profound wisdom.",
};

// ─── Step indicator dots ──────────────────────────────────────────────

function StepDots({ total, current }: { total: number; current: number }) {
  return (
    <div className="flex items-center justify-center gap-2" aria-hidden="true">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`rounded-full transition-all duration-300 ${
            i === current
              ? "w-5 h-2 bg-primary"
              : i < current
                ? "w-2 h-2 bg-primary/40"
                : "w-2 h-2 bg-white/[0.12]"
          }`}
        />
      ))}
    </div>
  );
}

// ─── Step variants ────────────────────────────────────────────────────

function slideVariants(prefersReducedMotion: boolean) {
  return {
    enter: (direction: number) => ({
      x: prefersReducedMotion ? 0 : direction * 40,
      opacity: 0,
    }),
    center: { x: 0, opacity: 1 },
    exit: (direction: number) => ({
      x: prefersReducedMotion ? 0 : direction * -40,
      opacity: 0,
    }),
  };
}

// ─── Step 1: Welcome ──────────────────────────────────────────────────

function StepWelcome() {
  return (
    <div className="text-center space-y-8">
      <div
        className="w-20 h-20 mx-auto rounded-full bg-primary/[0.08] border border-primary/[0.15] flex items-center justify-center"
        aria-hidden="true"
      >
        <svg
          className="w-9 h-9 text-primary/60"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>

      <div>
        <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-3">
          Welcome
        </p>
        <h2 className="font-display text-3xl font-light mb-3">
          Welcome to <span className="text-gradient-gold">Alchymine</span>
        </h2>
        <p className="font-body text-text/50 max-w-sm mx-auto leading-relaxed">
          Your personal transformation operating system — five integrated
          systems working together to unlock your full potential.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {PILLARS.map((pillar) => (
          <div
            key={pillar.label}
            className={`flex items-center gap-3 ${pillar.accentBg} border ${pillar.accentBorder} rounded-xl p-3`}
          >
            <div className={`flex-shrink-0 ${pillar.accentText} opacity-70`}>
              {pillar.icon}
            </div>
            <div>
              <div
                className={`font-display text-sm font-medium ${pillar.accentText}`}
              >
                {pillar.label}
              </div>
              <div className="font-body text-xs text-text/40 mt-0.5">
                {pillar.description}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Step 2: Quick info ───────────────────────────────────────────────

function StepPersonalize({
  name,
  birthDate,
  onNameChange,
  onBirthDateChange,
}: {
  name: string;
  birthDate: string;
  onNameChange: (v: string) => void;
  onBirthDateChange: (v: string) => void;
}) {
  const inputClass =
    "w-full bg-white/[0.04] border border-white/[0.10] rounded-xl px-4 py-3 font-body text-text placeholder:text-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors";

  return (
    <div className="space-y-8">
      <div className="text-center">
        <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-3">
          Step 2 of 4
        </p>
        <h2 className="font-display text-2xl font-light mb-2">
          Let&apos;s personalize your{" "}
          <span className="text-gradient-gold">experience</span>
        </h2>
        <p className="font-body text-text/50 text-sm">
          A few details help us reveal your unique path.
        </p>
      </div>

      <div className="space-y-4 max-w-sm mx-auto">
        <div>
          <label
            htmlFor="onboarding-name"
            className="block font-body text-sm text-text/60 mb-2"
          >
            Your name
          </label>
          <input
            id="onboarding-name"
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="Enter your name"
            className={inputClass}
            autoComplete="given-name"
          />
        </div>

        <div>
          <label
            htmlFor="onboarding-birthdate"
            className="block font-body text-sm text-text/60 mb-2"
          >
            Date of birth
          </label>
          <input
            id="onboarding-birthdate"
            type="date"
            value={birthDate}
            onChange={(e) => onBirthDateChange(e.target.value)}
            className={inputClass}
            max={new Date().toISOString().split("T")[0]}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Step 3: First insight ────────────────────────────────────────────

function StepFirstInsight({
  name,
  birthDate,
}: {
  name: string;
  birthDate: string;
}) {
  const lifePathNumber = birthDate ? calculateLifePathNumber(birthDate) : null;
  const meaning =
    lifePathNumber !== null
      ? (LIFE_PATH_MEANINGS[lifePathNumber] ?? "A unique and powerful path.")
      : null;

  const displayName = name.trim() || "Alchemist";

  return (
    <div className="space-y-8 text-center">
      <div>
        <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-3">
          Your First Insight
        </p>
        <h2 className="font-display text-2xl font-light mb-2">
          Hello, <span className="text-gradient-gold">{displayName}</span>
        </h2>
        <p className="font-body text-text/50 text-sm">
          Based on your birth date, we&apos;ve calculated your Life Path Number.
        </p>
      </div>

      {lifePathNumber !== null ? (
        <div className="flex flex-col items-center gap-6">
          <div className="relative">
            <div className="w-32 h-32 rounded-full bg-primary/[0.08] border border-primary/[0.20] flex items-center justify-center glow-gold">
              <span className="font-display text-5xl font-light text-gradient-gold">
                {lifePathNumber}
              </span>
            </div>
          </div>

          <div className="max-w-xs">
            <p className="font-display text-lg font-light text-text mb-2">
              Life Path{" "}
              <span className="text-gradient-gold">{lifePathNumber}</span>
            </p>
            <p className="font-body text-sm text-text/60 leading-relaxed">
              {meaning}
            </p>
          </div>
        </div>
      ) : (
        <div className="text-text/40 font-body text-sm">
          Enter your birth date in step 2 to see your Life Path Number.
        </div>
      )}
    </div>
  );
}

// ─── Step 4: Explore dashboard ────────────────────────────────────────

function StepExploreDashboard({ onComplete }: { onComplete: () => void }) {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-3">
          You&apos;re Ready
        </p>
        <h2 className="font-display text-2xl font-light mb-2">
          Explore Your <span className="text-gradient-gold">Dashboard</span>
        </h2>
        <p className="font-body text-text/50 text-sm max-w-sm mx-auto">
          Dive into any of the five systems below, or head to your dashboard for
          a full overview.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {PILLARS.map((pillar) => (
          <Link
            key={pillar.label}
            href={pillar.href}
            onClick={onComplete}
            className={`group flex items-center gap-3 ${pillar.accentBg} border ${pillar.accentBorder} rounded-xl p-4 transition-all duration-300 hover:-translate-y-0.5 hover:brightness-110`}
          >
            <div
              className={`flex-shrink-0 ${pillar.accentText} opacity-70 group-hover:opacity-100 transition-opacity`}
            >
              {pillar.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div
                className={`font-display text-sm font-medium ${pillar.accentText}`}
              >
                {pillar.label}
              </div>
              <div className="font-body text-xs text-text/40 mt-0.5">
                {pillar.description}
              </div>
            </div>
            <span
              className={`font-body text-xs ${pillar.accentText} opacity-60 group-hover:opacity-100 transition-opacity flex-shrink-0`}
            >
              Explore &rarr;
            </span>
          </Link>
        ))}
      </div>

      <div className="text-center pt-2">
        <Button onClick={onComplete} size="lg">
          Go to Dashboard
        </Button>
      </div>
    </div>
  );
}

// ─── Main wizard ──────────────────────────────────────────────────────

const TOTAL_STEPS = 4;

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const prefersReducedMotion = useReducedMotion() ?? false;
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");

  function goNext() {
    if (step < TOTAL_STEPS - 1) {
      setDirection(1);
      setStep((s) => s + 1);
    } else {
      handleComplete();
    }
  }

  function goBack() {
    if (step > 0) {
      setDirection(-1);
      setStep((s) => s - 1);
    }
  }

  function handleComplete() {
    if (typeof window !== "undefined") {
      localStorage.setItem("onboarding_complete", "true");
    }
    onComplete();
  }

  const canProceed =
    step === 0 ||
    step === 2 ||
    step === 3 ||
    (step === 1 && name.trim().length > 0 && birthDate.length > 0);

  const variants = slideVariants(prefersReducedMotion);

  const stepContent = [
    <StepWelcome key="welcome" />,
    <StepPersonalize
      key="personalize"
      name={name}
      birthDate={birthDate}
      onNameChange={setName}
      onBirthDateChange={setBirthDate}
    />,
    <StepFirstInsight key="insight" name={name} birthDate={birthDate} />,
    <StepExploreDashboard key="explore" onComplete={handleComplete} />,
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/90 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-label="Welcome to Alchymine"
    >
      <div className="w-full max-w-lg bg-surface border border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden">
        {/* Header progress bar */}
        <div className="h-1 bg-white/[0.04]">
          <div
            className="h-full bg-gradient-to-r from-primary-dark to-primary-light transition-all duration-500"
            style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
            role="progressbar"
            aria-valuenow={step + 1}
            aria-valuemin={1}
            aria-valuemax={TOTAL_STEPS}
            aria-label={`Step ${step + 1} of ${TOTAL_STEPS}`}
          />
        </div>

        {/* Step content */}
        <div className="p-6 sm:p-8 min-h-[420px] flex flex-col">
          <div className="flex-1 overflow-hidden relative">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={step}
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{
                  duration: prefersReducedMotion ? 0.01 : 0.3,
                  ease: [0.22, 1, 0.36, 1],
                }}
              >
                {stepContent[step]}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation */}
          {step < TOTAL_STEPS - 1 && (
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/[0.06]">
              <div>
                {step > 0 ? (
                  <Button variant="ghost" size="sm" onClick={goBack}>
                    Back
                  </Button>
                ) : (
                  <span />
                )}
              </div>

              <StepDots total={TOTAL_STEPS} current={step} />

              <Button
                variant="primary"
                size="sm"
                onClick={goNext}
                disabled={!canProceed}
              >
                {step === TOTAL_STEPS - 2 ? "See Insights" : "Next"}
              </Button>
            </div>
          )}

          {step === TOTAL_STEPS - 1 && (
            <div className="flex justify-center mt-6">
              <StepDots total={TOTAL_STEPS} current={step} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OnboardingWizard;
