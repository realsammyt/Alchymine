"use client";

import Link from "next/link";
import { useId, useState } from "react";

/** The lifecycle of one integration write, from the user's side. */
export type IntegrationState = "idle" | "saving" | "saved" | "error";

interface IntegrationPromptProps {
  practiceTitle: string;
  onSubmit: (input: {
    capacityDelta: number | null;
    note: string;
  }) => void | Promise<void>;
  onDismiss: () => void;
  state: IntegrationState;
  error?: string | null;
}

/**
 * The five readings the user can give, or none at all.
 *
 * Worded as capacity rather than as performance: "a bit more" means more
 * of the thing the practice builds, not a better score. Zero is "about
 * the same", which is an ordinary and common answer, so it sits in the
 * middle rather than reading as a failure at one end.
 */
const CAPACITY_CHOICES: { value: number; label: string }[] = [
  { value: -2, label: "A lot harder" },
  { value: -1, label: "A bit harder" },
  { value: 0, label: "About the same" },
  { value: 1, label: "A bit more" },
  { value: 2, label: "A lot more" },
];

/**
 * The integration step: what the practice did, in the user's own read.
 *
 * Everything is optional. Saving with nothing chosen and nothing written
 * is a valid loop, because the practice happened and that is the fact
 * worth recording. The journal link goes to the existing template rather
 * than growing a second place to write things down.
 */
export default function IntegrationPrompt({
  practiceTitle,
  onSubmit,
  onDismiss,
  state,
  error = null,
}: IntegrationPromptProps) {
  const groupId = useId();
  const noteId = useId();
  const [capacityDelta, setCapacityDelta] = useState<number | null>(null);
  const [note, setNote] = useState("");

  if (state === "saved") {
    return (
      <div className="mt-1 border-t border-white/[0.06] pt-4">
        <p className="text-sm font-body text-text/50">
          Logged. It&apos;ll show up on your dashboard.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-1 border-t border-white/[0.06] pt-4 flex flex-col gap-3">
      <p className="font-body text-sm text-text/70">
        You just did {practiceTitle}. Worth a moment?
      </p>

      <fieldset className="border-0 p-0 m-0" role="radiogroup" aria-labelledby={groupId}>
        <legend id={groupId} className="font-body text-xs text-text/40 mb-2">
          Compared to before, how much of that capacity do you have right now?
          Optional.
        </legend>
        <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
          {CAPACITY_CHOICES.map((choice) => (
            <label
              key={choice.value}
              className="touch-target inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 text-sm font-body text-text/60 cursor-pointer transition-colors duration-200 hover:border-white/20 has-[:checked]:border-primary/40 has-[:checked]:text-primary"
            >
              <input
                type="radio"
                name={`capacity-${groupId}`}
                value={choice.value}
                checked={capacityDelta === choice.value}
                onChange={() => setCapacityDelta(choice.value)}
                className="accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
              />
              {choice.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={noteId} className="font-body text-xs text-text/40">
          Anything else worth writing down? Optional.
        </label>
        <textarea
          id={noteId}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={2}
          maxLength={5000}
          className="w-full rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2 text-sm font-body text-text placeholder:text-text/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:border-primary/30"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onSubmit({ capacityDelta, note: note.trim() })}
          disabled={state === "saving"}
          className="touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 hover:bg-primary/25 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          {state === "saving" ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="touch-target px-4 py-2 rounded-lg text-sm font-body text-text/50 border border-white/10 transition-colors duration-200 hover:text-text/70 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Not now
        </button>
        <Link
          href="/journal?template=practice-integration"
          className="touch-target inline-flex items-center px-2 py-2 text-sm font-body text-primary underline underline-offset-4 transition-colors duration-200 hover:text-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
        >
          Write more in your journal
        </Link>
      </div>

      <p role="status" aria-live="polite" className="text-xs font-body text-text/50">
        {error}
      </p>
    </div>
  );
}
