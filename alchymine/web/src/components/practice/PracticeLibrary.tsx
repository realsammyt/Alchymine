"use client";

import { useId, useMemo, useState } from "react";
import PackAttribution from "./PackAttribution";
import { purposeLabel } from "./PracticeCard";
import type { PackResponse, PracticeResponse } from "@/lib/api";

/** The five capacities, in the fixed order the engine uses. */
const PURPOSES = [
  "self-knowledge",
  "steadiness",
  "stewardship",
  "expression",
  "reframing",
] as const;

interface PracticeLibraryProps {
  packs: PackResponse[];
  practices: PracticeResponse[];
}

interface PracticeRowProps {
  entry: PracticeResponse;
}

function PracticeRow({ entry }: PracticeRowProps) {
  const bodyId = useId();
  const [open, setOpen] = useState(false);
  const practice = entry.practice;

  return (
    <li className="border-b border-white/[0.05] last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((current) => !current)}
        className="touch-target w-full text-left py-3 px-1 flex flex-wrap items-baseline gap-x-3 gap-y-1 transition-colors duration-200 hover:bg-white/[0.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded"
      >
        <span className="font-display text-sm font-medium text-text">
          {practice.title}
        </span>
        <span className="text-[11px] font-body px-2 py-0.5 rounded-full bg-white/[0.06] text-text/50">
          {practice.duration_minutes} min
        </span>
        {practice.purposes.map((purpose) => (
          <span
            key={purpose}
            className="text-[11px] font-body px-2 py-0.5 rounded-full bg-primary/10 text-primary"
          >
            {purposeLabel(purpose)}
          </span>
        ))}
      </button>
      {/* The `hidden` attribute rather than a display class, so collapsed
          content is out of the accessibility tree and not merely off the
          screen. The element carrying `hidden` deliberately has no
          className: a Tailwind display utility such as `flex` has the
          same specificity as preflight's `[hidden] { display: none }` and
          comes later in the cascade, so putting one here would leave the
          body permanently visible in a browser while still reading as
          hidden in jsdom. The layout classes live on the inner div. */}
      <div id={bodyId} hidden={!open}>
        <div className="pb-4 px-1 flex flex-col gap-2">
          <p className="text-sm font-body text-text/60 leading-relaxed">
            {practice.summary}
          </p>
          <p className="text-sm font-body text-text/70 leading-relaxed whitespace-pre-line">
            {practice.description}
          </p>
          <p className="text-sm font-body text-text/50 leading-relaxed">
            {practice.expected_shift}
          </p>
          {practice.contraindications.length > 0 && (
            <div>
              <h4 className="font-body text-xs text-text/40 mb-1">
                Before you try this
              </h4>
              <ul className="list-disc pl-5 text-xs font-body text-text/45 space-y-1">
                {practice.contraindications.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

/**
 * The library: every practice in every mounted pack, grouped by pack.
 *
 * Grouped rather than flattened because license and attribution attach
 * to the pack, and a flat list would either repeat them on every row or
 * lose them.
 */
export default function PracticeLibrary({
  packs,
  practices,
}: PracticeLibraryProps) {
  const filterId = useId();
  const [purpose, setPurpose] = useState("");

  const visible = useMemo(
    () =>
      purpose
        ? practices.filter((entry) => entry.practice.purposes.includes(purpose))
        : practices,
    [practices, purpose],
  );

  if (packs.length === 0) {
    return (
      <div className="card-surface p-8 text-center">
        <p className="text-sm font-body text-text/50 max-w-md mx-auto">
          No practice packs are mounted right now.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={filterId} className="text-sm font-body text-text/50">
          Capacity
        </label>
        <select
          id={filterId}
          value={purpose}
          onChange={(event) => setPurpose(event.target.value)}
          className="touch-target rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2 text-sm font-body text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          <option value="">All five</option>
          {PURPOSES.map((option) => (
            <option key={option} value={option}>
              {purposeLabel(option)}
            </option>
          ))}
        </select>
      </div>

      {visible.length === 0 ? (
        <div className="card-surface p-8 text-center">
          <p className="text-sm font-body text-text/50">
            No practices match that capacity yet.
          </p>
        </div>
      ) : (
        packs.map((pack) => {
          const entries = visible.filter(
            (entry) => entry.pack_id === pack.manifest.pack_id,
          );
          if (entries.length === 0) return null;
          const headingId = `pack-${pack.manifest.pack_id}`;

          return (
            <section
              key={pack.manifest.pack_id}
              aria-labelledby={headingId}
              className="card-surface px-5 py-4 sm:px-6 sm:py-5"
            >
              <h2
                id={headingId}
                className="font-display text-lg font-medium text-text mb-1"
              >
                {pack.manifest.title}
              </h2>
              <p className="text-sm font-body text-text/50 mb-2">
                {pack.manifest.summary}
              </p>
              <PackAttribution manifest={pack.manifest} />
              <ul className="mt-3 list-none p-0">
                {entries.map((entry) => (
                  <PracticeRow
                    key={`${entry.pack_id}/${entry.practice.slug}`}
                    entry={entry}
                  />
                ))}
              </ul>
            </section>
          );
        })
      )}
    </div>
  );
}
