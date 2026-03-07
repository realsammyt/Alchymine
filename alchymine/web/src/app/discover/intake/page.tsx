"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { getProfile, saveIntake } from "@/lib/api";
import Button from "@/components/shared/Button";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

const INTENTIONS = [
  { value: "career", label: "Career Growth", icon: "briefcase" },
  { value: "love", label: "Love & Relationships", icon: "heart" },
  { value: "purpose", label: "Life Purpose", icon: "compass" },
  { value: "money", label: "Financial Freedom", icon: "chart" },
  { value: "health", label: "Health & Vitality", icon: "leaf" },
  { value: "family", label: "Family & Legacy", icon: "users" },
  { value: "business", label: "Business Building", icon: "rocket" },
  { value: "legacy", label: "Legacy & Impact", icon: "building" },
] as const;

interface IntakeFormData {
  fullName: string;
  birthDate: string;
  birthTime: string;
  birthCity: string;
  intentions: string[];
}

const MAX_INTENTIONS = 3;

function IntentionIcon({
  icon,
  className,
}: {
  icon: string;
  className?: string;
}) {
  const cls = className ?? "w-4 h-4";
  const props = {
    className: cls,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  switch (icon) {
    case "briefcase":
      return (
        <svg {...props}>
          <rect width="20" height="14" x="2" y="7" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      );
    case "heart":
      return (
        <svg {...props}>
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        </svg>
      );
    case "compass":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
      );
    case "chart":
      return (
        <svg {...props}>
          <line x1="12" y1="20" x2="12" y2="10" />
          <line x1="18" y1="20" x2="18" y2="4" />
          <line x1="6" y1="20" x2="6" y2="16" />
        </svg>
      );
    case "leaf":
      return (
        <svg {...props}>
          <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
      );
    case "users":
      return (
        <svg {...props}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "rocket":
      return (
        <svg {...props}>
          <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
          <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
          <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
          <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
        </svg>
      );
    case "building":
      return (
        <svg {...props}>
          <line x1="3" y1="22" x2="21" y2="22" />
          <line x1="6" y1="18" x2="6" y2="11" />
          <line x1="10" y1="18" x2="10" y2="11" />
          <line x1="14" y1="18" x2="14" y2="11" />
          <line x1="18" y1="18" x2="18" y2="11" />
          <polygon points="12 2 20 7 4 7" />
        </svg>
      );
    default:
      return null;
  }
}

export default function IntakePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [formData, setFormData] = useState<IntakeFormData>({
    fullName: "",
    birthDate: "",
    birthTime: "",
    birthCity: "",
    intentions: [],
  });
  const [errors, setErrors] = useState<
    Partial<Record<keyof IntakeFormData | "intentions", string>>
  >({});

  // Pre-fill from saved profile (enables cross-device sync)
  useEffect(() => {
    if (!user?.id) return;
    getProfile(user.id)
      .then((profile) => {
        if (profile.intake) {
          setFormData((prev) => ({
            fullName: profile.intake!.full_name || prev.fullName,
            birthDate: profile.intake!.birth_date || prev.birthDate,
            birthTime: profile.intake!.birth_time || prev.birthTime,
            birthCity: profile.intake!.birth_city || prev.birthCity,
            intentions:
              profile.intake!.intentions?.length
                ? profile.intake!.intentions
                : prev.intentions,
          }));
        }
      })
      .catch(() => {
        // No saved profile yet — that's fine, user fills in fresh
      });
  }, [user?.id]);

  function validate(): boolean {
    const newErrors: Partial<Record<keyof IntakeFormData, string>> = {};

    if (!formData.fullName.trim() || formData.fullName.trim().length < 2) {
      newErrors.fullName =
        "Please enter your full name (at least 2 characters).";
    }
    if (!formData.birthDate) {
      newErrors.birthDate = "Please select your birth date.";
    }
    if (formData.intentions.length === 0) {
      newErrors.intentions = "Please select at least one intention.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    // Store in sessionStorage for the assessment page to pick up.
    // Include `intention` (primary) for backward compat with report creation.
    sessionStorage.setItem(
      "alchymine_intake",
      JSON.stringify({
        ...formData,
        intention: formData.intentions[0],
      }),
    );

    // Persist to server profile for cross-device sync and durability.
    // Best-effort — don't block navigation if the API call fails.
    if (user?.id) {
      saveIntake(user.id, {
        full_name: formData.fullName,
        birth_date: formData.birthDate,
        birth_time: formData.birthTime || null,
        birth_city: formData.birthCity || null,
        intention: formData.intentions[0],
        intentions: formData.intentions,
      }).catch(() => {});
    }

    router.push("/discover/assessment");
  }

  const inputClass =
    "w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all duration-300 [color-scheme:dark]";

  return (
    <div className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
      <div className="w-full max-w-lg">
        {/* Header */}
        <MotionReveal>
          <div className="text-center mb-10">
            <h1 className="font-display text-display-md font-light mb-3">
              Let&apos;s <span className="text-gradient-gold">Begin</span>
            </h1>
            <hr className="rule-gold my-5 max-w-[80px] mx-auto" />
            <p className="text-text/40 font-body leading-relaxed">
              Tell us a bit about yourself. This information powers the
              deterministic engines behind your profile.
            </p>
          </div>
        </MotionReveal>

        <MotionReveal delay={0.15}>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Full Name */}
            <div>
              <label
                htmlFor="fullName"
                className="block text-sm font-body font-medium text-text/60 mb-2"
              >
                Full Name{" "}
                <span className="text-primary" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="fullName"
                type="text"
                required
                aria-required="true"
                aria-describedby={
                  errors.fullName ? "fullName-error" : undefined
                }
                placeholder="e.g. Maya Angelou"
                value={formData.fullName}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, fullName: e.target.value }))
                }
                className={inputClass}
              />
              {errors.fullName && (
                <p
                  id="fullName-error"
                  role="alert"
                  className="mt-1.5 text-sm font-body text-primary-dark"
                >
                  {errors.fullName}
                </p>
              )}
            </div>

            {/* Birth Date */}
            <div>
              <label
                htmlFor="birthDate"
                className="block text-sm font-body font-medium text-text/60 mb-2"
              >
                Birth Date{" "}
                <span className="text-primary" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="birthDate"
                type="date"
                required
                aria-required="true"
                aria-describedby={
                  errors.birthDate ? "birthDate-error" : undefined
                }
                value={formData.birthDate}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    birthDate: e.target.value,
                  }))
                }
                className={inputClass}
              />
              {errors.birthDate && (
                <p
                  id="birthDate-error"
                  role="alert"
                  className="mt-1.5 text-sm font-body text-primary-dark"
                >
                  {errors.birthDate}
                </p>
              )}
            </div>

            {/* Birth Time (optional) */}
            <div>
              <label
                htmlFor="birthTime"
                className="block text-sm font-body font-medium text-text/60 mb-2"
              >
                Birth Time{" "}
                <span className="text-text/25 font-normal">
                  (optional — enables Rising sign)
                </span>
              </label>
              <input
                id="birthTime"
                type="time"
                value={formData.birthTime}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    birthTime: e.target.value,
                  }))
                }
                className={inputClass}
              />
            </div>

            {/* Birth City (optional) */}
            <div>
              <label
                htmlFor="birthCity"
                className="block text-sm font-body font-medium text-text/60 mb-2"
              >
                Birth City{" "}
                <span className="text-text/25 font-normal">
                  (optional — enables house calculations)
                </span>
              </label>
              <input
                id="birthCity"
                type="text"
                placeholder="e.g. Toronto, Canada"
                value={formData.birthCity}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    birthCity: e.target.value,
                  }))
                }
                className={inputClass}
              />
            </div>

            {/* Intention Selector — multi-select (1-3) */}
            <fieldset>
              <legend className="block text-sm font-body font-medium text-text/60 mb-1">
                What brings you here?{" "}
                <span className="text-primary" aria-hidden="true">
                  *
                </span>
              </legend>
              <p
                id="intentions-hint"
                className="text-xs font-body text-text/30 mb-3"
              >
                Select up to {MAX_INTENTIONS} that resonate most
              </p>
              <MotionStagger
                staggerDelay={0.04}
                className="grid grid-cols-2 gap-3"
              >
                {INTENTIONS.map((intent) => {
                  const selected = formData.intentions.includes(intent.value);
                  const atMax =
                    formData.intentions.length >= MAX_INTENTIONS && !selected;
                  return (
                    <MotionStaggerItem key={intent.value}>
                      <button
                        type="button"
                        disabled={atMax}
                        aria-pressed={selected}
                        onClick={() =>
                          setFormData((prev) => ({
                            ...prev,
                            intentions: selected
                              ? prev.intentions.filter(
                                  (v) => v !== intent.value,
                                )
                              : [...prev.intentions, intent.value],
                          }))
                        }
                        className={`w-full flex items-center gap-2.5 px-4 py-3 rounded-xl border text-left text-sm font-body transition-all duration-300 touch-target focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg focus-visible:outline-none ${
                          selected
                            ? "border-primary/40 bg-primary/[0.08] text-text glow-gold"
                            : atMax
                              ? "border-white/[0.04] bg-white/[0.01] text-text/20 cursor-not-allowed"
                              : "border-white/[0.06] bg-white/[0.02] text-text/50 hover:border-white/[0.12] hover:bg-white/[0.04]"
                        }`}
                      >
                        <IntentionIcon
                          icon={intent.icon}
                          className={`w-4 h-4 flex-shrink-0 ${
                            selected ? "text-primary" : "text-text/30"
                          }`}
                        />
                        <span className="flex-1">{intent.label}</span>
                        {selected && (
                          <span
                            className="text-xs text-primary/60 font-medium"
                            aria-hidden="true"
                          >
                            {formData.intentions.indexOf(intent.value) + 1}
                          </span>
                        )}
                      </button>
                    </MotionStaggerItem>
                  );
                })}
              </MotionStagger>
              {errors.intentions && (
                <p
                  id="intentions-error"
                  role="alert"
                  className="mt-1.5 text-sm font-body text-primary-dark"
                >
                  {errors.intentions}
                </p>
              )}
            </fieldset>

            {/* Submit */}
            <div className="pt-4">
              <Button type="submit" size="lg" className="w-full">
                Continue to Assessment
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
              </Button>
            </div>
          </form>
        </MotionReveal>
      </div>
    </div>
  );
}
