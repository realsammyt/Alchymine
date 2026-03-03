"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ALL_QUESTIONS, LIKERT_LABELS, TOTAL_QUESTIONS } from "@/lib/questions";
import { createReport, IntakePayload } from "@/lib/api";
import Button from "@/components/shared/Button";
import ProgressBar from "@/components/shared/ProgressBar";

export default function AssessmentPage() {
  const router = useRouter();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direction, setDirection] = useState<"next" | "prev">("next");

  // Verify intake data exists
  useEffect(() => {
    const intake = sessionStorage.getItem("alchymine_intake");
    if (!intake) {
      router.replace("/discover/intake");
    }
  }, [router]);

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
          intention: intakeData.intention,
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

  // Category label for the current section
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

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="mb-8">
          <ProgressBar
            value={progress}
            label={`Question ${currentIndex + 1} of ${TOTAL_QUESTIONS}`}
            showPercentage
          />
        </div>

        {/* Question Card */}
        <div
          key={question.id}
          className={`card-surface p-8 mb-6 animate-fade-in`}
        >
          {/* Category tag */}
          <div className="mb-4">
            <span className="text-xs font-medium uppercase tracking-wider text-primary/60 bg-primary/10 px-3 py-1 rounded-full">
              {getCategoryLabel(question.category)}
            </span>
          </div>

          {/* Question text */}
          <h2 className="text-xl sm:text-2xl font-semibold mb-8 leading-relaxed">
            {question.text}
          </h2>

          {/* Likert scale */}
          <div className="space-y-3">
            {LIKERT_LABELS.map((label, idx) => {
              const value = idx + 1;
              const isSelected = responses[question.id] === value;
              return (
                <button
                  key={value}
                  onClick={() => handleAnswer(value)}
                  disabled={submitting}
                  className={`w-full flex items-center gap-4 px-5 py-3.5 rounded-xl border text-left transition-all duration-200 ${
                    isSelected
                      ? "border-primary/50 bg-primary/15 text-text"
                      : "border-white/10 bg-surface/50 text-text/70 hover:border-white/20 hover:bg-surface/80"
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div
                    className={`w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                      isSelected
                        ? "border-primary bg-primary text-bg"
                        : "border-white/20"
                    }`}
                  >
                    {isSelected && (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <span className="text-sm font-medium">{label}</span>
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
            className="flex items-center gap-1 text-sm text-text/40 hover:text-text/70 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m15 18-6-6 6-6" />
            </svg>
            Previous
          </button>

          {/* Show submit button if all questions are answered but user is reviewing */}
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
          <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
