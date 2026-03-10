"use client";

import Link from "next/link";

interface JournalCTAProps {
  templateId: string;
  /** Optional custom heading text */
  heading?: string;
  /** Optional custom description text */
  description?: string;
}

export default function JournalCTA({
  templateId,
  heading = "Reflect on this in your journal",
  description = "Capture your thoughts while they're fresh.",
}: JournalCTAProps) {
  return (
    <div className="card-surface border border-primary/[0.12] px-6 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h3 className="font-display text-base font-medium text-text mb-1">
          {heading}
        </h3>
        <p className="text-sm font-body text-text/35">{description}</p>
      </div>
      <Link
        href={`/journal?template=${templateId}`}
        className="touch-target inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98] self-start sm:self-auto whitespace-nowrap"
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
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
        Start Journal Entry
      </Link>
    </div>
  );
}
