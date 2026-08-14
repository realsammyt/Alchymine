"use client";

import { useId, useState } from "react";

interface SelfCheckPromptProps {
  /** The practice's own reflective question. Always ends in a question mark. */
  question: string;
  onSave: (response: string) => void | Promise<void>;
  onDismiss: () => void;
  saving?: boolean;
  error?: string | null;
}

/**
 * The self-check.
 *
 * A question and a box, and nothing else. There is no rating, no scale
 * and no yes/no: the answer is never read by the recommender and never
 * stored as a number, because scoring a reflective question turns it
 * into a diagnosis. The copy says so plainly rather than leaving the
 * user to guess whether this is being marked.
 */
export default function SelfCheckPrompt({
  question,
  onSave,
  onDismiss,
  saving = false,
  error = null,
}: SelfCheckPromptProps) {
  const fieldId = useId();
  const [response, setResponse] = useState("");
  const trimmed = response.trim();

  return (
    <div className="mt-1 border-t border-white/[0.06] pt-4 flex flex-col gap-3">
      <label
        htmlFor={fieldId}
        className="font-body text-sm text-text/70 leading-relaxed"
      >
        {question}
      </label>
      <p className="text-xs font-body text-text/35">
        Optional, and nobody scores this. It&apos;s yours.
      </p>
      <textarea
        id={fieldId}
        value={response}
        onChange={(event) => setResponse(event.target.value)}
        rows={3}
        maxLength={5000}
        className="w-full rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2 text-sm font-body text-text placeholder:text-text/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:border-primary/30"
        placeholder="Whatever you noticed."
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            if (trimmed) onSave(trimmed);
          }}
          disabled={saving || trimmed.length === 0}
          className="touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 hover:bg-primary/25 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          {saving ? "Saving..." : "Save this"}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="touch-target px-4 py-2 rounded-lg text-sm font-body text-text/50 border border-white/10 transition-colors duration-200 hover:text-text/70 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Skip this
        </button>
      </div>
      <p role="status" aria-live="polite" className="text-xs font-body text-text/50">
        {error}
      </p>
    </div>
  );
}
