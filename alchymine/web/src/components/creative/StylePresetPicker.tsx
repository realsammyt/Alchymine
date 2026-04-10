"use client";

import { useEffect, useRef, useState } from "react";
import { listStylePresets, StylePreset } from "@/lib/artApi";

export interface CreativeProfile {
  /** Canonical style label from the creative engine, e.g. "Architect". */
  creative_orientation?: string | null;
  /** Optional dominant style name returned by `getCreativeStyle`. */
  creative_style?: string | null;
}

interface StylePresetPickerProps {
  selected: string | null;
  onSelect: (presetId: string) => void;
  creativeProfile?: CreativeProfile | null;
}

/**
 * Fallback preset catalogue used when the `/art/presets` call fails or
 * hasn't resolved yet. Source of truth is
 * `alchymine/llm/art_prompts.py::STYLE_PRESETS`. Keep the ids in sync
 * with that dict — the picker passes the id straight through to the
 * generation endpoint which validates against it.
 */
const FALLBACK_PRESETS: StylePreset[] = [
  {
    id: "mystical",
    name: "Mystical",
    description: "Sacred geometry, indigo and gold",
  },
  {
    id: "modern",
    name: "Modern",
    description: "Clean, editorial, muted gradients",
  },
  {
    id: "organic",
    name: "Organic",
    description: "Botanical watercolour, earth tones",
  },
  {
    id: "celestial",
    name: "Celestial",
    description: "Starfields, nebulae, violet and silver",
  },
  {
    id: "grounded",
    name: "Grounded",
    description: "Stone, wood, terracotta, golden-hour",
  },
];

/**
 * Short gradient swatch classes per preset. These are purely visual
 * and do not need to match the server-side style suffix — they're
 * derived from the preset's mood for the thumbnail card.
 */
const PRESET_SWATCHES: Record<string, string> = {
  mystical: "from-primary/50 via-secondary/40 to-accent/30",
  modern: "from-white/20 via-white/10 to-surface",
  organic: "from-emerald-700/50 via-amber-700/30 to-lime-900/40",
  celestial: "from-indigo-900/60 via-violet-700/40 to-slate-200/20",
  grounded: "from-amber-800/50 via-stone-700/40 to-orange-900/40",
};

/**
 * Heuristic mapping from a user's creative orientation to the most
 * fitting preset. Keyed on lowercased substrings of the style label
 * so partial matches still fire. Add new rows here as the creative
 * engine grows more orientations.
 */
const ORIENTATION_PRESET_HINTS: Array<[string, string]> = [
  ["architect", "modern"],
  ["explorer", "celestial"],
  ["connector", "organic"],
  ["alchemist", "mystical"],
];

function suggestPresetForProfile(
  profile: CreativeProfile | null | undefined,
): string | null {
  if (!profile) return null;
  const label = (
    profile.creative_orientation ??
    profile.creative_style ??
    ""
  ).toLowerCase();
  if (!label) return null;
  for (const [needle, presetId] of ORIENTATION_PRESET_HINTS) {
    if (label.includes(needle)) return presetId;
  }
  return null;
}

/**
 * Card grid of style presets for the Creative Studio.
 *
 * The picker is a roving-tabindex ARIA radio group: arrow keys move
 * focus between cards, Enter/Space confirm the selection, and the
 * selected card carries `aria-pressed="true"`.
 */
export default function StylePresetPicker({
  selected,
  onSelect,
  creativeProfile,
}: StylePresetPickerProps) {
  const [presets, setPresets] = useState<StylePreset[]>(FALLBACK_PRESETS);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Load the live catalogue from the API; fall back silently on error.
  useEffect(() => {
    let cancelled = false;
    void listStylePresets()
      .then((next) => {
        if (!cancelled && next.length > 0) setPresets(next);
      })
      .catch(() => {
        /* keep FALLBACK_PRESETS — matches the server source of truth */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const suggestedPresetId = suggestPresetForProfile(creativeProfile);

  function handleKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    const lastIndex = presets.length - 1;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      const nextIndex = index === lastIndex ? 0 : index + 1;
      buttonRefs.current[nextIndex]?.focus();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      const prevIndex = index === 0 ? lastIndex : index - 1;
      buttonRefs.current[prevIndex]?.focus();
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(presets[index].id);
    } else if (event.key === "Home") {
      event.preventDefault();
      buttonRefs.current[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      buttonRefs.current[lastIndex]?.focus();
    }
  }

  return (
    <div
      role="group"
      aria-label="Choose a style preset"
      className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3"
    >
      {presets.map((preset, index) => {
        const isSelected = selected === preset.id;
        const isSuggested = suggestedPresetId === preset.id;
        const swatch =
          PRESET_SWATCHES[preset.id] ??
          "from-primary/40 via-secondary/30 to-accent/20";
        return (
          <button
            key={preset.id}
            ref={(el) => {
              buttonRefs.current[index] = el;
            }}
            type="button"
            aria-pressed={isSelected}
            aria-label={`${preset.name} — ${preset.description}${
              isSuggested ? ". Matched to your profile." : ""
            }`}
            tabIndex={
              isSelected || (!selected && index === 0) || isSuggested ? 0 : -1
            }
            onClick={() => onSelect(preset.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={`relative rounded-xl p-3 text-left border transition-all focus:outline-none focus:ring-2 focus:ring-primary/60 ${
              isSelected
                ? "border-primary bg-primary/10 shadow-[0_0_0_1px_rgba(123,45,142,0.5)]"
                : "border-white/[0.06] bg-surface hover:border-white/20"
            }`}
            data-testid={`style-preset-${preset.id}`}
          >
            <div
              className={`h-12 rounded-lg bg-gradient-to-br ${swatch} mb-2`}
              aria-hidden="true"
            />
            <p className="font-display text-sm font-medium text-text">
              {preset.name}
            </p>
            <p className="font-body text-xs text-text/50 mt-0.5 leading-snug">
              {preset.description}
            </p>
            {isSuggested && (
              <span
                className="mt-2 inline-block px-2 py-0.5 rounded-full bg-secondary/20 text-secondary text-[10px] font-body uppercase tracking-wider"
                data-testid={`style-preset-${preset.id}-badge`}
              >
                Matched to your profile
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
