"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ALL_QUESTIONS, LIKERT_LABELS, TOTAL_QUESTIONS } from "@/lib/questions";
import { createReport, getProfile, IntakePayload } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import Button from "@/components/shared/Button";
import ProgressBar from "@/components/shared/ProgressBar";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function AssessmentPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direction, setDirection] = useState<"next" | "prev">("next");

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
      .catch(() => {
        router.replace("/discover/intake");
      });
  }, [router, user?.id]);

  const question = ALL_QUESTIONS[currentIndex];
  const progress = (Object.keys(responses).length / TOTAL_QUESTIONS) * 100;
  const isLastQuestion = currentIndex === TOTAL_QUESTIONS - 1;
  const allAnswered = Object.keys(responses).length === TOTAL_QUESTIONS;

  const handleSubmit = useCallback(
    async (finalResponses: Record<string, number>) => {
      setSubmitting(true);
      setError(null);

      try {
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
          assessment_responses: finalResponses,
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
    [router],
  );

  const handleAnswer = useCallback(
    async (value: number) => {
      const newResponses = { ...responses, [question.id]: value };
      setResponses(newResponses);

      if (
        isLastQuestion &&
        Object.keys(newResponses).length === TOTAL_QUESTIONS
      ) {
        await handleSubmit(newResponses);
      } else if (!isLastQuestion) {
        setDirection("next");
        setTimeout(() => {
          setCurrentIndex((prev) => prev + 1);
        }, 200);
      }
    },
    [responses, question, isLastQuestion, handleSubmit],
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
      default:
        return {
          bg: "bg-white/[0.04]",
          text: "text-text/50",
          border: "border-white/[0.08]",
        };
    }
  }

  const catColor = getCategoryColor(question.category);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-12">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <MotionReveal y={10}>
          <div className="mb-8">
            <ProgressBar
              value={progress}
              label={`Question ${currentIndex + 1} of ${TOTAL_QUESTIONS}`}
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
            <Button
              onClick={() => handleSubmit(responses)}
              loading={submitting}
              size="md"
            >
              Submit Assessment
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
