"use client";

/**
 * SystemCoachBanner -- contextual coaching prompt banner rendered on
 * each system explore page (healing, wealth, creative, perspective,
 * intelligence).
 *
 * Shows 2-3 tailored prompt suggestions based on the current system.
 * Clicking a suggestion navigates to `/chat` with the prompt pre-filled
 * as a query parameter so the ChatPanel can pick it up on mount.
 *
 * Sprint 5, Task 5.1 (#165).
 */

import Link from "next/link";

import type { SystemKey } from "@/hooks/usePageContext";
import { getStarterPrompts } from "@/lib/starterPrompts";

interface Props {
  /** The active system key for this page. */
  systemKey: SystemKey;
}

const SYSTEM_LABELS: Record<SystemKey, string> = {
  intelligence: "Personal Intelligence",
  healing: "Ethical Healing",
  wealth: "Generational Wealth",
  creative: "Creative Development",
  perspective: "Perspective Enhancement",
};

const ACCENT_CLASSES: Record<SystemKey, { border: string; bg: string; text: string }> = {
  intelligence: {
    border: "border-primary/20",
    bg: "bg-primary/5",
    text: "text-primary",
  },
  healing: {
    border: "border-accent/20",
    bg: "bg-accent/5",
    text: "text-accent",
  },
  wealth: {
    border: "border-primary/20",
    bg: "bg-primary/5",
    text: "text-primary",
  },
  creative: {
    border: "border-secondary/20",
    bg: "bg-secondary/5",
    text: "text-secondary",
  },
  perspective: {
    border: "border-accent/20",
    bg: "bg-accent/5",
    text: "text-accent",
  },
};

export default function SystemCoachBanner({ systemKey }: Props) {
  const prompts = getStarterPrompts(systemKey).slice(0, 3);
  const label = SYSTEM_LABELS[systemKey];
  const accent = ACCENT_CLASSES[systemKey];

  if (prompts.length === 0) return null;

  return (
    <aside
      aria-label={`${label} coach suggestions`}
      data-testid="system-coach-banner"
      className={`rounded-xl border ${accent.border} ${accent.bg} p-4 sm:p-5`}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className={`font-display text-sm font-medium ${accent.text}`}>
            Talk to your {label} coach
          </h3>
          <p className="font-body text-xs text-text/50 mt-0.5">
            Ask a question to get personalised guidance.
          </p>
        </div>
        <Link
          href={`/chat?system=${systemKey}`}
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-body ${accent.text} border ${accent.border} transition-colors hover:bg-white/5`}
        >
          Open chat
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        </Link>
      </div>

      {/* Prompt suggestion chips */}
      <div className="mt-3 flex flex-wrap gap-2">
        {prompts.map((prompt) => (
          <Link
            key={prompt.label}
            href={`/chat?system=${systemKey}&prompt=${encodeURIComponent(prompt.message)}`}
            className={`rounded-full border ${accent.border} bg-white/5 px-3 py-1.5 text-xs font-body ${accent.text}/80 transition-colors hover:bg-white/10`}
          >
            {prompt.label}
          </Link>
        ))}
      </div>
    </aside>
  );
}
