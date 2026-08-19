"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import PracticeCard, { type PracticeCardState } from "./PracticeCard";
import SelfCheckPrompt from "./SelfCheckPrompt";
import IntegrationPrompt, { type IntegrationState } from "./IntegrationPrompt";
import { ApiError } from "@/lib/api";
import type {
  IntegrationCreate,
  PracticeDefinition,
  PracticeLogCreate,
  PracticeLogEntry,
  ProtocolItem,
  TodayResponse,
} from "@/lib/api";

type Slot = "morning" | "day" | "evening";

/**
 * The three slots in order, with the heading each one gets.
 *
 * They line up positionally with `daily_prompts`, so slot assignment is
 * a schema fact rather than a per-practice editorial call.
 */
const SLOTS: { key: Slot; heading: string }[] = [
  { key: "morning", heading: "Morning" },
  { key: "day", heading: "During the day" },
  { key: "evening", heading: "Evening" },
];

/** Everything one card is currently doing, keyed by slot and practice. */
interface CardStatus {
  state: PracticeCardState;
  /** True between the optimistic flip and the write landing. */
  pending: boolean;
  error: string | null;
  logId: string | null;
  selfCheckDismissed: boolean;
  selfCheckSaving: boolean;
  selfCheckSaved: boolean;
  selfCheckError: string | null;
  integration: IntegrationState;
  integrationError: string | null;
  integrationDismissed: boolean;
}

const FRESH: CardStatus = {
  state: "idle",
  pending: false,
  error: null,
  logId: null,
  selfCheckDismissed: false,
  selfCheckSaving: false,
  selfCheckSaved: false,
  selfCheckError: null,
  integration: "idle",
  integrationError: null,
  integrationDismissed: false,
};

/**
 * A card's identity. The slot is part of it: the same practice appears
 * three times a day, and completing it in the morning must not mark the
 * evening card done.
 */
function cardKey(slot: Slot, packId: string, slug: string): string {
  return `${slot}:${packId}/${slug}`;
}

/** A practice's identity across packs: two packs may share a slug. */
function practiceKey(packId: string, slug: string): string {
  return `${packId}/${slug}`;
}

/** True when a logged row names one of the three slots the page draws. */
function isSlot(value: string | null): value is Slot {
  return SLOTS.some((slot) => slot.key === value);
}

/**
 * The card face a logged row puts on, or null for a row that is not one.
 *
 * `started` is a row the user has not finished with, and a card that
 * says "Done today." for it would be claiming something they did not do.
 */
function loggedState(status: string): PracticeCardState | null {
  if (status === "completed") return "completed";
  if (status === "skipped") return "skipped";
  return null;
}

/**
 * Put the day's log onto the cards, filling only the ones still idle.
 *
 * This is what makes a reload keep today's work: completion lives in
 * component state, and without a read-back the rows sit in the log while
 * the cards come back blank (issue #312).
 *
 * Two passes, because a row that names its slot has the better claim on
 * it. A row logged from the morning card fills the morning card and
 * nothing else. Only a row with no usable slot on it, which is what a
 * completion logged outside the protocol looks like, falls through to
 * the earliest slot for that practice that is still free. Rows arrive
 * newest first, so the first claim on a card is the most recent thing
 * the user did there and an older row for the same card is left alone.
 *
 * A card the user has already moved is never rewritten. An optimistic
 * completion has no row in this log yet, and pushing it back to idle
 * would take away what they just did.
 *
 * Returns `current` itself when there is nothing to fill, so the caller
 * can hand it straight back to `setState` without forcing a render.
 */
function hydrateCards(
  current: Record<string, CardStatus>,
  today: TodayResponse,
  log: PracticeLogEntry[] | null,
): Record<string, CardStatus> {
  if (!log || log.length === 0) return current;

  // The cards today's protocol actually draws, kept in slot order per
  // practice so an unslotted row can take the earliest one still free.
  const drawn = new Set<string>();
  const slotsFor = new Map<string, string[]>();
  for (const { key: slot } of SLOTS) {
    for (const entry of today.slots[slot] ?? []) {
      const inProtocol = today.items.some(
        (item) => item.pack_id === entry.pack_id && item.slug === entry.slug,
      );
      if (!inProtocol) continue;
      const key = cardKey(slot, entry.pack_id, entry.slug);
      drawn.add(key);
      const practice = practiceKey(entry.pack_id, entry.slug);
      slotsFor.set(practice, [...(slotsFor.get(practice) ?? []), key]);
    }
  }

  const taken = new Set(
    Object.entries(current)
      .filter(([, status]) => status.state !== "idle")
      .map(([key]) => key),
  );

  // The rows already standing on a card, by the row's own id. Without
  // this, running again over the same log would walk an unslotted row
  // onto the next free slot and mark a second card the user never
  // touched. It also covers the row a completion just created: the write
  // records its id, so reading the log back cannot double it.
  const applied = new Set(
    Object.values(current)
      .map((status) => status.logId)
      .filter((id): id is string => id !== null),
  );

  const filled: Record<string, CardStatus> = {};
  const claim = (key: string, entry: PracticeLogEntry, state: PracticeCardState) => {
    taken.add(key);
    filled[key] = { ...FRESH, state, logId: entry.id };
  };

  const unslotted: { entry: PracticeLogEntry; state: PracticeCardState }[] = [];

  for (const entry of log) {
    const state = loggedState(entry.status);
    if (state === null) continue;
    if (applied.has(entry.id)) continue;
    const practice = practiceKey(entry.pack_id, entry.practice_slug);
    // Rotated out of today's protocol. The row stands in the log and on
    // the journey; there is simply no card here for it.
    if (!slotsFor.has(practice)) continue;

    if (!isSlot(entry.protocol_slot)) {
      unslotted.push({ entry, state });
      continue;
    }
    const key = cardKey(entry.protocol_slot, entry.pack_id, entry.practice_slug);
    // A row naming a slot this protocol does not draw, or one already
    // spoken for, stays where it is rather than being pushed onto some
    // other card the user never touched.
    if (!drawn.has(key) || taken.has(key)) continue;
    claim(key, entry, state);
  }

  for (const { entry, state } of unslotted) {
    const free = (
      slotsFor.get(practiceKey(entry.pack_id, entry.practice_slug)) ?? []
    ).find((key) => !taken.has(key));
    if (!free) continue;
    claim(free, entry, state);
  }

  if (Object.keys(filled).length === 0) return current;
  return { ...current, ...filled };
}

/** Shown when a save is worth trying again, which is most of them. */
const SAVE_FAILED = "That didn't save. Have another go in a moment.";

/**
 * What to tell the user about a refused integration save.
 *
 * A 422 from that route is the server declining on purpose: the entry's
 * note is full, and it says so in copy written for the reader, including
 * that the earlier notes are safe. Retrying is refused the same way, so
 * the generic line would be false as well as unhelpful. Everything else
 * keeps it, because a dropped connection really is worth another go.
 *
 * Only the integration route is read this way. The 422 there is a
 * deliberate sentence; a 422 elsewhere is schema validation, whose
 * detail is a list of field errors and not something to show anybody.
 */
function refusedSaveMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 422 && err.message) {
    return err.message;
  }
  return SAVE_FAILED;
}

interface DailyProtocolProps {
  today: TodayResponse;
  /**
   * Today's rows from the practice log, or null when they could not be
   * read. The cards start in the state these rows describe, so a reload
   * hands back the day the user has actually had rather than a clean
   * slate. Null degrades to the un-hydrated cards and nothing worse.
   */
  loggedToday?: PracticeLogEntry[] | null;
  /** The full definition, for the self-check question. May not be loaded yet. */
  lookup: (packId: string, slug: string) => PracticeDefinition | undefined;
  onLog: (entry: PracticeLogCreate) => Promise<PracticeLogEntry>;
  /**
   * Saves the integration record for one completion. Keyed on the
   * practice log row, so the self-check and the integration prompt both
   * write to the same record rather than one each.
   */
  onIntegrate: (entry: IntegrationCreate) => Promise<unknown>;
  /** Fires after a write lands, so the page can refresh the rhythm. */
  onLogged?: () => void;
}

/**
 * Today's protocol: N practices rendered three times, once per slot.
 *
 * Completion is optimistic. The card says "Done today." the moment it is
 * tapped and rolls back if the write fails, because the common case is
 * that it succeeds and a spinner between tap and confirmation makes a
 * one-second interaction feel like a transaction.
 *
 * Optimistic state is not the record, though, so the day's log comes in
 * as `loggedToday` and the cards start from it. See `hydrateCards` for
 * how rows land on cards and why a card the user has touched is never
 * rewritten.
 */
export default function DailyProtocol({
  today,
  loggedToday = null,
  lookup,
  onLog,
  onIntegrate,
  onLogged,
}: DailyProtocolProps) {
  // Hydrated in the initializer rather than in the effect below, so the
  // cards are drawn settled the first time. Drawing them idle and
  // flipping them a moment later would rewrite the page under the reader
  // and move focus onto a completion they did not just make.
  const [cards, setCards] = useState<Record<string, CardStatus>>(() =>
    hydrateCards({}, today, loggedToday),
  );

  // The log can also arrive after the first paint, or change under a
  // rotated protocol. Merging rather than replacing is what keeps a card
  // the user has just tapped from being pushed back.
  useEffect(() => {
    setCards((current) => hydrateCards(current, today, loggedToday));
  }, [today, loggedToday]);

  const statusFor = useCallback(
    (key: string): CardStatus => cards[key] ?? FRESH,
    [cards],
  );

  const patch = useCallback((key: string, changes: Partial<CardStatus>) => {
    setCards((current) => ({
      ...current,
      [key]: { ...(current[key] ?? FRESH), ...changes },
    }));
  }, []);

  const write = useCallback(
    async (
      key: string,
      item: ProtocolItem,
      slot: Slot,
      status: "completed" | "skipped",
    ) => {
      // Optimistic: show the outcome first, undo it only if the write
      // is refused. `pending` marks the window in between, which is what
      // the card reports as aria-busy.
      patch(key, { state: status, pending: true, error: null });
      try {
        const created = await onLog({
          pack_id: item.pack_id,
          practice_slug: item.slug,
          day_key: today.day_key,
          status,
          protocol_slot: slot,
        });
        patch(key, { logId: created.id, pending: false });
        onLogged?.();
      } catch {
        patch(key, {
          state: "idle",
          pending: false,
          error: SAVE_FAILED,
        });
      }
    },
    [onLog, onLogged, patch, today.day_key],
  );

  // The self-check and the integration prompt are two controls over one
  // completion, and they write to one record: the server keys it on the
  // practice log row and merges each save into what is already there.
  // The merge reads the stored note before adding to it, so two saves
  // in flight at once could have the second read the record before the
  // first had written to it, and one of the two notes would be lost.
  // Saves for a card queue behind each other instead of racing.
  const saves = useRef<Record<string, Promise<void>>>({});

  const enqueue = useCallback(
    (key: string, save: () => Promise<void>): Promise<void> => {
      // Each save reports its own failure and resolves either way, so
      // the chain needs no rejection path and one refused write does
      // not strand the next one behind it.
      const next = (saves.current[key] ?? Promise.resolve()).then(save);
      saves.current[key] = next;
      return next;
    },
    [],
  );

  const saveSelfCheck = useCallback(
    (key: string, logId: string, response: string) => {
      // The busy state is set on the click rather than when the queued
      // write starts, so a save waiting its turn still looks like a
      // save in progress.
      patch(key, { selfCheckSaving: true, selfCheckError: null });
      return enqueue(key, async () => {
        try {
          await onIntegrate({ practice_log_id: logId, note: response });
          // Confirmed rather than unmounted. A control that vanishes on
          // success takes the user's focus with it and says nothing.
          patch(key, { selfCheckSaving: false, selfCheckSaved: true });
        } catch (err) {
          patch(key, {
            selfCheckSaving: false,
            selfCheckError: refusedSaveMessage(err),
          });
        }
      });
    },
    [enqueue, onIntegrate, patch],
  );

  const saveIntegration = useCallback(
    (
      key: string,
      logId: string,
      input: { capacityDelta: number | null; note: string },
    ) => {
      patch(key, { integration: "saving", integrationError: null });
      return enqueue(key, async () => {
        try {
          await onIntegrate({
            practice_log_id: logId,
            capacity_delta: input.capacityDelta,
            note: input.note || null,
          });
          patch(key, { integration: "saved" });
        } catch (err) {
          patch(key, {
            integration: "error",
            integrationError: refusedSaveMessage(err),
          });
        }
      });
    },
    [enqueue, onIntegrate, patch],
  );

  if (today.items.length === 0) {
    return (
      <div className="card-surface p-8 text-center">
        <p className="text-sm font-body text-text/50 max-w-md mx-auto">
          Nothing scheduled today. Browse the library and pick something that
          fits.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {SLOTS.map(({ key: slot, heading }) => {
        const entries = today.slots[slot] ?? [];
        const headingId = `protocol-slot-${slot}`;
        return (
          <section key={slot} aria-labelledby={headingId}>
            <h2
              id={headingId}
              className="font-display text-lg font-medium text-text/80 mb-3"
            >
              {heading}
            </h2>
            <div className="flex flex-col gap-3">
              {entries.map((entry) => {
                const item = today.items.find(
                  (candidate) =>
                    candidate.pack_id === entry.pack_id &&
                    candidate.slug === entry.slug,
                );
                if (!item) return null;

                const key = cardKey(slot, entry.pack_id, entry.slug);
                const status = statusFor(key);
                const definition = lookup(entry.pack_id, entry.slug);
                const completed = status.state === "completed";
                const question = definition?.self_check?.question;

                return (
                  <PracticeCard
                    key={key}
                    item={item}
                    prompt={entry.prompt}
                    state={status.state}
                    pending={status.pending}
                    error={status.error}
                    onComplete={() => void write(key, item, slot, "completed")}
                    onSkip={() => void write(key, item, slot, "skipped")}
                  >
                    {completed && question && !status.selfCheckDismissed && (
                      <SelfCheckPrompt
                        question={question}
                        saving={status.selfCheckSaving}
                        saved={status.selfCheckSaved}
                        error={status.selfCheckError}
                        onSave={(response) => {
                          if (status.logId) {
                            void saveSelfCheck(key, status.logId, response);
                          }
                        }}
                        onDismiss={() => patch(key, { selfCheckDismissed: true })}
                      />
                    )}
                    {completed && !status.integrationDismissed && (
                      <IntegrationPrompt
                        practiceTitle={item.title}
                        state={status.integration}
                        error={status.integrationError}
                        onSubmit={(input) => {
                          if (status.logId) {
                            void saveIntegration(key, status.logId, input);
                          }
                        }}
                        onDismiss={() =>
                          patch(key, { integrationDismissed: true })
                        }
                      />
                    )}
                  </PracticeCard>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
