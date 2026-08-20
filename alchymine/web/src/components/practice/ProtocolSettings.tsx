"use client";

import { useCallback, useEffect, useId, useState } from "react";
import ApiStateView from "@/components/shared/ApiStateView";
import { useApi } from "@/lib/useApi";
import {
  ApiError,
  getEcologySettings,
  listPracticePacks,
  updateEcologySettings,
  PROTOCOL_SIZES,
  type EcologySettings,
  type EcologySettingsUpdate,
  type PackResponse,
} from "@/lib/api";

/**
 * DRAFT copy, awaiting Tyler's sign-off.
 *
 * The size line is the load-bearing one. A number in a box reads as a
 * promise of that many practices, and the recommender offers fewer when
 * fewer are ready. Saying so here is cheaper than the user finding out
 * on a morning they get three instead of five (#326).
 */
const SIZE_HELP =
  "Up to this many a day. Some days will offer fewer, depending on what's ready for you.";
const PACKS_HELP = "Today's practice is drawn from these.";

/**
 * Shown when the user has cleared every box.
 *
 * The server refuses an empty list too, and that refusal stays the real
 * gate. This exists so the answer arrives while the user is still
 * looking at the boxes rather than after a round trip that was never
 * going to succeed.
 */
const EMPTY_SELECTION = "Pick at least one pack, or go back to all packs.";

/** Shown when a save is worth trying again, which is most of them. */
const SAVE_FAILED = "That didn't save. Have another go in a moment.";

/** Shown once a save lands, and it says what happens next rather than just "done". */
const SAVED = "Saved. Today's practice is being put together again.";

/** Matches the line the library shows when the registry has nothing in it. */
const NO_PACKS = "No practice packs are mounted right now.";

/** Which packs a saved protocol draws from: everything, or a chosen few. */
type PackMode = "all" | "chosen";

/**
 * What to tell the user about a refused save.
 *
 * A 422 from this route is the server declining on purpose, in a
 * sentence written for the reader: the pack is not mounted, the list is
 * empty, the body asked for nothing. Retrying is refused the same way,
 * so the generic line would be both false and useless. Everything else
 * keeps it, because a dropped connection really is worth another go.
 */
function refusedSaveMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 422 && err.message) {
    return err.message;
  }
  return SAVE_FAILED;
}

/** True when two pack selections mean the same thing to the recommender. */
function sameSelection(
  left: string[] | null,
  right: string[] | null,
): boolean {
  if (left === null || right === null) return left === right;
  if (left.length !== right.length) return false;
  const a = [...left].sort();
  const b = [...right].sort();
  return a.every((value, index) => value === b[index]);
}

interface ProtocolSettingsProps {
  /**
   * Called after a save lands, so the page can read today's protocol
   * again. The server clears the stored protocol on any real change, so
   * the next read recomputes; without this the page would keep showing
   * the old one until a reload.
   */
  onSaved?: () => void;
}

/**
 * The two settings that shape every protocol: how many practices a day
 * holds, and which packs they come from.
 *
 * A disclosure rather than a page. These are settings somebody touches
 * twice a year, and the practices are what the page is for, so it opens
 * closed and the reads wait until it is opened at all.
 *
 * Only changed fields travel. An omitted field means "leave it alone"
 * on this route, and sending both every time would clear the stored
 * protocol on a save that changed nothing.
 */
export default function ProtocolSettings({ onSaved }: ProtocolSettingsProps) {
  const panelId = useId();
  const sizeId = useId();
  const sizeHelpId = useId();
  const packsHelpId = useId();
  const noticeId = useId();
  const modeName = useId();

  const [open, setOpen] = useState(false);
  // Latched rather than tracking `open`, so collapsing the panel does
  // not throw away what the user has typed into it and reopening does
  // not spend two more requests.
  const [everOpened, setEverOpened] = useState(false);

  const settings = useApi<EcologySettings>(
    everOpened ? (signal) => getEcologySettings(signal) : null,
    [everOpened],
  );
  const packs = useApi<PackResponse[]>(
    everOpened ? (signal) => listPracticePacks(signal) : null,
    [everOpened],
  );

  // What is stored, as far as this component knows. The form is dirty
  // relative to this, and a save replaces it with the server's answer
  // rather than with what was sent: the server sorts and deduplicates
  // the pack ids, so the response is the canonical version of the
  // choice and anything else would leave the form looking unsaved.
  const [baseline, setBaseline] = useState<EcologySettings | null>(null);
  const [size, setSize] = useState<number>(PROTOCOL_SIZES[0]);
  const [mode, setMode] = useState<PackMode>("all");
  const [chosen, setChosen] = useState<string[]>([]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const applySettings = useCallback((next: EcologySettings) => {
    setBaseline(next);
    setSize(next.protocol_size);
    setMode(next.active_pack_ids ? "chosen" : "all");
    setChosen(next.active_pack_ids ?? []);
  }, []);

  useEffect(() => {
    if (settings.data) applySettings(settings.data);
  }, [settings.data, applySettings]);

  /** Any edit clears the last save's verdict, which no longer describes the form. */
  const resetNotice = useCallback(() => {
    setSaveError(null);
    setSaved(false);
  }, []);

  const readError = settings.error ?? packs.error;
  const ready = baseline !== null && packs.data !== null;
  const loading = open && !ready && readError === null;

  const retryReads = useCallback(() => {
    if (settings.error) settings.refetch();
    if (packs.error) packs.refetch();
  }, [settings, packs]);

  const selection = mode === "all" ? null : chosen;
  const emptySelection = mode === "chosen" && chosen.length === 0;
  const sizeChanged = baseline !== null && size !== baseline.protocol_size;
  const packsChanged =
    baseline !== null && !sameSelection(baseline.active_pack_ids, selection);
  const changed = sizeChanged || packsChanged;
  const canSave = ready && changed && !emptySelection && !saving;

  // One message at a time, in one region that is always in the document:
  // a live region introduced at the same moment as its text is
  // unreliably announced. The refusal comes first because it is the
  // newest thing that happened, then the reason the save is inert, then
  // the last save's verdict.
  let notice = "";
  if (saveError) notice = saveError;
  else if (emptySelection) notice = EMPTY_SELECTION;
  else if (saved) notice = SAVED;

  const toggleChosen = useCallback(
    (packId: string) => {
      resetNotice();
      setChosen((current) =>
        current.includes(packId)
          ? current.filter((entry) => entry !== packId)
          : [...current, packId],
      );
    },
    [resetNotice],
  );

  const handleSave = useCallback(async () => {
    if (!canSave || baseline === null) return;

    const patch: EcologySettingsUpdate = {};
    if (sizeChanged) patch.protocol_size = size;
    if (packsChanged) patch.active_pack_ids = selection;

    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      applySettings(await updateEcologySettings(patch));
      setSaved(true);
      onSaved?.();
    } catch (err) {
      setSaveError(refusedSaveMessage(err));
    } finally {
      setSaving(false);
    }
  }, [
    canSave,
    baseline,
    sizeChanged,
    packsChanged,
    size,
    selection,
    applySettings,
    onSaved,
  ]);

  const mounted = packs.data ?? [];

  return (
    // A bordered strip rather than a card. The rhythm and the protocol
    // below are cards, and settings somebody touches twice a year should
    // not read as their peer.
    <div
      className="rounded-xl border border-white/[0.06] px-4 py-2"
      data-testid="protocol-settings"
    >
      {/* h2 to match the page's other blocks, wrapping the button so the
          settings keep a place in the heading outline while collapsed. */}
      <h2 className="m-0">
        {/* ring-primary/60 on every focus ring in this component, not the
            /50 used elsewhere: /60 is the computed value that clears the
            3:1 WCAG 1.4.11 floor against both the page background and the
            card surface. The /50 convention sits at 2.92:1 and is tracked
            repo-wide as #275, so new code stops adding to it. */}
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => {
            setEverOpened(true);
            setOpen((current) => !current);
          }}
          className="touch-target w-full text-left flex items-center justify-between gap-3 py-1 text-sm font-body text-text/60 transition-colors duration-200 hover:text-text/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
        >
          Protocol settings
          <span aria-hidden="true" className="text-xs text-text/60">
            {open ? "Hide" : "Show"}
          </span>
        </button>
      </h2>

      {/* The `hidden` attribute rather than a display class, and no
          layout classes on the element carrying it: a Tailwind `flex`
          would win on specificity against preflight's
          `[hidden] { display: none }` and the panel would stay on
          screen. The layout lives on the inner div. */}
      <div id={panelId} hidden={!open}>
        <div className="pt-4 pb-2 flex flex-col gap-6">
          <ApiStateView
            loading={loading}
            error={readError}
            loadingText="Loading your protocol settings..."
            onRetry={retryReads}
          >
            {ready && (
              <>
                <div className="flex flex-col gap-2">
                  <label
                    htmlFor={sizeId}
                    className="text-sm font-body text-text/70"
                  >
                    Practices a day
                  </label>
                  <select
                    id={sizeId}
                    value={String(size)}
                    aria-describedby={sizeHelpId}
                    onChange={(event) => {
                      resetNotice();
                      setSize(Number(event.target.value));
                    }}
                    className="touch-target w-full sm:w-auto rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2 text-sm font-body text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                  >
                    {PROTOCOL_SIZES.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                  <p
                    id={sizeHelpId}
                    className="text-xs font-body text-text/50 leading-relaxed max-w-prose"
                  >
                    {SIZE_HELP}
                  </p>
                </div>

                {mounted.length === 0 ? (
                  <p className="text-sm font-body text-text/50">{NO_PACKS}</p>
                ) : (
                  <fieldset
                    className="border-0 p-0 m-0"
                    aria-describedby={packsHelpId}
                  >
                    <legend className="text-sm font-body text-text/70 mb-1">
                      Practice packs
                    </legend>
                    <p
                      id={packsHelpId}
                      className="text-xs font-body text-text/50 leading-relaxed max-w-prose mb-2"
                    >
                      {PACKS_HELP}
                    </p>
                    <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
                      {(
                        [
                          { value: "all", label: "All packs" },
                          { value: "chosen", label: "Only the packs I pick" },
                        ] as { value: PackMode; label: string }[]
                      ).map((option) => (
                        <label
                          key={option.value}
                          className="touch-target inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 text-sm font-body text-text/60 cursor-pointer transition-colors duration-200 hover:border-white/20 has-[:checked]:border-primary/40 has-[:checked]:text-primary"
                        >
                          <input
                            type="radio"
                            name={`pack-mode-${modeName}`}
                            value={option.value}
                            checked={mode === option.value}
                            onChange={() => {
                              resetNotice();
                              setMode(option.value);
                            }}
                            className="accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                          />
                          {option.label}
                        </label>
                      ))}
                    </div>

                    {mode === "chosen" && (
                      <fieldset className="border-0 p-0 m-0 mt-3">
                        <legend className="text-xs font-body text-text/60 mb-2">
                          Packs to draw from
                        </legend>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {mounted.map((pack) => (
                            <label
                              key={pack.manifest.pack_id}
                              className="touch-target inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 text-sm font-body text-text/60 cursor-pointer transition-colors duration-200 hover:border-white/20 has-[:checked]:border-primary/40 has-[:checked]:text-primary"
                            >
                              <input
                                type="checkbox"
                                value={pack.manifest.pack_id}
                                checked={chosen.includes(pack.manifest.pack_id)}
                                onChange={() =>
                                  toggleChosen(pack.manifest.pack_id)
                                }
                                className="accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
                              />
                              {pack.manifest.title}
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    )}
                  </fieldset>
                )}

                <div className="flex flex-wrap items-center gap-3">
                  {/* aria-disabled rather than disabled, for the same
                      reason the integration prompt uses it: this button
                      goes inert the instant the save lands, and a
                      genuinely disabled control drops the keyboard user
                      who just pressed it back to the top of the page.
                      The handler is guarded, so it is inert either way. */}
                  <button
                    type="button"
                    onClick={handleSave}
                    aria-disabled={!canSave}
                    aria-busy={saving}
                    aria-describedby={notice ? noticeId : undefined}
                    className={`touch-target px-4 py-2 rounded-lg text-sm font-body font-medium bg-primary/15 text-primary border border-primary/30 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                      canSave
                        ? "hover:bg-primary/25"
                        : "opacity-50 cursor-not-allowed"
                    }`}
                  >
                    Save settings
                  </button>
                  <p
                    id={noticeId}
                    role="status"
                    aria-live="polite"
                    className="text-xs font-body text-text/60 leading-relaxed"
                  >
                    {notice}
                  </p>
                </div>
              </>
            )}
          </ApiStateView>
        </div>
      </div>
    </div>
  );
}
