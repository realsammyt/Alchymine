"use client";

import React, { useState, useCallback } from "react";
import Button from "@/components/shared/Button";
import type { SupplementQuestion } from "@/lib/questions";

interface SupplementModalProps {
  title: string;
  description?: string;
  questions: SupplementQuestion[];
  loading?: boolean;
  onSubmit: (responses: Record<string, number | string>) => void;
  onClose: () => void;
}

const LIKERT_OPTIONS = [
  { value: 1, label: "Strongly Disagree" },
  { value: 2, label: "Disagree" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "Agree" },
  { value: 5, label: "Strongly Agree" },
];

export default function SupplementModal({
  title,
  description,
  questions,
  loading = false,
  onSubmit,
  onClose,
}: SupplementModalProps) {
  const [responses, setResponses] = useState<Record<string, number | string>>(
    {},
  );

  const handleLikert = useCallback((id: string, value: number) => {
    setResponses((prev) => ({ ...prev, [id]: value }));
  }, []);

  const handleSelect = useCallback((id: string, value: string) => {
    setResponses((prev) => ({ ...prev, [id]: value }));
  }, []);

  const answeredCount = Object.keys(responses).length;
  const totalCount = questions.length;
  const allAnswered = answeredCount === totalCount;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto mx-4 card-surface-elevated rounded-2xl border border-white/[0.08] shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-surface/95 backdrop-blur-md px-6 pt-5 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-light tracking-tight text-text">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/[0.06] text-text/40 hover:text-text/70 transition-colors"
              aria-label="Close"
            >
              <svg
                className="w-5 h-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          {description && (
            <p className="mt-2 text-sm font-body text-text/40 leading-relaxed">
              {description}
            </p>
          )}
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-dark to-primary rounded-full transition-all duration-500"
                style={{
                  width: `${totalCount > 0 ? (answeredCount / totalCount) * 100 : 0}%`,
                }}
              />
            </div>
            <span className="text-xs font-body text-text/30">
              {answeredCount}/{totalCount}
            </span>
          </div>
        </div>

        {/* Questions */}
        <div className="px-6 py-5 space-y-6">
          {questions.map((q, idx) => (
            <div key={q.id} className="space-y-3">
              <p className="text-sm font-body text-text/70 leading-relaxed">
                <span className="text-text/30 font-display text-xs mr-2">
                  {idx + 1}.
                </span>
                {q.text}
              </p>

              {q.type === "likert" ? (
                <div className="flex gap-1.5">
                  {LIKERT_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleLikert(q.id, opt.value)}
                      className={`flex-1 py-2 px-1 rounded-lg text-xs font-body transition-all duration-200 ${
                        responses[q.id] === opt.value
                          ? "bg-primary/20 border border-primary/40 text-primary font-medium"
                          : "bg-white/[0.03] border border-white/[0.06] text-text/40 hover:bg-white/[0.06] hover:text-text/60"
                      }`}
                      title={opt.label}
                    >
                      {opt.value}
                    </button>
                  ))}
                </div>
              ) : (
                <select
                  value={(responses[q.id] as string) ?? ""}
                  onChange={(e) => handleSelect(q.id, e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/[0.08] text-sm font-body text-text/70 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-colors"
                >
                  <option value="" disabled>
                    Select...
                  </option>
                  {q.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-surface/95 backdrop-blur-md px-6 py-4 border-t border-white/[0.06] flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => onSubmit(responses)}
            disabled={!allAnswered || loading}
            loading={loading}
          >
            Update Profile
          </Button>
        </div>
      </div>
    </div>
  );
}
