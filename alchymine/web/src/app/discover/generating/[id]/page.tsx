"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { getReport, ApiError } from "@/lib/api";
import { MotionReveal } from "@/components/shared/MotionReveal";

const GENERATION_STEPS = [
  { label: "Calculating numerology...", icon: "numerology", duration: 4000 },
  { label: "Mapping astrology...", icon: "astrology", duration: 6000 },
  { label: "Analyzing personality...", icon: "personality", duration: 5000 },
  { label: "Mapping archetypes...", icon: "archetype", duration: 5000 },
  { label: "Building your profile...", icon: "profile", duration: 10000 },
];

function StepIcon({ icon, className }: { icon: string; className?: string }) {
  const cls = className ?? "w-5 h-5";
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
    case "numerology":
      return (
        <svg {...props}>
          <rect width="18" height="18" x="3" y="3" rx="2" />
          <path d="M12 8v8" />
          <path d="M8 12h8" />
        </svg>
      );
    case "astrology":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a7 7 0 1 0 7 7" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
    case "personality":
      return (
        <svg {...props}>
          <path d="M12 2a8 8 0 0 0-8 8c0 6 8 12 8 12s8-6 8-12a8 8 0 0 0-8-8z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      );
    case "archetype":
      return (
        <svg {...props}>
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
    case "profile":
      return (
        <svg {...props}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <polyline points="16 11 18 13 22 9" />
        </svg>
      );
    default:
      return null;
  }
}

export default function GeneratingPage() {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;

  const [currentStep, setCurrentStep] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [networkWarning, setNetworkWarning] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const animationRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStartRef = useRef<number | null>(null);
  const networkFailuresRef = useRef(0);

  // Animate through the visual steps
  useEffect(() => {
    let stepIndex = 0;
    const totalDuration = GENERATION_STEPS.reduce(
      (s, step) => s + step.duration,
      0,
    );
    let elapsed = 0;

    animationRef.current = setInterval(() => {
      elapsed += 100;
      const progressPercent = Math.min((elapsed / totalDuration) * 90, 90);
      setOverallProgress(progressPercent);

      let cumulative = 0;
      for (let i = 0; i < GENERATION_STEPS.length; i++) {
        cumulative += GENERATION_STEPS[i].duration;
        if (elapsed < cumulative) {
          if (i !== stepIndex) {
            stepIndex = i;
            setCurrentStep(i);
          }
          break;
        }
      }

      if (elapsed >= totalDuration) {
        setCurrentStep(GENERATION_STEPS.length - 1);
      }
    }, 100);

    return () => {
      if (animationRef.current) clearInterval(animationRef.current);
    };
  }, []);

  // Poll the API for report completion
  useEffect(() => {
    if (!reportId) return;

    const POLL_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes
    const MAX_NETWORK_FAILURES = 10;
    const NETWORK_WARNING_THRESHOLD = 3;

    let delay = 4000; // Start at 4s, back off on 429
    let stopped = false;
    pollStartRef.current = Date.now();
    networkFailuresRef.current = 0;

    const poll = async () => {
      if (stopped) return;

      // Check poll timeout
      if (Date.now() - (pollStartRef.current ?? 0) >= POLL_TIMEOUT_MS) {
        console.error("[generating] poll timeout reached");
        setError("Report generation timed out. Please try again.");
        stopped = true;
        if (animationRef.current) clearInterval(animationRef.current);
        return;
      }

      try {
        console.log("[generating] polling report", reportId, "delay:", delay);
        const report = await getReport(reportId);
        console.log("[generating] report status:", report.status);
        if (report.status === "complete") {
          console.log("[generating] report complete — redirecting");
          setOverallProgress(100);
          stopped = true;
          if (animationRef.current) clearInterval(animationRef.current);
          setTimeout(() => {
            router.push(`/discover/report/${reportId}`);
          }, 800);
          return;
        } else if (report.status === "failed") {
          const errorMsg =
            report.error || "Report generation failed. Please try again.";
          console.error("[generating] report failed:", errorMsg);
          setError(errorMsg);
          stopped = true;
          if (animationRef.current) clearInterval(animationRef.current);
          return;
        }
        // Reset delay and network failure count on success
        delay = 4000;
        networkFailuresRef.current = 0;
        setNetworkWarning(null);
      } catch (err) {
        if (err instanceof ApiError && err.status === 202) {
          console.log("[generating] still generating (202)");
          networkFailuresRef.current = 0;
          setNetworkWarning(null);
        } else if (err instanceof ApiError && err.status === 429) {
          // Rate limited — back off
          delay = Math.min(delay * 2, 30000);
          console.warn(
            "[generating] rate limited (429), backing off to",
            delay,
          );
          networkFailuresRef.current = 0;
          setNetworkWarning(null);
        } else {
          // Network or unknown error
          networkFailuresRef.current += 1;
          const failures = networkFailuresRef.current;
          console.error(
            "[generating] polling error (failure #" + failures + "):",
            err,
          );
          if (failures >= MAX_NETWORK_FAILURES) {
            setError(
              "Unable to reach the server. Please check your connection and try again.",
            );
            stopped = true;
            if (animationRef.current) clearInterval(animationRef.current);
            return;
          } else if (failures >= NETWORK_WARNING_THRESHOLD) {
            setNetworkWarning(
              "Having trouble reaching the server. Still trying...",
            );
          }
        }
      }
      if (!stopped) {
        pollRef.current = setTimeout(poll, delay);
      }
    };

    pollRef.current = setTimeout(poll, delay);

    return () => {
      stopped = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [reportId, router]);

  const step = GENERATION_STEPS[currentStep];

  return (
    <div className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
      <div className="w-full max-w-md text-center">
        {/* Animated orb */}
        <MotionReveal>
          <div className="relative w-32 h-32 mx-auto mb-10">
            {/* Outer glow ring */}
            <div className="absolute inset-0 rounded-full bg-primary/[0.08] animate-pulse-gold" />
            {/* Spinning gradient ring */}
            <div
              className="absolute inset-2 rounded-full border-2 border-transparent border-t-primary border-r-primary/50 animate-spin"
              style={{ animationDuration: "3s" }}
            />
            {/* Inner shimmer */}
            <div className="absolute inset-4 rounded-full bg-gradient-to-br from-primary-dark/20 to-secondary-dark/20 shimmer-gold" />
            {/* Center icon */}
            <div className="absolute inset-0 flex items-center justify-center">
              <StepIcon icon={step.icon} className="w-8 h-8 text-primary/70" />
            </div>
          </div>
        </MotionReveal>

        {/* Step label */}
        <h2
          className="font-display text-xl sm:text-2xl font-light text-text mb-2 animate-fade-in"
          key={step.label}
        >
          {step.label}
        </h2>
        <p className="text-text/35 text-sm font-body mb-8">
          Our deterministic engines are analyzing your unique data.
        </p>

        {/* Progress bar */}
        <div
          className="w-full bg-white/[0.04] rounded-full h-2 mb-4 overflow-hidden"
          role="progressbar"
          aria-valuenow={Math.round(overallProgress)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Report generation progress"
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-300 ease-out relative overflow-hidden"
            style={{ width: `${overallProgress}%` }}
          >
            <div className="absolute inset-0 shimmer-gold opacity-50" />
          </div>
        </div>
        <p className="text-xs font-body text-text/25 tracking-wide">
          {Math.round(overallProgress)}% complete
        </p>

        {/* Step indicators */}
        <div className="mt-10 space-y-2.5">
          {GENERATION_STEPS.map((s, idx) => (
            <div
              key={s.label}
              className={`flex items-center gap-3 text-sm font-body transition-all duration-500 ${
                idx < currentStep
                  ? "text-primary/70"
                  : idx === currentStep
                    ? "text-text"
                    : "text-text/15"
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-500 ${
                  idx < currentStep
                    ? "bg-primary text-bg"
                    : idx === currentStep
                      ? "border-2 border-primary glow-gold"
                      : "border border-white/[0.08]"
                }`}
              >
                {idx < currentStep && (
                  <svg
                    className="w-2.5 h-2.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </div>
              <span className="tracking-wide">
                {s.label.replace("...", "")}
              </span>
            </div>
          ))}
        </div>

        {/* Network warning */}
        {networkWarning && !error && (
          <MotionReveal y={8}>
            <div className="mt-8 p-4 rounded-xl card-surface text-sm font-body text-text/60">
              <p>{networkWarning}</p>
            </div>
          </MotionReveal>
        )}

        {/* Error state */}
        {error && (
          <MotionReveal y={8}>
            <div className="mt-8 p-4 rounded-xl card-surface text-sm font-body text-text/60">
              <p className="mb-2">{error}</p>
              <button
                onClick={() => router.push("/discover/intake")}
                className="text-primary hover:text-primary-light underline transition-colors duration-300 touch-target"
              >
                Start over
              </button>
            </div>
          </MotionReveal>
        )}
      </div>
    </div>
  );
}
