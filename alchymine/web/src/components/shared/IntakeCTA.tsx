"use client";

import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { useIntake } from "@/lib/useApi";

/**
 * Prominent banner prompting users to complete their intake assessment.
 * Self-contained: checks auth + intake state internally.
 * Renders nothing if intake is already complete or still loading.
 */
export default function IntakeCTA() {
  const { user } = useAuth();
  const { data: intake, loading } = useIntake(user?.id ?? null);

  // Don't render while loading or if intake is already done
  if (loading || intake) return null;

  return (
    <Link
      href="/discover/intake"
      className="group flex items-center gap-4 card-surface border border-primary/20 rounded-xl px-5 py-4 mb-8 no-underline transition-all duration-300 hover:border-primary/40 hover:bg-primary/[0.04]"
    >
      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
        <svg
          className="w-5 h-5 text-primary"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-display text-sm font-medium text-text">
          Complete Your Intake Assessment
        </p>
        <p className="font-body text-xs text-text/40 mt-0.5">
          Tell us about yourself so we can personalize your journey across all
          five systems.
        </p>
      </div>
      <svg
        className="w-5 h-5 text-primary/50 flex-shrink-0 group-hover:translate-x-1 transition-transform"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </Link>
  );
}
