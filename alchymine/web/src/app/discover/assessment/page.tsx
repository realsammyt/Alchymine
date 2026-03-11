"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import {
  LIKERT_LABELS,
  filterQuestionsBySection,
  type QuestionCategory,
} from "@/lib/questions";
import {
  createReport,
  getProfile,
  reassessProfile,
  IntakePayload,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import Button from "@/components/shared/Button";
import ProgressBar from "@/components/shared/ProgressBar";
import { MotionReveal } from "@/components/shared/MotionReveal";

// Section-to-system mapping
const SECTION_TO_SYSTEM: Record<string, string> = {
  big_five: "intelligence",
  attachment: "intelligence",
  risk_tolerance: "intelligence",
  enneagram: "intelligence",
  perspective: "perspective",
  creativity: "creative",
};

export default function AssessmentPage() {
  const router = useRouter();
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const sectionsParam = searchParams.get("sections");
  const selectedSections = sectionsParam
    ? (sectionsParam.split(",") as QuestionCategory[])
    : undefined;

  const questions = filterQuestionsBySection(selectedSections);
  const totalQuestions = questions.length;

  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direction, setDirection] = useState<"next" | "prev">("next");
  const [showCompletion, setShowCompletion] = useState(false);

  // Verify intake data exists — try sessionStorage first, then fall back
  // to the server profile (supports cross-device sync).
  useEffect(() => {
    const intake = sessionStorage.getItem("alchymine_intake");
    if (intake) return;

    if (!user?.id) {
      router.replace("/discover/intake");
      return;
    }

    // Try loading from saved profile
    getProfile(user.id)
      .then((profile) => {
        if (profile.intake) {
          sessionStorage.setItem(
            "alchymine_intake",
            JSON.stringify({
              fullName: profile.intake.full_name,
              birthDate: profile.intake.birth_date,
              birthTime: profile.intake.birth_time || "",
              birthCity: profile.intake.birth_city || "",
              intentions: profile.intake.intentions,
              intention: profile.intake.intention,
            }),
          );
        } else {
          router.replace("/discover/intake");
        }
      })
      .catch((err) => {
        // Only redirect to intake if the profile truly doesn't exist (404).
        // On transient errors (500, network), stay on the page — sessionStorage
        // may have the data from the previous page.
        if (err?.status === 404) {
          router.replace("/discover/intake");
        } else {
          console.warn("Failed to load profile (non-404):", err);
        }
      });
  }, [router, user?.id]);

  useEffect(() => {
    if (!selectedSections || !user?.id) return;

    // In section mode, load existing responses from profile
    getProfile(user.id)
      .then((profile) => {
        const existing = profile.intake?.assessment_responses;
        if (existing) {
          sessionStorage.setItem(
            "alchymine_existing_responses",
            JSON.stringify(existing),
          );
        }
      })
      .catch(() => {});
  }, [selectedSections, user?.id]);

  const question = questions[currentIndex];
  const progress = (Object.keys(responses).length / totalQuestions) * 100;
  const isLastQuestion = currentIndex === totalQuestions - 1;
  const allAnswered = Object.keys(responses).length === totalQuestions;

  const handleSubmit = useCallback(
    async (finalResponses: Record<string, number>) => {
      setSubmitting(true);
      setError(null);

      try {
        const existingRaw = sessionStorage.getItem(
          "alchymine_existing_responses",
        );
        const existingResponses = existingRaw ? JSON.parse(existingRaw) : {};
        const mergedResponses = { ...existingResponses, ...finalResponses };

        if (selectedSections && user?.id) {
          const systems = [
            ...new Set(selectedSections.map((s) => SECTION_TO_SYSTEM[s])),
          ];
          for (const system of systems) {
            await reassessProfile(user.id, system, mergedResponses);
          }
          router.push("/profile");
          return;
        }

        const intakeRaw = sessionStorage.getItem("alchymine_intake");
        if (!intakeRaw) {
          router.replace("/discover/intake");
          return;
        }

        const intakeData = JSON.parse(intakeRaw);

        const intake: IntakePayload = {
          full_name: intakeData.fullName,
          birth_date: intakeData.birthDate,
          birth_time: intakeData.birthTime || null,
          birth_city: intakeData.birthCity || null,
          intention: intakeData.intention ?? intakeData.intentions?.[0],
          intentions:
            intakeData.intentions ??
            (intakeData.intention ? [intakeData.intention] : []),
          assessment_responses: mergedResponses,
          wealth_context: intakeData.wealth_context ?? null,
        };

        const result = await createReport(intake);
        sessionStorage.setItem("alchymine_report_id", result.id);
        router.push(`/discover/generating/${result.id}`);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.",
        );
        setSubmitting(false);
      }
    },
    [router, selectedSections, user?.id],
  );

  const handleAnswer = useCallback(
    (value: number) => {
      const newResponses = { ...responses, [question.id]: value };
      setResponses(newResponses);

      if (
        isLastQuestion &&
        Object.keys(newResponses).length === totalQuestions
      ) {
        // Show completion screen instead of auto-submitting
        setShowCompletion(true);
      } else if (!isLastQuestion) {
        setDirection("next");
        setTimeout(() => {
          setCurrentIndex((prev) => prev + 1);
        }, 200);
      }
    },
    [responses, question, isLastQuestion],
  );

  function goBack() {
    if (currentIndex > 0) {
      setDirection("prev");
      setCurrentIndex((prev) => prev - 1);
    }
  }

  function getCategoryLabel(category: string): string {
    switch (category) {
      case "big_five":
        return "Personality";
      case "attachment":
        return "Attachment Style";
      case "risk_tolerance":
        return "Risk Tolerance";
      case "enneagram":
        return "Enneagram";
      case "creativity":
        return "Creativity";
      case "perspective":
        return "Perspective";
      default:
        return "";
    }
  }

  function getCategoryColor(category: string): {
    bg: string;
    text: string;
    border: string;
  } {
    switch (category) {
      case "big_five":
        return {
          bg: "bg-primary/[0.06]",
          text: "text-primary/70",
          border: "border-primary/[0.12]",
        };
      case "attachment":
        return {
          bg: "bg-accent/[0.06]",
          text: "text-accent/70",
          border: "border-accent/[0.12]",
        };
      case "risk_tolerance":
        return {
          bg: "bg-secondary/[0.06]",
          text: "text-secondary-light/70",
          border: "border-secondary/[0.12]",
        };
      case "enneagram":
        return {
          bg: "bg-purple-500/[0.06]",
          text: "text-purple-300/70",
          border: "border-purple-500/[0.12]",
        };
      case "creativity":
        return {
          bg: "bg-rose-500/[0.06]",
          text: "text-rose-300/70",
          border: "border-rose-500/[0.12]",
        };
      case "perspective":
        return {
          bg: "bg-teal-500/[0.06]",
          text: "text-teal-300/70",
          border: "border-teal-500/[0.12]",
        };
      default:
        return {
          bg: "bg-white/[0.04]",
          text: "text-text/50",
          border: "border-white/[0.08]",
        };
    }
  }

  const catColor = getCategoryColor(question.category);

  // ── Completion Screen ─────────────────────────────────────────────
  if (showCompletion) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-12">
        <div className="w-full max-w-lg text-center">
          <MotionReveal>
            <div className="mb-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-6">
                <svg
                  className="w-8 h-8 text-primary"
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
              </div>
              <h1 className="font-display text-display-md font-light mb-3">
                Assessment <span className="text-gradient-gold">Complete</span>
              </h1>
              <hr className="rule-gold my-5 max-w-[80px] mx-auto" />
              <p className="text-text/40 font-body leading-relaxed max-w-sm mx-auto">
                You&apos;ve answered all {totalQuestions} questions. Ready to
                generate your personalized Alchymine report?
              </p>
            </div>
          </MotionReveal>

          <MotionReveal delay={0.2}>
            <div className="space-y-3">
              <Button
                onClick={() => handleSubmit(responses)}
                loading={submitting}
                size="lg"
                className="w-full"
              >
                Generate My Report
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
              <button
                onClick={() => setShowCompletion(false)}
                disabled={submitting}
                className="text-sm font-body text-text/30 hover:text-text/60 transition-colors"
              >
                Review answers
              </button>
            </div>
          </MotionReveal>

          {error && (
            <MotionReveal y={8}>
              <div className="mt-6 p-4 rounded-xl card-surface border-primary-dark/20 text-primary-dark text-sm font-body">
                {error}
              </div>
            </MotionReveal>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-12">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <MotionReveal y={10}>
          <div className="mb-8">
            <ProgressBar
              value={progress}
              label={`Question ${currentIndex + 1} of ${totalQuestions}`}
              showPercentage
            />
          </div>
        </MotionReveal>

        {/* Question Card */}
        <div
          key={question.id}
          className="card-surface-elevated p-6 sm:p-8 mb-6 animate-fade-in"
        >
          {/* Category tag */}
          <div className="mb-5">
            <span
              className={`inline-flex items-center text-[0.65rem] font-body font-medium uppercase tracking-[0.15em] ${catColor.text} ${catColor.bg} ${catColor.border} border px-3 py-1.5 rounded-full`}
            >
              {getCategoryLabel(question.category)}
            </span>
          </div>

          {/* Question text */}
          <h2 className="font-display text-xl sm:text-2xl font-medium mb-8 leading-relaxed text-text">
            {question.text}
          </h2>

          {/* Likert scale */}
          <div
            className="space-y-2.5"
            role="radiogroup"
            aria-label="Your response"
          >
            {LIKERT_LABELS.map((label, idx) => {
              const value = idx + 1;
              const isSelected = responses[question.id] === value;
              return (
                <button
                  key={value}
                  onClick={() => handleAnswer(value)}
                  disabled={submitting}
                  role="radio"
                  aria-checked={isSelected}
                  className={`w-full flex items-center gap-4 px-4 sm:px-5 py-3.5 rounded-xl border text-left text-sm font-body transition-all duration-300 touch-target ${
                    isSelected
                      ? "border-primary/40 bg-primary/[0.08] text-text glow-gold"
                      : "border-white/[0.06] bg-white/[0.02] text-text/60 hover:border-white/[0.12] hover:bg-white/[0.04]"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div
                    className={`w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                      isSelected
                        ? "border-primary bg-primary text-bg"
                        : "border-white/[0.15]"
                    }`}
                  >
                    {isSelected && (
                      <svg
                        className="w-3 h-3"
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
                  <span className="font-medium">{label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={goBack}
            disabled={currentIndex === 0 || submitting}
            className="flex items-center gap-1.5 text-sm font-body text-text/30 hover:text-text/60 transition-colors duration-300 disabled:opacity-30 disabled:cursor-not-allowed touch-target"
          >
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
              <path d="m15 18-6-6 6-6" />
            </svg>
            Previous
          </button>

          {allAnswered && (
            <Button onClick={() => setShowCompletion(true)} size="md">
              Complete Assessment
            </Button>
          )}
        </div>

        {/* Error message */}
        {error && (
          <MotionReveal y={8}>
            <div className="mt-4 p-4 rounded-xl card-surface border-primary-dark/20 text-primary-dark text-sm font-body">
              {error}
            </div>
          </MotionReveal>
        )}
      </div>
    </div>
  );
}
