"use client";

import Link from "next/link";

/**
 * What a brand-new user sees here.
 *
 * The page is drawn entirely from the practice log, so before there is
 * a log there is nothing honest to draw. That makes this the first
 * thing most people see on this route, and it has one job: say what
 * the page will become, and point at the one action that starts it.
 *
 * No placeholder chart and no sample data. A fake series would teach
 * somebody to read a shape that is not theirs.
 */
export default function JourneyEmpty() {
  return (
    <section
      aria-labelledby="journey-empty-heading"
      className="card-surface px-5 py-8 sm:px-8 sm:py-10"
    >
      <h2
        id="journey-empty-heading"
        className="font-display text-lg font-medium text-text mb-2"
      >
        Your journey starts with one practice
      </h2>
      <p className="font-body text-sm text-text/70 leading-relaxed max-w-prose mb-6">
        This page is drawn from what you actually do, so it stays empty until
        there is something to draw. Log one practice and the first day appears
        here, alongside whatever you make of it when you close the loop.
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <Link
          href="/practice"
          className="touch-target inline-flex items-center px-4 py-2 rounded-lg font-body text-sm font-medium text-bg bg-primary transition-colors duration-200 hover:bg-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Go to today&apos;s practice
        </Link>
        <Link
          href="/practice/library"
          className="touch-target inline-flex items-center font-body text-sm text-primary underline underline-offset-4 transition-colors duration-200 hover:text-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
        >
          Browse the library
        </Link>
      </div>
    </section>
  );
}
