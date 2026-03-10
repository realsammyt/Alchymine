"use client";

import { useState } from "react";
import FeedbackForm from "./FeedbackForm";

export default function FeedbackButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 bg-surface border border-white/10 rounded-full shadow-lg text-sm font-body text-text/70 hover:text-text hover:border-white/20 transition-all hover:shadow-xl"
        aria-label="Open feedback form"
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
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Feedback
      </button>

      <FeedbackForm
        isOpen={open}
        onClose={() => setOpen(false)}
        pageUrl={
          typeof window !== "undefined" ? window.location.href : undefined
        }
      />
    </>
  );
}
