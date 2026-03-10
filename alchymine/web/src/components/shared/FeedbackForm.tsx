"use client";

import { useState } from "react";

const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "bug", label: "Bug Report" },
  { value: "feature", label: "Feature Request" },
  { value: "praise", label: "Praise" },
  { value: "other", label: "Other" },
];

interface FeedbackFormProps {
  isOpen: boolean;
  onClose: () => void;
  pageUrl?: string;
}

export default function FeedbackForm({
  isOpen,
  onClose,
  pageUrl,
}: FeedbackFormProps) {
  const [category, setCategory] = useState("general");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { submitFeedback } = await import("@/lib/api");
      await submitFeedback({
        category,
        message,
        email: email || undefined,
        page_url: pageUrl,
      });
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setSubmitted(false);
    setMessage("");
    setEmail("");
    setCategory("general");
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-surface border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {submitted ? (
          <div className="text-center py-8">
            <p className="text-2xl mb-3">Thank you</p>
            <p className="text-text/60 font-body">
              Your feedback helps improve Alchymine for everyone.
            </p>
            <button
              onClick={handleClose}
              className="mt-6 px-6 py-2 bg-primary/10 text-primary rounded-lg text-sm hover:bg-primary/20 transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display text-lg text-text">Share Feedback</h2>
              <button
                onClick={handleClose}
                className="text-text/40 hover:text-text/80 transition-colors"
                aria-label="Close feedback form"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Message
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  required
                  minLength={10}
                  maxLength={2000}
                  placeholder="Tell us what's on your mind..."
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder-text/30 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Email (optional)
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="reply@example.com"
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder-text/30 focus:outline-none focus:border-primary/50"
                />
              </div>

              {error && (
                <p className="text-red-400 text-sm font-body">{error}</p>
              )}

              <button
                type="submit"
                disabled={submitting || message.length < 10}
                className="w-full py-2.5 bg-primary text-bg rounded-lg text-sm font-body font-medium hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? "Sending..." : "Send Feedback"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
