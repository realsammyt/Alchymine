"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { useFocusOnEnter } from "@/hooks/useFocusOnEnter";

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
 * The readings the user can give, or none at all.
 *
 * Worded as capacity rather than as performance: "a bit more" means more
 * of the thing the practice builds, not a better score. Zero is "about
 * the same", which is an ordinary and common answer, so it sits in the
 * middle rather than reading as a failure at one end.
 *
 * "Rather not say" exists because the copy calls the question optional
 * and a radio group cannot otherwise be returned to no-answer once
 * anything is picked. It submits the same `null` as never touching the
 * group at all.
 */
const CAPACITY_CHOICES: { key: string; value: number | null; label: string }[] = [
  { key: "-2", value: -2, label: "A lot harder" },
  { key: "-1", value: -1, label: "A bit harder" },
  { key: "0", value: 0, label: "About the same" },
  { key: "1", value: 1, label: "A bit more" },
  { key: "2", value: 2, label: "A lot more" },
  // Keyed separately from its value. "Rather not say" submits null, and
  // so does never touching the group, but the two are different states
  // on screen: keying this one off `null` would draw it pre-selected
  // before the user has answered anything.
  { key: "declined", value: null, label: "Rather not say" },
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
  const noteId = useId();
  const groupName = useId();
  // "" means untouched. See CAPACITY_CHOICES for why this is not just
  // the numeric value.
  const [selectedKey, setSelectedKey] = useState("");
  const [note, setNote] = useState("");

  const saved = state === "saved";
  const savedRef = useFocusOnEnter<HTMLParagraphElement>(saved);

  if (saved) {
    return (
      <div className="mt-1 border-t border-white/[0.06] pt-4">
        <p
          ref={savedRef}
          role="status"
          aria-live="polite"
          tabIndex={-1}
          className="text-sm font-body text-text/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded"
        >
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

      {/* A fieldset with a legend is already a named group. No explicit
          role is needed, and adding one only risks fighting the native
          semantics. */}
      <fieldset className="border-0 p-0 m-0">
        <legend className="font-body text-xs text-text/60 mb-2">
          Compared to before, how much of that capacity do you have right now?
          Optional.
        </legend>
        <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
          {CAPACITY_CHOICES.map((choice) => (
            <label
              key={choice.key}
              className="touch-target inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 text-sm font-body text-text/60 cursor-pointer transition-colors duration-200 hover:border-white/20 has-[:checked]:border-primary/40 has-[:checked]:text-primary"
            >
              <input
                type="radio"
                name={`capacity-${groupName}`}
                value={choice.key}
                checked={selectedKey === choice.key}
                onChange={() => setSelectedKey(choice.key)}
                className="accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
              />
              {choice.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor={noteId} className="font-body text-xs text-text/60">
          Anything else worth writing down? Optional.
        </label>
        <textarea
          id={noteId}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={2}
          maxLength={5000}
          className="w-full rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2 text-sm font-body text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:border-primary/30"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* Stable label plus aria-busy, and aria-disabled rather than
            disabled, so the in-flight window neither renames the control
            nor blurs the user off it. */}
        <button
          type="button"
          onClick={() => {
            if (state === "saving") return;
            const chosen = CAPACITY_CHOICES.find((c) => c.key === selectedKey);
            onSubmit({
              capacityDelta: chosen?.value ?? null,
              note: note.trim(),
            });
          }}
          aria-disabled={state === "saving"}
          aria-busy={state === "saving"}
          className={`touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
            state === "saving"
              ? "opacity-50 cursor-not-allowed"
              : "hover:bg-primary/25"
          }`}
        >
          Save
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="touch-target px-4 py-2 rounded-lg text-sm font-body text-text/60 border border-white/10 transition-colors duration-200 hover:text-text/80 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
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

      <p role="status" aria-live="polite" className="text-xs font-body text-text/60">
        {error}
      </p>
    </div>
  );
}
